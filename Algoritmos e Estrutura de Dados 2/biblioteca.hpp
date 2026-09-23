#pragma once

#include <string>
#include <vector>

struct Livro {
    int id;
    std::string titulo;
    std::string autor;
    std::string categoria;
    int anoPublicacao;
};

struct Cliente {
    int id;
    std::string nome;
    std::string email;
    std::string telefone;
};

struct Emprestimo {
    int id;
    int clienteId;
    int livroId;
    std::string dataObtencao;
    std::string dataRetorno;
};

int numeroAleatorio(int minimo, int maximo);

std::vector<Livro> gerarLivros(int quantidade);

std::vector<Cliente> gerarClientes(int quantidade);

std::vector<Emprestimo> gerarEmprestimos(
    int quantidade,
    int quantidadeClientes,
    int quantidadeLivros
);

bool salvarBibliotecaJson(
    const std::string& caminho,
    const std::vector<Livro>& livros,
    const std::vector<Cliente>& clientes,
    const std::vector<Emprestimo>& emprestimos
);