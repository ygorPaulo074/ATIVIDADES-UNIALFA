#include <iostream>
#include <vector>
#include "biblioteca.hpp"

int* criarPonteiro();
int particionar(int vetor[], int inicio, int fim);

//para generalizar a busca para outros tipos de dados
template <typename Tipo, typename Chave>

int buscaSequencial(const std::vector<Tipo>& vetor, Chave chave, Chave Tipo::* campo) {

    for(std::size_t i = 0; i < vetor.size(); ++i) {
        if(vetor[i].*campo == chave) {
            return static_cast<int>(i);
        }
    }
    return -1;
}

template <typename Tipo, typename Chave>

int buscaBinaria(const std::vector<Tipo>& vetor, Chave chave, Chave Tipo::* campo) {
    int inicio = 0;
    int fim = vetor.size() - 1;

    while (inicio <= fim) {
        int meio = inicio + (fim - inicio) / 2;

        if (vetor[meio].*campo == chave) {
            return static_cast<int>(meio);
        }

        if (vetor[meio].*campo < chave) {
            inicio = meio + 1;
        } else {
            fim = meio - 1;
        }
    }

    return -1;
}

template <typename Tipo, typename Chave>
std::vector<int> vetorizador( const std::vector<Tipo>& vetor, const Chave& chave, Chave Tipo::* campo) {
    std::vector<int> encontrados;

    for (const Tipo& item : vetor) {
        if (item.*campo == chave) {
            encontrados.push_back(item.id);
        }
    }

    return encontrados;
}

void quickSort(int vetor[], int inicio, int fim){
    if (inicio < fim) {
        int posicaoPivo = particionar(vetor, inicio, fim);

        //ORDENAR PRA ESQUERDA
        quickSort(vetor, inicio, posicaoPivo - 1);

        //ORDENAR PRA DIREITA
        quickSort(vetor, posicaoPivo + 1, fim);
    }
}

int particionar(int vetor[], int inicio, int fim) {
    int pivo = vetor[fim];

    int i = inicio - 1;

    for (int j = inicio; j < fim; j++) {
        if (vetor[j] <= pivo) {
            i++;

            int temp = vetor[i];
            vetor[i] = vetor[j];
            vetor[j] = temp;

        }
    }

    int temp = vetor[i + 1];
    vetor[i + 1] = vetor[fim];
    vetor[fim] = temp;

    return i + 1;
}

int main() {
    std::vector<Livro> livros = gerarLivros(10000);
    std::vector<Cliente> clientes = gerarClientes(1000);
    std::vector<Emprestimo> emprestimos = gerarEmprestimos(5000, clientes.size(), livros.size());

    if (salvarBibliotecaJson("biblioteca.json", livros, clientes, emprestimos)) {
        std::cout << "Dados exportados para biblioteca.json\n";
    } else {
        std::cerr << "Nao foi possivel criar biblioteca.json\n";
    }

    int opcao;
    int tipoArray = 0;
    std::vector<int> itensEncontrados;

    do {
        tipoArray = 0;
        itensEncontrados.clear();

        std::cout << "\n=== PAINEL DA BIBLIOTECA ===\n"
                  << "1. Buscar sequencialmente\n"
                  << "2. Buscar via busca binaria\n"
                  << "3. Ordenar livros\n"
                  << "4. Ordenar clientes\n"
                  << "5. Ordenar emprestimos\n"
                  << "0. Sair\n"
                  << "Escolha uma opcao: ";
        std::cin >> opcao;

        switch (opcao) {
            case 1: {
                int tipo;
                int chave;

                std::cout << "\nO que deseja buscar?\n"
                          << "1. Livro\n"
                          << "2. Cliente\n"
                          << "3. Emprestimo\n"
                          << "Escolha: ";
                std::cin >> tipo;

                std::cout << "Digite o ID: ";
                std::cin >> chave;

                switch (tipo) {
                    case 1: {
                        int resultado = buscaSequencial(
                            livros, chave, &Livro::id
                        );

                        if (resultado == -1) {
                            std::cout << "Livro nao encontrado.\n";
                        } else {
                            std::cout << "\nLivro encontrado na posicao "
                                      << resultado + 1 << ":\n"
                                      << "ID: " << livros[resultado].id << '\n'
                                      << "Titulo: " << livros[resultado].titulo << '\n'
                                      << "Autor: " << livros[resultado].autor << '\n'
                                      << "Categoria: " << livros[resultado].categoria << '\n'
                                      << "Ano de Publicacao: "
                                      << livros[resultado].anoPublicacao << '\n';
                        }
                        break;
                    }

                    case 2: {
                        int resultado = buscaSequencial(
                            clientes, chave, &Cliente::id
                        );

                        if (resultado == -1) {
                            std::cout << "Cliente nao encontrado.\n";
                        } else {
                            std::cout << "\nCliente encontrado na posicao "
                                      << resultado + 1 << ":\n"
                                      << "ID: " << clientes[resultado].id << '\n'
                                      << "Nome: " << clientes[resultado].nome << '\n'
                                      << "E-mail: " << clientes[resultado].email << '\n'
                                      << "Telefone: " << clientes[resultado].telefone << '\n';
                        }
                        break;
                    }

                    case 3: {
                        int resultado = buscaSequencial(
                            emprestimos, chave, &Emprestimo::id
                        );

                        if (resultado == -1) {
                            std::cout << "Emprestimo nao encontrado.\n";
                        } else {
                            std::cout << "\nEmprestimo encontrado na posicao "
                                      << resultado + 1 << ":\n"
                                      << "ID: " << emprestimos[resultado].id << '\n'
                                      << "ID do cliente: "
                                      << emprestimos[resultado].clienteId << '\n'
                                      << "ID do livro: "
                                      << emprestimos[resultado].livroId << '\n'
                                      << "Data de obtencao: "
                                      << emprestimos[resultado].dataObtencao << '\n'
                                      << "Data de retorno: "
                                      << emprestimos[resultado].dataRetorno << '\n';
                        }
                        break;
                    }

                    default:
                        std::cout << "Tipo invalido.\n";
                }
                break;
            }

            case 2: {
                int chave;
                int tipo;

                std::cout << "\nA busca binaria sera feita por ID.\n"
                          << "1. Livro\n"
                          << "2. Cliente\n"
                          << "3. Emprestimo\n"
                          << "Escolha: ";
                std::cin >> tipo;

                std::cout << "Digite o ID: ";
                std::cin >> chave;

                switch (tipo) {
                    case 1: {
                        int resultado = buscaBinaria(
                            livros, chave, &Livro::id
                        );

                        if (resultado == -1) {
                            std::cout << "Livro nao encontrado.\n";
                        } else {
                            std::cout << "\nLivro encontrado na posicao "
                                      << resultado + 1 << ":\n"
                                      << "ID: " << livros[resultado].id << '\n'
                                      << "Titulo: " << livros[resultado].titulo << '\n'
                                      << "Autor: " << livros[resultado].autor << '\n'
                                      << "Categoria: " << livros[resultado].categoria << '\n'
                                      << "Ano de Publicacao: "
                                      << livros[resultado].anoPublicacao << '\n';
                        }
                        break;
                    }

                    case 2: {
                        int resultado = buscaBinaria(
                            clientes, chave, &Cliente::id
                        );

                        if (resultado == -1) {
                            std::cout << "Cliente nao encontrado.\n";
                        } else {
                            std::cout << "\nCliente encontrado na posicao "
                                      << resultado + 1 << ":\n"
                                      << "ID: " << clientes[resultado].id << '\n'
                                      << "Nome: " << clientes[resultado].nome << '\n'
                                      << "E-mail: " << clientes[resultado].email << '\n'
                                      << "Telefone: " << clientes[resultado].telefone << '\n';
                        }
                        break;
                    }

                    case 3: {
                        int resultado = buscaBinaria(
                            emprestimos, chave, &Emprestimo::id
                        );

                        if (resultado == -1) {
                            std::cout << "Emprestimo nao encontrado.\n";
                        } else {
                            std::cout << "\nEmprestimo encontrado na posicao "
                                      << resultado + 1 << ":\n"
                                      << "ID: " << emprestimos[resultado].id << '\n'
                                      << "ID do cliente: "
                                      << emprestimos[resultado].clienteId << '\n'
                                      << "ID do livro: "
                                      << emprestimos[resultado].livroId << '\n'
                                      << "Data de obtencao: "
                                      << emprestimos[resultado].dataObtencao << '\n'
                                      << "Data de retorno: "
                                      << emprestimos[resultado].dataRetorno << '\n';
                        }
                        break;
                    }

                    default:
                        std::cout << "Tipo invalido.\n";
                }
                break;
            }

            case 3: {
                std::string categoria;
                std::cout << "Digite a categoria dos livros: ";
                std::cin >> categoria;

                itensEncontrados = vetorizador(
                    livros, categoria, &Livro::categoria
                );
                tipoArray = 1;

                if (!itensEncontrados.empty()) {
                    quickSort(
                        itensEncontrados.data(),
                        0,
                        static_cast<int>(itensEncontrados.size()) - 1
                    );
                }
                break;
            }

            case 4: {
                int clienteId;
                std::cout << "Digite o ID do cliente: ";
                std::cin >> clienteId;

                itensEncontrados = vetorizador(
                    clientes, clienteId, &Cliente::id
                );
                tipoArray = 2;

                if (!itensEncontrados.empty()) {
                    quickSort(
                        itensEncontrados.data(),
                        0,
                        static_cast<int>(itensEncontrados.size()) - 1
                    );
                }
                break;
            }

            case 5: {
                int clienteId;
                std::cout << "Digite o ID do cliente dos emprestimos: ";
                std::cin >> clienteId;

                itensEncontrados = vetorizador(
                    emprestimos, clienteId, &Emprestimo::clienteId
                );
                tipoArray = 3;

                if (!itensEncontrados.empty()) {
                    quickSort(
                        itensEncontrados.data(),
                        0,
                        static_cast<int>(itensEncontrados.size()) - 1
                    );
                }
                break;
            }

            case 0:
                std::cout << "Encerrando.\n";
                break;

            default:
                std::cout << "Opcao invalida.\n";
        }

        if (tipoArray != 0) {
            if (itensEncontrados.empty()) {
                std::cout << "Nenhum item encontrado.\n";
            } else if (tipoArray == 1) {
                std::cout << "\n=== LIVROS ORDENADOS POR ID ===\n";

                for (int id : itensEncontrados) {
                    int posicao = buscaSequencial(livros, id, &Livro::id);
                    const Livro& livro = livros[posicao];

                    std::cout << "ID: " << livro.id
                              << " | Titulo: " << livro.titulo
                              << " | Autor: " << livro.autor
                              << " | Categoria: " << livro.categoria
                              << " | Ano: " << livro.anoPublicacao << '\n';
                }
            } else if (tipoArray == 2) {
                std::cout << "\n=== CLIENTES ORDENADOS POR ID ===\n";

                for (int id : itensEncontrados) {
                    int posicao = buscaSequencial(clientes, id, &Cliente::id);
                    const Cliente& cliente = clientes[posicao];

                    std::cout << "ID: " << cliente.id
                              << " | Nome: " << cliente.nome
                              << " | E-mail: " << cliente.email
                              << " | Telefone: " << cliente.telefone << '\n';
                }
            } else {
                std::cout << "\n=== EMPRESTIMOS ORDENADOS POR ID ===\n";

                for (int id : itensEncontrados) {
                    int posicao = buscaSequencial(
                        emprestimos, id, &Emprestimo::id
                    );
                    const Emprestimo& emprestimo = emprestimos[posicao];

                    std::cout << "ID: " << emprestimo.id
                              << " | Cliente: " << emprestimo.clienteId
                              << " | Livro: " << emprestimo.livroId
                              << " | Obtencao: " << emprestimo.dataObtencao
                              << " | Retorno: " << emprestimo.dataRetorno << '\n';
                }
            }
        }

    } while (opcao != 0);

    return 0;
}