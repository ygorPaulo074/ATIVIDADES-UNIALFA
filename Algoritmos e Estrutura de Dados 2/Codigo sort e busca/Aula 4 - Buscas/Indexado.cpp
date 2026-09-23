//
// Created by arken on 08/09/2026.
//

#include "iostream"
using namespace std;

struct Index {
    int valor;
    int posicao;
};

int buscaIndexada(int vetor[], int tamanho, Index indice[], int tamanhoIndice, int valor) {
    int inicio = 0;
    int fim = tamanho -1;

    for (int i = 0; i < tamanhoIndice; i++) {
        if (indice[i].valor >  valor) {
            break;
        }

        inicio = indice[i].posicao;
    }

    for (int i = 0; i < tamanhoIndice; i++) {
        if (indice[i].posicao > inicio) {
            fim = indice[i].posicao;
            break;
        }
    }

    for (int i = inicio; i <= fim && i < tamanho; i++) {
        if (vetor[i] == valor) {
            return i;
        }
    }

    return -1;
}

int main() {
    int vetor[] = {3, 5, 8, 10, 12, 15, 18, 22, 25, 27, 30, 33, 36, 40, 42};
    int tamanho = 15;
    int chave = 20;

    Index indice[] = {
        {3, 0},
        {10, 3},
        {22, 7},
        {30, 10},
        {40, 13}
    };

    int tamanhoIndice = 5;

    cout << "Buscando pelo numero: " << chave << endl;

    int resposta = buscaIndexada(vetor, tamanho, indice, tamanhoIndice, chave);
    if (resposta != -1) {
        cout<< "Elemento encontrado na posicao " << resposta+1 << endl;
    }else {
        cout << "Elemento nao encontrado";
    }
}