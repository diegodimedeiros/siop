# Padrao Backend

## Objetivo

Consolidar um padrao unico de backend baseado na estrutura real do projeto, sem reinventar arquitetura, garantindo:

- contrato JSON previsivel
- separacao clara de responsabilidades
- reducao de duplicacao
- evolucao segura e incremental
- prevencao de regressoes estruturais

## Principio Central

O backend do projeto segue um modelo padronizado onde:

- toda resposta JSON usa `api_success(...)` ou `api_error(...)`
- todo erro de dominio e representado por `ServiceError`
- toda view e fina e nao contem regra de negocio
- toda regra de negocio vive nos services
- parsing e validacao reutilizavel nao ficam na view
- o padrao e reforcado por testes e checagem automatizada

## Arquitetura do Backend

### Infraestrutura comum

Local: `core/`

Responsavel por:

- contrato HTTP/JSON (`core/api.py`)
- excecoes de dominio (`ServiceError`)
- parsing, validacao e helpers reutilizaveis
- utilitarios de exportacao, formatacao e permissoes

### Services de dominio

Local: `siop/services/`

Responsavel por:

- regra de negocio
- validacao de dominio
- persistencia
- integracao com helpers comuns

Services:

- nao conhecem HTTP
- nao retornam `JsonResponse`
- nao acessam `request`
- levantam `ServiceError` quando necessario

### Views

Local: `siop/view/`

Responsavel por:

- autenticacao
- leitura da request
- chamada do service
- retorno padronizado

Views:

- nao contem regra de negocio complexa
- nao fazem parsing duplicado
- nao montam respostas fora de `api_success(...)` e `api_error(...)`

## Contrato JSON

### Sucesso

```json
{
  "ok": true,
  "data": {},
  "message": "Mensagem opcional"
}
```

### Erro

```json
{
  "ok": false,
  "error": {
    "code": "error_code",
    "message": "Mensagem amigavel",
    "details": {}
  }
}
```

## Codigos de Erro Oficiais

- `validation_error`
- `invalid_json`
- `invalid_payload`
- `invalid_pagination`
- `permission_denied`
- `not_found`
- `method_not_allowed`
- `conflict`
- `internal_error`

Regras:

- `code` deve ser estavel
- `message` deve ser amigavel
- `details` deve conter informacoes por campo quando necessario

## Fluxo Padrao de Execucao

Toda rota de dominio deve seguir:

1. autenticar e validar metodo
2. extrair payload por caminho padronizado
3. delegar regra de negocio ao service
4. traduzir `ServiceError` para `api_error(...)`
5. traduzir sucesso para `api_success(...)`
6. registrar erro inesperado com logging e responder com `internal_error`

## Padrao de View

```python
import logging

from django.contrib.auth.decorators import login_required

from core.api import ApiStatus, api_error, api_success, parse_json_body
from core.services import ServiceError
from siop.services import create_recurso

logger = logging.getLogger(__name__)


def _extract_request_payload(request):
    json_data, json_error = parse_json_body(request)
    if json_error:
        return None, None, json_error

    if json_data is not None:
        return json_data, [], None

    return request.POST, request.FILES.getlist("anexos"), None


def _service_error_response(exc):
    return api_error(
        code=exc.code,
        message=exc.message,
        status=exc.status,
        details=exc.details,
    )


def _unexpected_error_response(log_message, **extra):
    logger.exception(log_message, extra=extra or None)
    return api_error(
        code="internal_error",
        message="Erro interno ao processar a solicitacao.",
        status=500,
    )


@login_required
def recurso_new(request):
    if request.method != "POST":
        return api_error(
            code="method_not_allowed",
            message="Metodo nao permitido.",
            status=405,
        )

    try:
        data, files, payload_error = _extract_request_payload(request)
        if payload_error:
            return payload_error

        recurso = create_recurso(
            data=data,
            files=files,
            user=request.user,
        )

        return api_success(
            data={"id": recurso.id},
            message="Recurso criado com sucesso.",
            status=ApiStatus.CREATED,
        )
    except ServiceError as exc:
        return _service_error_response(exc)
    except Exception:
        return _unexpected_error_response(
            "Erro inesperado ao criar recurso",
            user_id=getattr(request.user, "id", None),
        )
```

## Padrao de Service

```python
from core.services import ServiceError


def create_recurso(*, data, files, user):
    if not str(data.get("campo", "")).strip():
        raise ServiceError(
            code="validation_error",
            message="Campo obrigatorio.",
            status=422,
        )

    # regra de negocio
    # persistencia

    return recurso
```

## Regras de Implementacao

### Deve

- usar `api_success(...)` e `api_error(...)`
- usar `ServiceError`
- manter a view fina
- reutilizar helpers de parsing e validacao
- usar `@login_required` em rotas sensiveis

### Nao deve

- usar `JsonResponse` diretamente nas views
- colocar regra de negocio na view
- duplicar parsing de dados
- acessar `request` dentro de service
- criar contrato JSON diferente do padrao

## Paginacao

Endpoints de listagem devem usar:

```json
{
  "meta": {
    "pagination": {
      "total": 0,
      "limit": 10,
      "offset": 0,
      "count": 10
    }
  }
}
```

## Exportacao

Exportacoes devem:

- reutilizar infraestrutura comum
- evitar logica duplicada por dominio
- separar `headers`, `row_getters` e formatacao

## Testes Minimos Obrigatorios

Todo dominio critico deve ter:

- acesso protegido com redirect para login
- sucesso com `ok=true`
- erro com `ok=false`
- teste de payload invalido
- teste de metodo invalido
- teste de paginacao invalida, quando aplicavel

## Checagem Automatizada

Script:

```bash
python3 scripts/check_backend_patterns.py
```

Valida:

- uso de `api_success(...)` e `api_error(...)`
- presenca de `@login_required`
- uso correto de parsing
- ausencia de `JsonResponse` indevido
- estrutura basica das views
- arquivos grandes como warning de divida tecnica

## Estrategia de Evolucao

A evolucao do backend deve seguir:

1. extrair duplicacao
2. padronizar estrutura
3. validar com checker e testes
4. so entao considerar refatoracao maior

Nao fazer:

- refatoracao massiva de uma vez
- split agressivo de arquivos grandes
- mudanca simultanea de estrutura e regra

## Quando Criar Helper Novo

Criar helper comum quando:

- o mesmo parsing aparece em mais de uma view
- o mesmo contrato JSON aparece em mais de um dominio
- a mesma serializacao e usada em lista e detalhe
- a mesma validacao aparece em mais de um service

Nao criar helper quando:

- a regra ainda e local de um unico dominio
- a abstracao so existe para reduzir poucas linhas
- o helper ficaria mais generico do que util

## Revisao de Endpoint de Referencia

### Endpoint revisado

- `POST /ocorrencias/new/`
- view: `siop/view/ocorrencias.py`

### Pontos positivos

- usa `@login_required`
- usa payload padronizado para JSON ou multipart
- delega regra de negocio para `create_ocorrencia(...)`
- converte `ServiceError` para `api_error(...)`
- usa `api_success(...)` com `201 Created`
- trata excecao inesperada com `internal_error`

### Pontos de atencao

- a mesma view ainda responde ao fluxo HTML de criacao
- o arquivo continua grande e merece cortes incrementais
- o proximo passo natural e reduzir duplicacao de export, filtros e serializacao

### Veredito

O endpoint esta alinhado ao padrao consolidado do projeto e pode ser tratado como referencia de implementacao para fluxos `create`.

## Direcao Operacional para `ocorrencias.py`

Nesta fase do projeto, a evolucao de `siop/view/ocorrencias.py` deve seguir o mesmo padrao incremental ja validado em `acesso_terceiros.py` e `chamado.py`: reduzir duplicacao estrutural, centralizar infraestrutura repetida, preservar o contrato HTTP/JSON, manter a regra de negocio intacta e medir continuamente com checker e testes.

O arquivo ainda concentra:

- exportacao CSV, XLSX e PDF
- serializacao de anexos, lista e detalhe
- busca, ordenacao e filtros
- paginacao
- listagem JSON e listagem parcial HTML
- render da tela principal
- detail JSON
- create e edit
- catalogos e endpoints auxiliares

Ou seja: o problema residual do modulo ja nao e mais falta de padrao, e sim concentracao de responsabilidade.

### Ordem correta de consolidacao

1. centralizar queryset, busca, filtros, ordenacao e paginacao
2. centralizar a infraestrutura de exportacao
3. agrupar serializacao e render da tela principal
4. preservar `create/edit` no padrao oficial ja consolidado
5. medir novamente antes de considerar qualquer split fisico

### Cortes internos recomendados

Para listagem e filtros:

- `_build_ocorrencias_base_qs()`
- `_normalize_ocorrencia_search_params(request)`
- `_build_ocorrencia_filtered_qs(request)`

Para exportacao:

- `OCORRENCIAS_EXPORT_HEADERS`
- `OCORRENCIAS_EXPORT_BASE_COL_WIDTHS`
- `_get_ocorrencias_export_row_getters()`

Para render da pagina:

- `_build_ocorrencia_page_context(request)`
- `_render_ocorrencia_page(request)`

Para serializacao, quando necessario:

- `_serialize_ocorrencia_base_fields(...)`
- `_serialize_ocorrencia_audit_fields(...)`
- `_serialize_ocorrencia_anexos(...)`

### O que nao fazer nesta etapa

- nao criar arquitetura nova
- nao mover tudo para novos modulos fisicos de uma vez
- nao alterar contrato JSON
- nao mudar regra de negocio
- nao trocar semantica de filtros, paginacao ou exportacao

### Criterio de pronto desta fase

Essa etapa pode ser considerada bem-feita quando:

- listagem, filtros, paginacao e export usam a mesma base de queryset
- exportacao nao repete `headers` e `row_getters`
- a tela principal nao tem render duplicado
- serializacao continua previsivel e centralizada
- `create/edit` permanecem no padrao oficial do projeto
- o checker nao aponta erro duro
- o restante do warning de tamanho represente apenas volume residual, e nao inconsistencia estrutural

### Formulacao oficial da etapa

A refatoracao final de `ocorrencias.py` deve reduzir duplicacao estrutural de queryset, filtros, paginacao, exportacao, serializacao e render da tela principal, preservando o contrato HTTP/JSON, o padrao de `create/edit` ja consolidado e toda a regra de negocio existente, com validacao continua por checker e testes antes de qualquer split fisico do arquivo.

## Regra de Ouro

Nenhuma melhoria estrutural deve alterar o comportamento do sistema.

Refatoracao deve ser sempre:

- incremental
- testavel
- reversivel
- previsivel
