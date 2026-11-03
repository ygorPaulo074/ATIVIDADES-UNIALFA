#include <iostream>
#include <string>

// Estrutura da arvore AVL

struct No {
    int chave;
    int altura = 1; // folha tem altura 1
    No* esquerda = nullptr;
    No* direita = nullptr;
    int fb;  // fator de balanceamento

        /* Explicacao do Fator de Balanceamento (fb):
        o fator de balanceamento e um ponto de medida para avaliar o equilibrio de uma arvore binaria. 
        Ele e calculado como a diferenca entre a altura da subarvore esquerda e a altura da subarvore direita de um no especifico. 
        O fator de balanceamento pode assumir valores negativos, positivos ou zero, dependendo da estrutura da arvore.
        Exemplo: 
        Arvore Binaria:
                10
               /  \
              5    15
             / \     \
            3   7     20

        - Para o no 10, a altura da subarvore esquerda e 2 (nos 5, 3 e 7) e a altura da subarvore direita e 2 (nos 15 e 20).
        - Portanto, o fator de balanceamento para o no 10 e 2 - 2 = 0, indicando que a arvore esta equilibrada nesse ponto.
        - Para o no 5, a altura da subarvore esquerda e 1 (no 3) e a altura da subarvore direita e 1 (no 7).
        - Portanto, o fator de balanceamento para o no 5 e 1 - 1 = 0, indicando que a arvore esta equilibrada nesse ponto.
        - Para o no 15, a altura da subarvore esquerda e 0 (nao ha nos) e a altura da subarvore direita e 1 (no 20).
        - Portanto, o fator de balanceamento para o no 15 e 0 - 1 = -1, indicando que a arvore esta ligeiramente desequilibrada para a direita nesse ponto.
        - O fator de balanceamento provoca uma rotacao na arvore quando o desequilibrio atinge um valor absoluto maior que 1, 
        - Ou seja, quando o fator de balanceamento e menor que -1 ou maior que 1.
        */
};

int altura(No* no_atual) {
    if (no_atual != nullptr)
        return no_atual->altura;   // no existe: devolve a altura guardada nele
    else
        return 0;  
}

int fatorBalanceamento(No* no_atual) {
    if (!no_atual) return 0;
    return altura(no_atual->esquerda) - altura(no_atual->direita);
}

void atualizarAltura(No* no_atual) {
    int altura_esq = altura(no_atual->esquerda);
    int altura_dir = altura(no_atual->direita);

    if (altura_esq > altura_dir)
        no_atual->altura = 1 + altura_esq;
    else
        no_atual->altura = 1 + altura_dir;
}

No* rotacaoDireita(No* no_desbalanceado) {
    No* novo_topo = no_desbalanceado->esquerda;

    no_desbalanceado->esquerda = novo_topo->direita;
    novo_topo->direita = no_desbalanceado;

    atualizarAltura(no_desbalanceado);   // primeiro quem desceu
    atualizarAltura(novo_topo);          // depois quem subiu
    return novo_topo;
}

No* rotacaoEsquerda(No* no_desbalanceado) {
    No* novo_topo = no_desbalanceado->direita;

    no_desbalanceado->direita = novo_topo->esquerda;
    novo_topo->esquerda = no_desbalanceado;

    atualizarAltura(no_desbalanceado);
    atualizarAltura(novo_topo);
    return novo_topo;
}

No* balancear(No* no_atual) {

    atualizarAltura(no_atual);
    int fator = fatorBalanceamento(no_atual);

    // Pesado a esquerda
    if (fator > 1) {
        if (fatorBalanceamento(no_atual->esquerda) < 0)            // Esquerda-Direita
            no_atual->esquerda = rotacaoEsquerda(no_atual->esquerda);
        return rotacaoDireita(no_atual);                      // Esquerda-Esquerda
    }

    // Pesado a direita
    if (fator < -1) {
        if (fatorBalanceamento(no_atual->direita) > 0)            // Direita-Esquerda
            no_atual->direita = rotacaoDireita(no_atual->direita);
        return rotacaoEsquerda(no_atual);                     // Direita-Direita
    }

    return no_atual;   // ja estava equilibrado
};

No* encontrarMinimo(No* no_atual) {
    while (no_atual && no_atual->esquerda)
        no_atual = no_atual->esquerda;
    return no_atual;
}

No* inserir(No* raiz, int chave) {
    // Funcao para inserir um no na Arvore Binaria
    if (raiz != nullptr) {
        if (chave < raiz->chave) {
            raiz->esquerda = inserir(raiz->esquerda, chave);
        } else if (chave > raiz->chave) {
            raiz->direita = inserir(raiz->direita, chave);
        }
    } else {
        raiz = new No();
        raiz->chave = chave;
    }

    return balancear(raiz); // Reequilibrar a arvore apos a insercao do no
};

No* destruir(No* no_atual, int chave) {
    if (!no_atual) return nullptr;

    if (chave < no_atual->chave) {
        no_atual->esquerda = destruir(no_atual->esquerda, chave);
    } else if (chave > no_atual->chave) {
        no_atual->direita = destruir(no_atual->direita, chave);
    } else {
        // No a ser removido encontrado
        if (!no_atual->esquerda) {
            No* temp = no_atual->direita;
            delete no_atual;
            return temp;
        } else if (!no_atual->direita) {
            No* temp = no_atual->esquerda;
            delete no_atual;
            return temp;
        }

        // No com dois filhos
        No* temp = encontrarMinimo(no_atual->direita);
        no_atual->chave = temp->chave;
        no_atual->direita = destruir(no_atual->direita, temp->chave);
    }

    return balancear(no_atual);
}

bool buscar(No* no_atual, int valor) {
    if (!no_atual) return false;
    if (valor == no_atual->chave) return true;

    if (valor < no_atual->chave)
        return buscar(no_atual->esquerda, valor);
    return buscar(no_atual->direita, valor);
}

//Made by Claude
// Imprime a arvore "deitada": direita em cima, esquerda embaixo
// "/--" liga um filho da direita ao pai (abaixo dele), "\--" liga um filho da esquerda ao pai (acima dele)
void imprimirArvore(No* no_atual, std::string prefixo = "", bool eh_raiz = true, bool eh_direita = false) {
    if (!no_atual) return;

    std::string recuo_dir = eh_raiz ? "" : (eh_direita ? "    " : "|   ");
    std::string recuo_esq = eh_raiz ? "" : (eh_direita ? "|   " : "    ");
    std::string ligacao = eh_raiz ? "" : (eh_direita ? "/-- " : "\\-- ");

    imprimirArvore(no_atual->direita, prefixo + recuo_dir, false, true);
    std::cout << prefixo << ligacao << no_atual->chave << std::endl;
    imprimirArvore(no_atual->esquerda, prefixo + recuo_esq, false, false);
}

//Made by Claude
int main () {
    No* raiz = nullptr; // Inicializa a raiz da arvore
    int opcao = 0;

    do {
        std::cout << "\nArvore AVL - Insercao e Remocao de Nos" << std::endl;
        std::cout << "----------------------------------------" << std::endl;
        std::cout << "O que deseja fazer?" << std::endl;
        std::cout << "1. Inserir no" << std::endl;
        std::cout << "2. Remover no" << std::endl;
        std::cout << "3. Ver arvore balanceada" << std::endl;
        std::cout << "4. Buscar no" << std::endl;
        std::cout << "0. Sair" << std::endl;
        std::cout << "Opcao: ";

        if (!(std::cin >> opcao)) break; // entrada invalida ou fim da entrada

        int chave;
        switch (opcao) {
            case 1:
                std::cout << "Chave a inserir: ";
                std::cin >> chave;
                raiz = inserir(raiz, chave);
                break;
            case 2:
                std::cout << "Chave a remover: ";
                std::cin >> chave;
                raiz = destruir(raiz, chave);
                break;
            case 3:
                if (raiz)
                    imprimirArvore(raiz);
                else
                    std::cout << "Arvore vazia." << std::endl;
                break;
            case 4:
                std::cout << "Chave a buscar: ";
                std::cin >> chave;
                std::cout << "Chave " << chave
                          << (buscar(raiz, chave) ? " encontrada." : " nao encontrada.") << std::endl;
                break;
            case 0:
                break;
            default:
                std::cout << "Opcao invalida." << std::endl;
        }
    } while (opcao != 0);

    return 0;
}
