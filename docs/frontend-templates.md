# Frontend Templates

## Objetivo

Consolidar um padrao de templates alinhado com a arquitetura atual do projeto, garantindo:

- separacao clara entre estrutura HTML, comportamento JS e contrato backend
- carregamento de scripts por dominio, e nao globalmente sem necessidade
- eliminacao gradual de residuos de comportamento inline
- evolucao incremental dos templates sem abrir refatoracao visual desnecessaria

## Principio Central

Os templates do projeto devem cumprir papel estrutural e declarativo.

Isso significa:

- HTML organiza layout, blocos e pontos de integracao
- backend injeta estado inicial da tela
- JS controla comportamento, eventos e consumo de API
- feedback visual converge para a camada compartilhada

## Papel de Cada Camada

### `base.html`

Responsavel por:

- layout global
- sidebar e navegacao
- blocos de extensao (`content`, `extra_js`, etc.)
- carregamento apenas do que e realmente global

Nao deve:

- carregar scripts de dominio de todas as telas
- concentrar comportamento especifico de pagina

### Template de dominio

Exemplo: `ocorrencias/ocorrencia.html`

Responsavel por:

- estruturar a tela principal do dominio
- injetar estado inicial via `data-*`
- incluir parciais (`list`, `view`, `edit`, `new`, `export`)
- carregar JS especifico do dominio via `block extra_js`

### Includes

Responsaveis por:

- separar responsabilidades visuais da tela
- evitar templates gigantes
- manter cada bloco previsivel e isolado

## Estado Atual Consolidado

A camada de templates do projeto ja esta estruturalmente boa e coerente com a arquitetura consolidada de backend e JS.

Pontos fortes:

- `base.html` bem organizado como layout global
- uso consistente de `{% block content %}` e `{% block extra_js %}`
- telas de dominio modularizadas por `{% include %}`
- integracao com backend via `data-*` para estado inicial
- integracao com JS sem dependencia pesada de handlers inline

## Contrato Entre Template e Frontend

### Estado inicial da tela

Quando a tela precisar manter sincronismo entre SSR e JS, o estado inicial deve ser injetado via `data-*`.

Exemplo de uso valido:

- `data-current-query`
- `data-current-scope`
- `data-current-sort`
- `data-current-dir`

Esse padrao deve ser entendido como contrato oficial da camada de apresentacao:

- backend renderiza estado inicial
- JS le esse estado e continua a interacao sem duplicar regra

### Contrato de navegacao frontend

Quando o frontend depender de atributos estruturais do layout global, isso deve ser tratado como convencao explicita.

Exemplo atual:

- `body[data-real-path]`

Nao exige mudanca imediata, mas deve ser entendido como contrato entre template e bootstrap JS.

## Desvios Reais de Padrao

### 1. Residuos de comportamento inline

Ainda podem existir pontos pequenos com `onclick` ou comportamento equivalente dentro do HTML.

Direcao correta:

- HTML continua estrutural
- comportamento vai para o modulo JS do dominio

### 2. Feedback local legado

Modais locais de sucesso ou erro dentro de templates de dominio devem ser tratados como legado quando ja existir:

- `shared/modal.js`
- `shared/feedback.js`

Direcao correta:

- nao replicar novo feedback local
- convergir progressivamente para a camada compartilhada

### 3. Estilos inline espalhados

Existe divida real em `style="..."` distribuido em templates.

Isso deve ser tratado de forma gradual, nunca junto de uma refatoracao estrutural maior.

## O Que Esta Correto e Deve Ser Mantido

- estrutura por tabs com `{% include %}` em telas densas
- estado inicial da tela via `data-*`
- separacao entre layout global e tela de dominio
- integracao do HTML com JS por seletores e atributos, e nao por handlers espalhados
- uso de `block extra_js` para carga por pagina

## Ordem Correta de Ajustes

### Ajuste prioritario

Remover residuos de comportamento inline e mover o comportamento para os modulos JS correspondentes.

### Ajuste seguinte

Convergir modais locais de sucesso/erro para `shared/feedback.js` e `shared/modal.js`.

### Ajuste posterior

Enxugar paginas especiais, como `login.html`, para carregar apenas os shareds realmente necessarios.

### Ajuste futuro

Reduzir `style="..."` repetidos para classes CSS reutilizaveis, sem abrir redesign da tela.

## O Que Nao Fazer Agora

- nao criar sistema de componentes complexo para templates
- nao tentar resolver toda repeticao visual de uma vez
- nao abrir redesign junto com ajuste estrutural
- nao mexer em todos os templates simultaneamente
- nao criar includes novos sem evidencia clara de ganho

## Sequencia Oficial Desta Fase

1. remover comportamento inline residual
2. tratar modais locais como legado e convergir para feedback compartilhado
3. enxugar carregamento de scripts em paginas especiais
4. reduzir estilos inline gradualmente em rodadas futuras

## Formulacao Oficial da Etapa

Os templates do projeto ja estao coerentes com a arquitetura consolidada; a proxima etapa deve apenas alinhar carregamento de scripts por dominio, eliminar residuos de comportamento inline e convergir o feedback visual para a camada compartilhada, sem abrir uma nova refatoracao estrutural dos templates.
