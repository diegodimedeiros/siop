# Contrato da API Interna

## Formato de sucesso

```json
{
  "ok": true,
  "data": {},
  "message": "Operacao realizada com sucesso.",
  "meta": {}
}
```

Notas:
- `meta` e opcional.
- Em listas, `meta.pagination` informa `total`, `limit`, `offset` e `count`.

## Formato de erro

```json
{
  "ok": false,
  "error": {
    "code": "validation_error",
    "message": "Mensagem amigavel",
    "details": {}
  }
}
```

Notas:
- `details` pode ser `null` quando nao houver detalhe adicional.

## Status codes padronizados

- `200` OK
- `201` Created
- `204` No Content
- `400` Bad Request
- `401` Unauthorized
- `403` Forbidden
- `404` Not Found
- `409` Conflict
- `422` Unprocessable Entity

## Codigos de erro oficiais

- `validation_error`
- `invalid_json`
- `invalid_payload`
- `invalid_pagination`
- `permission_denied`
- `not_found`
- `method_not_allowed`
- `conflict`
- `internal_error`

Regra:

- `code` deve ser estavel e previsivel;
- `message` deve ser amigavel para consumo do frontend;
- `details` deve carregar detalhe tecnico ou por campo quando necessario.

## Parsing e validacao de JSON

- Para `Content-Type: application/json`, o backend usa parser central.
- JSON malformado retorna `400` com `error.code = "invalid_json"`.
- JSON bem-formado com payload invalido (ex.: nao-objeto) retorna `422`.
- Campos obrigatorios ausentes/invalidos retornam `422` com `error.details` por campo.
- Para upload de anexos, `multipart/form-data` continua suportado.

## Rotas canonicas por recurso

- `GET /api/ocorrencias/`
- `GET /api/ocorrencias/<id>/`
- `GET /api/acessos-terceiros/`
- `GET /api/acessos-terceiros/<id>/`

As rotas antigas permanecem ativas para compatibilidade.

## Convencao de implementacao

- view fina: autentica, le entrada, chama service e responde;
- service levanta `ServiceError` para regra de negocio invalida;
- endpoint JSON nao deve montar resposta arbitraria se `api_success/api_error` ja cobrem o caso;
- paginacao deve usar `meta.pagination` com `total`, `limit`, `offset` e `count`.
