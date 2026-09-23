#include "biblioteca.hpp"
#include <fstream>
#include <random>

std::string escaparJson(const std::string& texto) {
    std::string resultado;

    for (char caractere : texto) {
        if (caractere == '\\') {
            resultado += "\\\\";
        } else if (caractere == '"') {
            resultado += "\\\"";
        } else if (caractere == '\n') {
            resultado += "\\n";
        } else {
            resultado += caractere;
        }
    }

    return resultado;
}

int numeroAleatorio(int minimo, int maximo) {
    static std::random_device rd;
    static std::mt19937 gen(rd());

    std::uniform_int_distribution<> dist(minimo, maximo);

    return dist(gen);
}


// ========================================
// GERAR LIVROS
// ========================================

std::vector<Livro> gerarLivros(int quantidade) {

    std::vector<Livro> livros;

    std::vector<std::string> categorias = {
        "Fantasia",
        "Ficcao",
        "Romance",
        "Terror",
        "Historia",
        "Tecnologia",
        "Ciencia",
        "Aventura",
        "Literatura",
        "Biografia"
    };

    std::vector<std::string> autores = {
        "Machado de Assis",
        "J. R. R. Tolkien",
        "George Orwell",
        "Stephen King",
        "Clarice Lispector",
        "Jorge Amado",
        "Isaac Asimov",
        "Agatha Christie",
        "Neil Gaiman",
        "Arthur Conan Doyle"
    };

    livros.reserve(quantidade);

    for (int i = 1; i <= quantidade; i++) {

        Livro livro;

        livro.id = i;

        livro.titulo = "Livro Ficticio " + std::to_string(i);

        livro.autor = autores[numeroAleatorio(0, autores.size() - 1)];

        livro.categoria =
            categorias[numeroAleatorio(0, categorias.size() - 1)];

        livro.anoPublicacao =
            numeroAleatorio(1900, 2026);

        livros.push_back(livro);
    }

    return livros;
}


// ========================================
// GERAR CLIENTES
// ========================================

std::vector<Cliente> gerarClientes(int quantidade) {

    std::vector<Cliente> clientes;

    clientes.reserve(quantidade);

    for (int i = 1; i <= quantidade; i++) {

        Cliente cliente;

        cliente.id = i;

        cliente.nome =
            "Cliente " + std::to_string(i);

        cliente.email =
            "cliente" + std::to_string(i) + "@email.com";

        cliente.telefone =
            "(62) 99999-" +
            std::to_string(1000 + (i % 9000));

        clientes.push_back(cliente);
    }

    return clientes;
}


// ========================================
// GERAR EMPRESTIMOS
// ========================================

std::vector<Emprestimo> gerarEmprestimos(
    int quantidade,
    int quantidadeClientes,
    int quantidadeLivros
) {

    std::vector<Emprestimo> emprestimos;

    emprestimos.reserve(quantidade);

    for (int i = 1; i <= quantidade; i++) {

        Emprestimo emprestimo;

        emprestimo.id = i;

        emprestimo.clienteId =
            numeroAleatorio(1, quantidadeClientes);

        emprestimo.livroId =
            numeroAleatorio(1, quantidadeLivros);

        int diaObtencao = numeroAleatorio(1, 28);
        int mesObtencao = numeroAleatorio(1, 12);

        int diaRetorno = numeroAleatorio(1, 28);
        int mesRetorno = numeroAleatorio(1, 12);

        emprestimo.dataObtencao =
            std::to_string(diaObtencao) +
            "/" +
            std::to_string(mesObtencao) +
            "/2026";

        emprestimo.dataRetorno =
            std::to_string(diaRetorno) +
            "/" +
            std::to_string(mesRetorno) +
            "/2026";

        emprestimos.push_back(emprestimo);
    }

    return emprestimos;
}

bool salvarBibliotecaJson(
    const std::string& caminho,
    const std::vector<Livro>& livros,
    const std::vector<Cliente>& clientes,
    const std::vector<Emprestimo>& emprestimos
) {
    std::ofstream arquivo(caminho);

    if (!arquivo) {
        return false;
    }

    arquivo << "{\n  \"livros\": [\n";
    for (std::size_t i = 0; i < livros.size(); ++i) {
        const Livro& livro = livros[i];

        arquivo << "    {\"id\": " << livro.id
                << ", \"titulo\": \"" << escaparJson(livro.titulo)
                << "\", \"autor\": \"" << escaparJson(livro.autor)
                << "\", \"categoria\": \"" << escaparJson(livro.categoria)
                << "\", \"anoPublicacao\": " << livro.anoPublicacao << "}";

        if (i + 1 < livros.size()) {
            arquivo << ',';
        }
        arquivo << '\n';
    }

    arquivo << "  ],\n  \"clientes\": [\n";
    for (std::size_t i = 0; i < clientes.size(); ++i) {
        const Cliente& cliente = clientes[i];

        arquivo << "    {\"id\": " << cliente.id
                << ", \"nome\": \"" << escaparJson(cliente.nome)
                << "\", \"email\": \"" << escaparJson(cliente.email)
                << "\", \"telefone\": \"" << escaparJson(cliente.telefone)
                << "\"}";

        if (i + 1 < clientes.size()) {
            arquivo << ',';
        }
        arquivo << '\n';
    }

    arquivo << "  ],\n  \"emprestimos\": [\n";
    for (std::size_t i = 0; i < emprestimos.size(); ++i) {
        const Emprestimo& emprestimo = emprestimos[i];

        arquivo << "    {\"id\": " << emprestimo.id
                << ", \"clienteId\": " << emprestimo.clienteId
                << ", \"livroId\": " << emprestimo.livroId
                << ", \"dataObtencao\": \""
                << escaparJson(emprestimo.dataObtencao)
                << "\", \"dataRetorno\": \""
                << escaparJson(emprestimo.dataRetorno) << "\"}";

        if (i + 1 < emprestimos.size()) {
            arquivo << ',';
        }
        arquivo << '\n';
    }

    arquivo << "  ]\n}\n";
    return arquivo.good();
}
