//
// Created by arken on 08/09/2026.
//

#include <iostream>

using namespace std;


int buscaSequencial(int vetor[], int tamanho, int chave) {
    for (int i = 0; i < tamanho; i++) {
        if (vetor[i] == chave) {
            return i;
        }
    }
    return -1;
}

int main() {
    int vetor[] = {3, 5, 98, 37, 6, 54, 21, 20, 18, 38, 17, 1};
    int tamanho = 12;
    int chave = 32;

    cout << "Buscando pelo numero: " << chave << endl;

    int resposta = buscaSequencial(vetor, tamanho, chave);
    if (resposta != -1) {
        cout<< "Elemento encontrado na posicao " << resposta+1 << endl;
    }else {
        std::cout << "Elemento nao encontrado";
    }
}