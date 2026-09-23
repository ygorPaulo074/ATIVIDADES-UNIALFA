//
// Created by arken on 08/09/2026.
//

#include <iostream>

using namespace std;

int buscaBinaria(int vetor[], int tamanho, int chave) {
    int inicio = 0;
    int fim = tamanho - 1;

    while (inicio <= fim) {
        int meio = (inicio + fim) / 2;

        if (vetor[meio] == chave) {
            return meio;
        }

        if (vetor[meio] < chave) {
            inicio = meio + 1;
        } else {
            fim = meio - 1;
        }
    }
    return -1;
}

int main() {
    int vetor[] = {1, 3, 5, 10, 13, 15, 25, 26, 35, 42, 44, 46, 58, 70};
    int tamanho = 14;
    int chave = 5;

    cout << "Buscando pelo numero: " << chave << endl;

    int resposta = buscaBinaria(vetor, tamanho, chave);
    if (resposta != -1) {
        cout<< "Elemento encontrado na posicao " << resposta+1 << endl;
    }else {
        cout << "Elemento nao encontrado";
    }
}