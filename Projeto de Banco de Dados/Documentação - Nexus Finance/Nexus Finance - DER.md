# Nexus Finance - DER documentation
## Summary

- [Introduction](#introduction)
- [Database Type](#database-type)
- [Table Structure](#table-structure)
	- [usuarios](#usuarios)
	- [categorias](#categorias)
	- [formas_pagamento](#formas_pagamento)
	- [recorrencias](#recorrencias)
	- [contas](#contas)
	- [investimentos](#investimentos)
	- [transacoes](#transacoes)
	- [aportes](#aportes)
	- [historico_valor](#historico_valor)
- [Relationships](#relationships)
- [Database Diagram](#database-diagram)

## Introduction

## Database type

- **Database system:** PostgreSQL
## Table structure

### usuarios

| Name        | Type          | Settings                      | References                    | Note                           |
|-------------|---------------|-------------------------------|-------------------------------|--------------------------------|
| **id** | BIGSERIAL | 🔑 PK, null |  | |
| **nome** | VARCHAR(150) | not null |  | |
| **email** | VARCHAR(255) | not null, unique |  | |
| **senha** | VARCHAR(255) | not null |  | |
| **data_criacao** | TIMESTAMP | not null, default: NOW() |  | | 


### categorias

| Name        | Type          | Settings                      | References                    | Note                           |
|-------------|---------------|-------------------------------|-------------------------------|--------------------------------|
| **id** | BIGSERIAL | 🔑 PK, null |  | |
| **nome** | VARCHAR(100) | not null |  | |
| **tipo** | VARCHAR(20) | not null |  | | 


### formas_pagamento

| Name        | Type          | Settings                      | References                    | Note                           |
|-------------|---------------|-------------------------------|-------------------------------|--------------------------------|
| **id** | BIGSERIAL | 🔑 PK, null |  | |
| **nome** | VARCHAR(100) | not null, unique |  | | 


### recorrencias

| Name        | Type          | Settings                      | References                    | Note                           |
|-------------|---------------|-------------------------------|-------------------------------|--------------------------------|
| **id** | BIGSERIAL | 🔑 PK, null |  | |
| **tipo** | VARCHAR(20) | not null |  | |
| **intervalo** | INTEGER | not null, default: 1 |  | |
| **data_inicio** | DATE | not null |  | |
| **data_fim** | DATE | null |  | | 


### contas

| Name        | Type          | Settings                      | References                    | Note                           |
|-------------|---------------|-------------------------------|-------------------------------|--------------------------------|
| **id** | BIGSERIAL | 🔑 PK, null |  | |
| **usuario_id** | BIGINT | not null | fk_contas_usuario_id_usuarios | |
| **tipo** | VARCHAR(20) | not null |  | |
| **nome_entidade** | VARCHAR(255) | not null |  | |
| **valor** | NUMERIC(15,2) | not null |  | |
| **data_vencimento** | DATE | not null |  | |
| **data_pagamento** | DATE | null |  | |
| **status** | VARCHAR(20) | not null |  | |
| **descricao** | TEXT | null |  | |
| **recorrencia_id** | BIGINT | null | fk_contas_recorrencia_id_recorrencias | | 


### investimentos

| Name        | Type          | Settings                      | References                    | Note                           |
|-------------|---------------|-------------------------------|-------------------------------|--------------------------------|
| **id** | BIGSERIAL | 🔑 PK, null |  | |
| **usuario_id** | BIGINT | not null | fk_investimentos_usuario_id_usuarios | |
| **nome_ativo** | VARCHAR(150) | not null |  | |
| **tipo** | VARCHAR(50) | not null |  | | 


### transacoes

| Name        | Type          | Settings                      | References                    | Note                           |
|-------------|---------------|-------------------------------|-------------------------------|--------------------------------|
| **id** | BIGSERIAL | 🔑 PK, null |  | |
| **usuario_id** | BIGINT | not null | fk_transacoes_usuario_id_usuarios | |
| **tipo** | VARCHAR(20) | not null |  | |
| **valor** | NUMERIC(15,2) | not null |  | |
| **data** | DATE | not null |  | |
| **descricao** | VARCHAR(255) | not null |  | |
| **categoria_id** | BIGINT | not null | fk_transacoes_categoria_id_categorias | |
| **forma_pagamento_id** | BIGINT | not null | fk_transacoes_forma_pagamento_id_formas_pagamento | |
| **origem_conta_id** | BIGINT | null | fk_transacoes_origem_conta_id_contas | |
| **observacoes** | TEXT | null |  | | 


### aportes

| Name        | Type          | Settings                      | References                    | Note                           |
|-------------|---------------|-------------------------------|-------------------------------|--------------------------------|
| **id** | BIGSERIAL | 🔑 PK, null |  | |
| **investimento_id** | BIGINT | not null | fk_aportes_investimento_id_investimentos | |
| **valor** | NUMERIC(15,2) | not null |  | |
| **data** | DATE | not null |  | | 


### historico_valor

| Name        | Type          | Settings                      | References                    | Note                           |
|-------------|---------------|-------------------------------|-------------------------------|--------------------------------|
| **id** | BIGSERIAL | 🔑 PK, null |  | |
| **investimento_id** | BIGINT | not null | fk_historico_valor_investimento_id_investimentos | |
| **valor_atual** | NUMERIC(15,2) | not null |  | |
| **data** | DATE | not null |  | | 


## Relationships

- **contas to usuarios**: many_to_one
- **contas to recorrencias**: many_to_one
- **investimentos to usuarios**: many_to_one
- **transacoes to usuarios**: many_to_one
- **transacoes to categorias**: many_to_one
- **transacoes to formas_pagamento**: many_to_one
- **transacoes to contas**: many_to_one
- **aportes to investimentos**: many_to_one
- **historico_valor to investimentos**: many_to_one

## Database Diagram

```mermaid
erDiagram
	contas }o--|| usuarios : references
	contas }o--|| recorrencias : references
	investimentos }o--|| usuarios : references
	transacoes }o--|| usuarios : references
	transacoes }o--|| categorias : references
	transacoes }o--|| formas_pagamento : references
	transacoes }o--|| contas : references
	aportes }o--|| investimentos : references
	historico_valor }o--|| investimentos : references

	usuarios {
		BIGSERIAL id
		VARCHAR(150) nome
		VARCHAR(255) email
		VARCHAR(255) senha
		TIMESTAMP data_criacao
	}

	categorias {
		BIGSERIAL id
		VARCHAR(100) nome
		VARCHAR(20) tipo
	}

	formas_pagamento {
		BIGSERIAL id
		VARCHAR(100) nome
	}

	recorrencias {
		BIGSERIAL id
		VARCHAR(20) tipo
		INTEGER intervalo
		DATE data_inicio
		DATE data_fim
	}

	contas {
		BIGSERIAL id
		BIGINT usuario_id
		VARCHAR(20) tipo
		VARCHAR(255) nome_entidade
		NUMERIC(15,2) valor
		DATE data_vencimento
		DATE data_pagamento
		VARCHAR(20) status
		TEXT descricao
		BIGINT recorrencia_id
	}

	investimentos {
		BIGSERIAL id
		BIGINT usuario_id
		VARCHAR(150) nome_ativo
		VARCHAR(50) tipo
	}

	transacoes {
		BIGSERIAL id
		BIGINT usuario_id
		VARCHAR(20) tipo
		NUMERIC(15,2) valor
		DATE data
		VARCHAR(255) descricao
		BIGINT categoria_id
		BIGINT forma_pagamento_id
		BIGINT origem_conta_id
		TEXT observacoes
	}

	aportes {
		BIGSERIAL id
		BIGINT investimento_id
		NUMERIC(15,2) valor
		DATE data
	}

	historico_valor {
		BIGSERIAL id
		BIGINT investimento_id
		NUMERIC(15,2) valor_atual
		DATE data
	}
```