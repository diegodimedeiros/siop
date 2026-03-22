# Arquitetura JavaScript

## Resumo

O frontend foi reorganizado para reduzir duplicacao, isolar responsabilidades e permitir crescimento incremental com baixo risco.

O que ja foi consolidado:

- camada `shared` para infraestrutura reutilizavel;
- modulos por dominio e por tela;
- extracao de `modal` e `signature-pad`;
- limpeza do `main.js` para papel de bootstrap;
- uso de `context pattern` em dominios mais densos;
- decomposicao de funcoes grandes, como o fluxo de ocorrencias/acessos.

## Camadas

### 1. `shared/`

Infraestrutura reutilizavel e sem regra de negocio.

Arquivos atuais:

- `http.js`
- `forms.js`
- `files.js`
- `geolocation.js`
- `modal.js`
- `feedback.js`
- `signature-pad.js`

Regra:

- resolve `como` fazer algo;
- registra helpers em `window.SIOPShared`;
- nao deve conter fluxo especifico de tela.

### 2. Dominio

Camada intermediaria para logicas reutilizaveis dentro de um mesmo dominio.

Exemplo de alvo:

- `ocorrencias-core.js`
- `ocorrencias-search-list.js`
- `ocorrencias-view-edit.js`
- `ocorrencias-create.js`
- `ocorrencias-export.js`
- `ocorrencias-feedback.js`

Regra:

- resolve fluxo reutilizavel dentro do dominio;
- pode usar `context pattern`;
- ainda nao deve carregar regra global do app.

### 3. Modulos de tela

Arquivos focados no fluxo e na regra de negocio de uma tela especifica.

Exemplos atuais:

- `controlebc-manejo.js`
- `controlebc-atendimento.js`
- `controlebc-geolocation.js`

Regra:

- resolve `quando` usar a infraestrutura;
- integra DOM, eventos e regra da tela;
- deve fazer `abort early` quando a tela nao tiver os elementos esperados.

### 4. `main.js`

Arquivo de bootstrap e features globais.

Responsabilidades:

- inicializadores globais;
- comportamento transversal do app;
- orquestracao de modulos de dominio ainda residentes no arquivo.

Regra:

- se e global, fica aqui;
- se e de dominio, deve sair daqui com o tempo.

## Principios

- Separacao de responsabilidades
- Modularizacao
- Baixo acoplamento
- Reutilizacao controlada
- Refatoracao incremental de baixo risco

## Regras Importantes

- Nunca misturar infraestrutura com regra de negocio.
- Nunca refatorar comportamento e estrutura ao mesmo tempo.
- Sempre seguir o fluxo: copiar -> testar -> apagar.
- Evitar abstrair cedo demais quando a regra ainda e local.

## Context Pattern

Para dominios grandes, criar um objeto de contexto em vez de espalhar dezenas de referencias soltas.

Exemplo:

- `buildOcorrenciasContext()`

Beneficios:

- reduz duplicacao;
- centraliza estado;
- melhora legibilidade;
- facilita o recorte em funcoes menores.

## Padrao de Modulo

Cada modulo deve seguir, sempre que possivel:

- `IIFE`
- `'use strict'`
- aliases de `window.SIOPShared`
- `initNomeDoModulo()`
- `DOMContentLoaded`
- `abort early` se o DOM necessario nao existir

## Padrao de Shared

- registrar em `window.SIOPShared`;
- expor apenas helpers reutilizaveis;
- evitar regra de negocio;
- manter API pequena e previsivel.

## Padrao de Feedback

Convencao atual do frontend:

- sucesso rapido: `toast`;
- erro de request: `toast` padronizado;
- aviso: `toast`;
- confirmacao importante: `modal`;
- validacao de campo: mensagem inline junto ao campo;
- loading: no botao ou na area afetada.

Infraestrutura atual:

- `shared/modal.js`
- `shared/feedback.js`
- `shared/http.js`

## Como Criar Um Modulo Novo

Antes de criar um arquivo novo, decidir primeiro em qual camada ele pertence:

- se resolve infraestrutura reutilizavel, vai para `shared/`;
- se resolve fluxo de um dominio, vai para arquivos de dominio;
- se resolve comportamento de uma tela especifica, vira modulo de tela;
- se o comportamento e global, deve ficar no `main.js`.

### Checklist

- confirmar a responsabilidade do modulo;
- evitar misturar infraestrutura e regra de negocio;
- reunir referencias de DOM no inicio do fluxo;
- usar `abort early` se a tela nao tiver os elementos esperados;
- consumir `window.SIOPShared` em vez de recriar helper local;
- manter a inicializacao em uma funcao `init`;
- registrar listeners apenas uma vez;
- preferir composicao de funcoes pequenas em vez de uma funcao gigante.

### Estrutura recomendada

- `IIFE`
- `'use strict'`
- aliases de `window.SIOPShared`, se necessario
- refs principais de DOM ou `buildContext()`
- helpers privadas
- `init()`
- bootstrap com `DOMContentLoaded`, quando for modulo autonomo

### Regras praticas

- se o modulo depende de elementos que so existem em uma tela, ele nao deve ir para `main.js`;
- se duas telas usam a mesma solucao tecnica, avaliar extracao para `shared/`;
- se o fluxo crescer demais, quebrar por responsabilidade antes de mexer na regra de negocio;
- nomes devem refletir responsabilidade, nao detalhe de implementacao.

### Fluxo recomendado de refatoracao

- copiar a logica para o novo lugar;
- ligar o novo modulo;
- testar o fluxo;
- so depois apagar o codigo antigo.

## Bootstrap

O `main.js` deve usar:

- lista unica de inicializadores;
- `initApp()` como ponto de entrada.

## Regra Final

- Se resolve `como` fazer: `shared`
- Se resolve `quando` fazer: modulo
- Se e global: `main.js`

## Direcao Atual

O proximo passo natural da arquitetura e continuar o split do dominio de ocorrencias/acessos em arquivos menores por responsabilidade, sem mexer cedo demais na regra de negocio.

## Roadmap Atual

Como o projeto ainda esta em fase de construcao, a prioridade atual nao e blindagem por testes, e sim consolidacao estrutural e padrao de desenvolvimento.

### Sprint 1 - Consolidacao da arquitetura

- revisar o split de `ocorrencias-*`;
- remover residuos restantes do `main.js`;
- consolidar convencoes de modulo, dominio e `shared`.

### Sprint 2 - Padronizacao e estabilidade

- adicionar `eslint`;
- avaliar uso de `prettier`;
- iniciar a substituicao de `alert(...)` por feedback visual padronizado.

### Sprint 3 - Backend com a mesma disciplina

- revisar servicos duplicados;
- reduzir utilitarios redundantes;
- padronizar contratos JSON;
- mover configuracoes sensiveis para `.env`, se ainda houver algo exposto.

### Sprint 4 - Qualidade de produto

- revisar UX e responsividade de `atendimento` e `manejo`;
- adicionar estados de carregamento;
- melhorar validacao visual;
- padronizar feedback de erro e sucesso.

### Sprint 5 - Blindagem final

- criar testes minimos para os fluxos criticos;
- cobrir `create/edit` de ocorrencias;
- cobrir `create` de acesso;
- cobrir `atendimento`;
- cobrir `manejo`;
- cobrir `exportacao`.

## Prioridade Atual

A leitura honesta do momento e:

- a base arquitetural principal ja existe;
- o foco imediato e consolidar padrao e terminar a construcao;
- testes entram como ultima etapa dessa fase, para evitar retrabalho enquanto a estrutura ainda muda.
