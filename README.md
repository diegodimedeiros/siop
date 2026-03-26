# SIOP

## Visão Geral

Este projeto é um sistema web interno desenvolvido em Django para apoiar rotinas operacionais de controle, atendimento e registro de eventos em campo.

Pelo domínio modelado no código, o sistema foi pensado para centralizar informações relacionadas a:

- registro de ocorrências;
- controle de acesso de terceiros;
- atendimento operacional;
- manejo de fauna;
- anexos, fotos, assinaturas e geolocalização.

Em termos práticos, trata-se de uma aplicação administrativa usada para documentar fatos, pessoas, acessos e ações executadas em uma operação local.

## Objetivo

O objetivo do sistema é oferecer um ponto único para cadastro, consulta, acompanhamento e exportação de informações operacionais, permitindo rastreabilidade e organização dos registros.

## Principais Módulos

### Ocorrências

Responsável pelo registro de incidentes ou eventos observados na operação.

Funcionalidades identificadas:

- cadastro de ocorrência;
- edição de ocorrência;
- listagem com filtros e busca;
- visualização em JSON;
- exportação em PDF, Excel e CSV;
- vínculo com anexos.

Campos centrais observados:

- data e hora;
- natureza;
- tipo;
- área;
- local;
- tipo de pessoa;
- descrição;
- status;
- indicadores como CFTV e acionamento de bombeiro civil.

### Acesso de Terceiros

Módulo voltado ao controle de entrada e saída de pessoas externas, como visitantes, fornecedores ou prestadores.

Funcionalidades identificadas:

- cadastro de acesso;
- edição;
- listagem com busca;
- exportação;
- anexação de arquivos.

Campos centrais observados:

- entrada e saída;
- nome e documento;
- empresa;
- placa de veículo;
- P1;
- descrição do acesso.

### Controle de Atendimento

Módulo relacionado a atendimentos operacionais, com foco em dados da pessoa atendida, contexto do atendimento e evidências associadas.

Capacidades previstas no projeto:

- registro do atendimento;
- dados de pessoa e contato;
- informações sobre acompanhante;
- primeiros socorros;
- transporte e encaminhamento;
- testemunhas;
- assinatura;
- fotos;
- geolocalização;
- anexos.

### Manejo

Módulo voltado ao registro de manejo de fauna.

Funcionalidades identificadas:

- cadastro de manejo;
- seleção de classe e espécie;
- registro de captura e soltura;
- fotos de captura e soltura;
- geolocalização;
- observações operacionais.

## Recursos Transversais

### Anexos e Arquivos

O projeto possui modelos genéricos para anexos, fotos e assinaturas, com armazenamento binário no banco de dados.

Também foram identificados:

- cálculo de hash dos arquivos;
- validação de tamanho;
- associação genérica com diferentes entidades do sistema.

### Geolocalização

O sistema permite vincular latitude e longitude a diferentes registros, com validação e regras de unicidade.

### Exportação de Dados

Há utilitários para exportação em:

- CSV;
- Excel;
- PDF.

Esse recurso aparece principalmente nos módulos de ocorrências e acessos de terceiros.

### Catálogos JSON

O projeto usa arquivos JSON como fonte de catálogos operacionais, por exemplo:

- áreas;
- naturezas;
- tipos;
- fauna;
- P1;
- sexos;
- transportes;
- encaminhamentos.

Esses catálogos são carregados por utilitários e usados para popular formulários e APIs auxiliares.

## Stack

- Python 3
- Django 5.2
- SQLite
- openpyxl
- reportlab

## Estrutura Principal

- `core/`: configuração principal, utilitários e serviços compartilhados;
- `siop/`: app principal com modelos, views, serviços, templates e catálogos;
- `static/`: arquivos estáticos;
- `docs/`: documentação auxiliar.

## Documentação Técnica

- [Contrato da API](./docs/api.md)
- [Arquitetura JavaScript](./docs/js-arquitetura.md)
- [Templates Frontend](./docs/frontend-templates.md)
- [Padrão Backend](./docs/backend-padrao.md)
- [Banco de Dados](./docs/banco-de-dados.md)
- [Checklist de Testes](./docs/testes-fluxos.md)
- [Checklist de Revisão](./docs/revisao-checklist.md)

Observacao:
- `docs/backend-padrao.md` e a fonte oficial do padrao de implementacao do backend.
- `docs/js-arquitetura.md` concentra o roadmap e as convencoes da arquitetura frontend.
- `docs/frontend-templates.md` concentra o padrao da camada de templates e sua integracao com backend e JS.
- `core.utils` e a fonte preferencial para catalogos, formatadores, exports e helpers compartilhados; `siop.utils` permanece apenas como camada de compatibilidade temporaria.

## Ambiente e Qualidade

- Exemplo de variaveis locais: `.env.example`
- Lint de frontend: `npm run lint:js`
- Verificacao de formatacao: `npm run format:check`
- Checagem de padrao backend: `python3 scripts/check_backend_patterns.py`
- Smoke tests backend: `python3 manage.py test siop`

## Resumo

O projeto é um sistema operacional interno para registro e acompanhamento de ocorrências, acessos, atendimentos e manejo, com foco em controle administrativo, evidências e geração de relatórios.
