# Banco de Dados do Projeto

## Tecnologia atual

O banco em uso no projeto e um SQLite local, armazenado no arquivo `db.sqlite3`.

A aplicacao utiliza:

- Django ORM para mapear os models para o banco
- migrations do Django para criar e evoluir o schema
- SQLite como implementacao fisica atual

## Como a modelagem aparece neste projeto

### Nivel conceitual

No nivel conceitual, o banco foi pensado para representar as regras de negocio do sistema. As entidades principais identificadas no projeto sao:

- ocorrencias
- acessos de terceiros
- atendimentos
- manejo
- pessoas
- contatos
- testemunhas
- anexos
- fotos
- assinaturas
- geolocalizacoes

### Nivel logico

No nivel logico, essas entidades foram organizadas em tabelas relacionadas entre si por chaves estrangeiras, relacoes muitos-para-muitos e relacoes genericas.

Os principais tipos de relacionamento encontrados foram:

- `ForeignKey`
- `ManyToMany`
- relacoes genericas com `content_type_id` e `object_id`

### Nivel fisico

No nivel fisico, toda essa estrutura esta implementada no arquivo `db.sqlite3`, com tabelas, indices e constraints gerados pelas migrations do Django.

## Tabelas principais do dominio

As tabelas de negocio existentes hoje no banco sao:

- `siop_ocorrencia`
- `siop_acessoterceiros`
- `siop_controleatendimento`
- `siop_manejo`
- `siop_pessoa`
- `siop_contato`
- `siop_testemunha`
- `siop_controleatendimento_testemunhas`
- `siop_anexo`
- `siop_foto`
- `siop_assinatura`
- `siop_geolocalizacao`

Tambem existem as tabelas padrao do Django para autenticacao, permissoes, sessoes, log administrativo e migrations.

## Estrutura por tabela

### `siop_ocorrencia`

Essa tabela registra ocorrencias operacionais.

Campos principais:

- `id`
- `tipo_pessoa`
- `data_ocorrencia`
- `natureza`
- `tipo`
- `area`
- `local`
- `cftv`
- `bombeiro_civil`
- `status`
- `descricao`
- `criado_por_id`
- `modificado_por_id`

Quantidade atual de registros:

- `2`

### `siop_acessoterceiros`

Essa tabela registra a entrada e saida de terceiros.

Campos principais:

- `id`
- `entrada`
- `saida`
- `empresa`
- `placa_veiculo`
- `p1`
- `descricao_acesso`
- `pessoa_id`
- `criado_por_id`
- `modificado_por_id`

Quantidade atual de registros:

- `2`

### `siop_controleatendimento`

Essa tabela registra os atendimentos operacionais.

Campos principais:

- `id`
- `tipo_pessoa`
- `pessoa_id`
- `contato_id`
- `area_atendimento`
- `local`
- `data_atendimento`
- `tipo_ocorrencia`
- `possui_acompanhante`
- `acompanhante_pessoa_id`
- `grau_parentesco`
- `doenca_preexistente`
- `descricao_doenca`
- `alergia`
- `descricao_alergia`
- `plano_saude`
- `nome_plano_saude`
- `numero_carteirinha`
- `primeiros_socorros`
- `atendimentos`
- `responsavel_atendimento`
- `seguiu_passeio`
- `houve_remocao`
- `transporte`
- `encaminhamento`
- `hospital`
- `medico_responsavel`
- `crm`
- `descricao`
- `hash_atendimento`

Quantidade atual de registros:

- `0`

### `siop_manejo`

Essa tabela registra os dados de manejo.

Campos principais:

- `id`
- `data_hora`
- `classe`
- `nome_cientifico`
- `nome_popular`
- `estagio_desenvolvimento`
- `area_captura`
- `local_captura`
- `descricao_local`
- `importancia_medica`
- `realizado_manejo`
- `responsavel_manejo`
- `area_soltura`
- `local_soltura`
- `descricao_local_soltura`
- `acionado_orgao_publico`
- `orgao_publico`
- `numero_boletim_ocorrencia`
- `motivo_acionamento`
- `observacoes`

Quantidade atual de registros:

- `6`

### `siop_pessoa`

Essa tabela armazena pessoas vinculadas aos modulos do sistema.

Campos principais:

- `id`
- `nome`
- `documento`
- `orgao_emissor`
- `sexo`
- `data_nascimento`
- `nacionalidade`

### `siop_contato`

Essa tabela armazena dados de contato.

Campos principais:

- `id`
- `telefone`
- `email`
- `endereco`
- `cidade`
- `pais`

### `siop_testemunha`

Essa tabela representa testemunhas e aproveita a estrutura de pessoa.

Campos principais:

- `pessoa_ptr_id`
- `contato_id`

### `siop_controleatendimento_testemunhas`

Essa e a tabela de associacao entre atendimentos e testemunhas.

Ela implementa o relacionamento muitos-para-muitos entre:

- `siop_controleatendimento`
- `siop_testemunha`

### `siop_anexo`

Essa tabela armazena anexos genericos ligados a diferentes entidades.

Campos principais:

- `id`
- `content_type_id`
- `object_id`
- `nome_arquivo`
- `mime_type`
- `tamanho`
- `arquivo`
- `hash_arquivo`
- `hash_arquivo_atual`

Quantidade atual de registros:

- `1`

### `siop_foto`

Essa tabela armazena fotos genericas ligadas a diferentes entidades.

Campos principais:

- `id`
- `content_type_id`
- `object_id`
- `tipo`
- `nome_arquivo`
- `mime_type`
- `tamanho`
- `arquivo`
- `hash_arquivo`
- `hash_arquivo_atual`

Quantidade atual de registros:

- `10`

### `siop_assinatura`

Essa tabela armazena assinaturas.

Campos principais:

- `id`
- `content_type_id`
- `object_id`
- `nome_arquivo`
- `mime_type`
- `tamanho`
- `arquivo`
- `hash_arquivo`
- `hash_arquivo_atual`
- `hash_assinatura`

Quantidade atual de registros:

- `0`

### `siop_geolocalizacao`

Essa tabela armazena coordenadas geograficas associadas a diferentes entidades.

Campos principais:

- `id`
- `content_type_id`
- `object_id`
- `tipo`
- `latitude`
- `longitude`
- `hash_geolocalizacao`

Quantidade atual de registros:

- `10`

## Relacionamentos importantes

Os relacionamentos mais importantes observados no banco atual sao:

- `siop_acessoterceiros.pessoa_id` aponta para `siop_pessoa.id`
- `siop_controleatendimento.pessoa_id` aponta para `siop_pessoa.id`
- `siop_controleatendimento.contato_id` aponta para `siop_contato.id`
- `siop_controleatendimento.acompanhante_pessoa_id` aponta para `siop_pessoa.id`
- `siop_testemunha.contato_id` aponta para `siop_contato.id`
- `siop_controleatendimento_testemunhas` liga atendimentos a testemunhas
- `siop_anexo`, `siop_foto`, `siop_assinatura` e `siop_geolocalizacao` usam relacao generica com `content_type_id` e `object_id`

## Indices observados

O banco possui indices para acelerar consultas nos principais campos operacionais.

Entre eles:

- ocorrencias por data, natureza, tipo, area, local, status e bombeiro civil
- acessos de terceiros por entrada, saida, P1 e pessoa
- atendimentos por data, tipo de pessoa, tipo de ocorrencia, area de atendimento e pessoa
- manejo por data, classe, area de captura, local de captura e situacao do manejo
- tabelas genericas com indices em hash e `content_type_id`

## Constraints e regras persistidas

No banco atual tambem foram identificadas regras importantes persistidas no schema:

- validacao de unicidade para geolocalizacao por objeto e tipo
- regra para impedir saida anterior a entrada em `siop_acessoterceiros`
- unicidade de assinatura por objeto
- uso de hashes para rastreabilidade de anexos, fotos, assinaturas e geolocalizacao

## Estado atual do banco local

Hoje, o banco local possui dados nas seguintes tabelas principais:

- `siop_ocorrencia`: `2`
- `siop_acessoterceiros`: `2`
- `siop_manejo`: `6`
- `siop_anexo`: `1`
- `siop_foto`: `10`
- `siop_geolocalizacao`: `10`

Hoje, o banco local ainda nao possui registros em:

- `siop_controleatendimento`
- `siop_assinatura`

## Resumo

O banco de dados atual do projeto esta estruturado para sustentar quatro frentes principais do sistema:

- ocorrencias
- acesso de terceiros
- atendimento
- manejo

Ele tambem possui uma camada generica de evidencias e apoio, composta por:

- anexos
- fotos
- assinaturas
- geolocalizacao
- pessoas
- contatos
- testemunhas
