//
// Created by arken on 25/08/2026.
//

#include <iostream>

using namespace std;

void imprimirVetor(int vetor[], int tamanho) {
    cout << "[ ";

    for (int i = 0; i < tamanho; i++) {
        cout << vetor[i] << " ";
    }

    cout << "]" << endl;
}

void insertionSort(int vetor[], int tamanho) {
    for (int i = 1; i < tamanho; i++) {
        int chave = vetor[i];
        int j = i - 1;

        cout << "\nInserindo o elemento: " << chave << endl;

        while (j >= 0 && vetor[j] > chave) {
            vetor[j + 1] = vetor[j];
            j--;

            cout << "Deslocamento: ";
            imprimirVetor(vetor, tamanho);
        }

        vetor[j + 1] = chave;

        cout << "Depois da insercao: ";
        imprimirVetor(vetor, tamanho);
    }
}

void selectionSort(int vetor[], int tamanho) {
    for (int i = 0; i < tamanho - 1; i++) {
        int posicaoMenor = i;

        cout << "\n--- Passada " << i + 1 << " ---\n";
        cout << "Parte ainda nao ordenada: ";

        for (int k = i; k < tamanho; k++) {
            cout << vetor[k] << " ";
        }
        cout << endl;

        for (int j = i + 1; j < tamanho; j++) {
            if (vetor[j] < vetor[posicaoMenor]) {
                posicaoMenor = j;
            }
        }
        cout << "Menor elemento encontrado: "
             << vetor[posicaoMenor] << endl;

        if (posicaoMenor != i) {
            int temp = vetor[i];
            vetor[i] = vetor[posicaoMenor];
            vetor[posicaoMenor] = temp;

            cout << "Depois da troca: ";
            imprimirVetor(vetor, tamanho);
        }
        else {
            cout << "Nenhuma troca necessaria.\n";
        }
    }
}

void bubbleSort(int vetor[], int tamanho) {
    for (int i = 0; i < tamanho - 1; i++) {
        cout << "\n--- Passada " << i + 1 << " ---\n";

        bool houveTroca = false;

        for (int j = 0; j < tamanho - i - 1; j++) {
            if (vetor[j] > vetor[j + 1]) {

                int temp = vetor[j];
                vetor[j] = vetor[j + 1];
                vetor[j + 1] = temp;

                houveTroca = true;

                cout << "Troca: ";
                imprimirVetor(vetor, tamanho);
            }
        }

        if (!houveTroca) {
            cout << "Nenhuma troca foi realizada.\n";
            break;
        }
    }
}

void Merge(int vetor[], int inicio, int fim, int meio, int tamanho) {
    int tamanhoDireita = fim - meio;
    int tamanhoEsquerda = meio - inicio + 1;

    int* esquerda = new int[tamanhoEsquerda];
    int* direita = new int[tamanhoDireita];

    for (int j = 0; j < tamanhoDireita; j++) {
        direita[j] = vetor[meio + j + 1];
    }

    for (int i = 0; i < tamanhoEsquerda; i++) {
        esquerda[i] = vetor[inicio + i];
    }

    int i = 0;
    int j = 0;
    int k = inicio;

    //INTERCALAÇÃO
    while (i < tamanhoEsquerda && j < tamanhoDireita) {
        if (esquerda[i] <= direita[j]) {
            vetor[k] = esquerda[i];
            i++;
        }else {
            vetor[k] = direita[j];
            j++;
        }

        k++;
    }

    while (i < tamanhoEsquerda) {
        vetor[k] = esquerda[i];
        i++;
        k++;
    }

    while (j < tamanhoDireita) {
        vetor[k] = direita[j];
        j++;
        k++;
    }

    delete[] esquerda;
    delete[] direita;

    cout << "Intercalando [" << inicio << " - " << fim << "]: " << endl;
    imprimirVetor(vetor, tamanho);
}

void mergeSort(int vetor[], int inicio, int fim, int tamanho) {
    if (inicio >= fim) {
        return;
    }

    int meio = inicio + (fim - inicio) / 2;

    //ORDENAR METADE ESQUERDA
    mergeSort(vetor, inicio, meio, tamanho);

    //ORDENAR METADE DIREITA
    mergeSort(vetor, meio+1, fim, tamanho);

    //ORDENAR OS DOIS ELEMENTOS
    Merge(vetor, inicio, fim, meio, tamanho);
}

int particionar(int vetor[], int inicio, int fim, int tamanho) {
    int pivo = vetor[fim];

    int i = inicio - 1;

    cout << "\n Pivo escolhido: " << pivo << endl;

    for (int j = inicio; j < fim; j++) {
        if ( vetor[j] <= pivo) {
            i++;

            int temp = vetor[i];
            vetor[i] = vetor[j];
            vetor[j] = temp;

            cout << "Troca: ";
            imprimirVetor(vetor, tamanho);
        }
    }

    int temp = vetor[i + 1];
    vetor[i + 1] = vetor[fim];
    vetor[fim] = temp;

    cout << "Coloquei o pivo: ";
    imprimirVetor(vetor, tamanho);

    cout << "Posicao final do pivo: " << i+1 << endl;

    return i + 1;
}

void quickSort(int vetor[], int inicio, int fim, int tamanho) {
    if (inicio < fim) {
        int posicaoPivo = particionar(vetor, inicio, fim, tamanho);

        //ORDENAR PRA ESQUERDA
        quickSort(vetor, inicio, posicaoPivo-1, tamanho);

        //ORDENAR PRA DIREITA
        quickSort(vetor, posicaoPivo+1, fim, tamanho);
    }
}

int main() {
    int vetorOriginal[6] = {8, 3, 5, 1, 9, 2};
    int vetor[6];

    for (int i = 0; i < 6; i++) {
        vetor[i] = vetorOriginal[i];
    }

    // cout << "==== MERGE SORT ===\n";
    // cout <<  "Vetor original: ";
    // imprimirVetor(vetor, 6);
    //
    // mergeSort(vetor, 0, 5, 6);
    //
    // cout << "vetor ordenado: ";
    // imprimirVetor(vetor, 6);
    // cout<< "\n\n\n";

        cout << "==== QUICK SORT ===\n";
    cout <<  "Vetor original: ";
    imprimirVetor(vetor, 6);

    quickSort(vetor, 0, 5, 6);

    cout << "vetor ordenado: ";
    imprimirVetor(vetor, 6);
    cout<< "\n\n\n";

    // cout << "===== INSERTION SORT =====\n";
    // cout <<  "Vetor original: ";
    // imprimirVetor(vetor, 5);
    //
    // insertionSort(vetor, 5);
    //
    // cout << "vetor ordenado: ";
    // imprimirVetor(vetor, 5);
    // cout<< "\n\n\n";
    //
    //
    //
    // for (int i = 0; i < 5; i++) {
    //     vetor[i] = vetorOriginal[i];
    // }
    // cout << "===== SELECTION SORT =====\n";
    // cout <<  "Vetor original: ";
    // imprimirVetor(vetor, 5);
    //
    // selectionSort(vetor, 5);
    //
    // cout << "vetor ordenado: ";
    // imprimirVetor(vetor, 5);
    // cout<< "\n\n\n";
    //
    //
    //
    // for (int i = 0; i < 5; i++) {
    //     vetor[i] = vetorOriginal[i];
    // }
    // cout << "===== BUBBLE SORT =====\n";
    // cout <<  "Vetor original: ";
    // imprimirVetor(vetor, 5);
    //
    // bubbleSort(vetor, 5);
    //
    // cout << "vetor ordenado: ";
    // imprimirVetor(vetor, 5);
}