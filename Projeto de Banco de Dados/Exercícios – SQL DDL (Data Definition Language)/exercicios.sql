-- EXERCÍCIOS COM CREATE TABLE --

create table if not exists PROFESSORES (
	id_professor int primary key,
	nome varchar(100) not null,
	email varchar(150) unique,
	data_contratacao date
);

create table if not exists DISCIPLINA (
	id_disciplina int primary key,
	nome_disciplina varchar(100) not null,
	carga_horaria int,
	id_professor int references PROFESSORES(id_professor)
);

create table if not exists TURMAS (
	id_turma int primary key,
	id_disciplina int references DISCIPLINA(id_disciplina),
	semestre varchar(10) not null,
	ano int not null
);

-- EXERCÍCIOS COM ALTER TABLE --

--EXERCÍCIO 4
alter table PROFESSORES add column telefone varchar(20) unique;
--EXERCÍCIO 5
alter table PROFESSORES alter column nome type varchar(150);
--EXERCÍCIO 6
alter table DISCIPLINA add constraint chk_carga_horaria check (carga_horaria>0);

-- EXERCÍCIOS COM DROP -- 

--EXERCÍCIO 7
alter table PROFESSORES drop column telefone;
--EXERCÍCIO 8
alter table DISCIPLINA drop constraint chk_carga_horaria;
--EXERCÍCIO 9
drop table TURMAS;

--EXERCÍCIO 10 --

create table if not exists ALUNOS (
	id_aluno int primary key,
	nome varchar not null,
	cpf varchar unique not null,
	data_nascimento date check (data_nascimento <=CURRENT_DATE),
	email varchar unique,
	status varchar default 'ATIVO'
);

