//
// Created by arken on 08/09/2026.
//
#include <iostream>
using namespace std;

int buscaBinaria(int vetor[], int chave, int inicio, int fim){
    if (inicio > fim) {
        return -1;
    }

    int meio = (inicio + fim) / 2;

    if (vetor[meio] == chave ) {
        return meio;
    }

    if (vetor[meio] > chave) {
        return buscaBinaria(vetor, chave, inicio, meio);
    }

    return buscaBinaria(vetor, chave, meio +1, fim);
}

int main() {
    int vetor[] = {1, 3, 5, 10, 13, 15, 25, 26, 35, 42, 44, 46, 58, 70};
    int tamanho = 14;
    int chave = 85;

    cout << "Buscando pelo numero: " << chave << endl;

    int resposta = buscaBinaria(vetor, chave, 0, tamanho -1);
    if (resposta != -1) {
        cout<< "Elemento encontrado na posicao " << resposta+1 << endl;
    }else {
        cout << "Elemento nao encontrado";
    }
}