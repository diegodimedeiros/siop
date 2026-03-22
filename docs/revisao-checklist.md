# Checklist de Revisao

## Arquitetura

- a funcao nova esta na camada correta?
- existe helper pronto antes de duplicar logica?
- `shared` nao recebeu regra de negocio?
- o modulo de tela nao recebeu infraestrutura generica?
- o `main.js` nao recebeu comportamento que deveria ficar em modulo?

## Frontend

- feedback visual segue o padrao novo?
- loading visual foi aplicado onde ha acao assincrona?
- erro AJAX esta usando helper padronizado?
- nao foi criado `alert(...)` novo?
- nao foi criado JS inline novo?
- formularios com campos obrigatorios mantem validacao visual coerente?

## Backend

- o endpoint retorna contrato JSON consistente?
- sucesso usa `api_success` quando fizer sentido?
- erro usa `api_error` quando fizer sentido?
- detalhes tecnicos sensiveis nao vazam para o usuario final?

## Qualidade

- configuracoes sensiveis ficaram fora do codigo versionado?
- documentacao precisa de ajuste?
- existe teste ou checklist cobrindo o fluxo alterado?
