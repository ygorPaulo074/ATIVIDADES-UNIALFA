
CREATE TABLE IF NOT EXISTS "produtos" (
	"id" serial NOT NULL UNIQUE,
	"nome" varchar(255),
	"preco" double,
	"idCategoria" int,
	PRIMARY KEY("id")
);


CREATE TABLE IF NOT EXISTS "categorias" (
	"id" serial NOT NULL UNIQUE,
	"nome" varchar(255),
	PRIMARY KEY("id")
);


CREATE TABLE IF NOT EXISTS "pedidos" (
	"id" serial NOT NULL UNIQUE,
	"cliente" int,
	"quantia" int,
	"idProduto" int,
	PRIMARY KEY("id")
);


CREATE TABLE IF NOT EXISTS "Clientes" (
	"id" serial NOT NULL UNIQUE,
	"nome" varchar(255),
	"endereco" varchar(255),
	"email" varchar(255),
	PRIMARY KEY("id")
);


ALTER TABLE "pedidos"
ADD FOREIGN KEY("idProduto") REFERENCES "produtos"("id")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "produtos"
ADD FOREIGN KEY("idCategoria") REFERENCES "categorias"("id")
ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE "pedidos"
ADD FOREIGN KEY("cliente") REFERENCES "Clientes"("id")
ON UPDATE NO ACTION ON DELETE NO ACTION;