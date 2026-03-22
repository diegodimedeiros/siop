# Checklist de Testes

## Fluxos Criticos

### Ocorrencias

- criar ocorrencia com campos obrigatorios
- editar ocorrencia existente
- validar erro visual quando faltar campo obrigatorio
- validar loading no botao de salvar
- validar feedback de sucesso e erro

### Acesso de Terceiros

- criar acesso com campos obrigatorios
- editar acesso existente
- validar loading no botao de salvar
- validar feedback de sucesso e erro

### Atendimento

- enviar formulario com validacao nativa
- validar loading no submit
- validar captura de geolocalizacao antes do envio
- validar reset do formulario e limpeza visual

### Manejo

- criar manejo com dados minimos validos
- validar loading no submit
- validar feedback de sucesso
- validar erro JSON padronizado em envio invalido

### Exportacao

- filtrar registros
- exportar CSV
- exportar XLSX
- exportar PDF
- validar que o botao nao fica preso em loading quando houver bloqueio

## Testes Automatizados Minimos

Atualmente existem smoke tests em Django para:

- redirecionamento de paginas protegidas quando anonimo
- renderizacao autenticada das paginas principais
- contrato JSON de erro para POST AJAX invalido nos fluxos principais
