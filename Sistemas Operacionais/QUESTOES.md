Exercícios Teóricos – Processos

1 Qual a diferença entre programa e processo?
2 Quais são os estados de um processo e quando ocorrem as transições?
3 O que contém um Process Control Block (PCB)?
4 O que acontece com os recursos de um processo quando ele termina?
5 Qual a diferença entre fork() e exec() no UNIX?
6 Como funciona a hierarquia de processos em UNIX?
7 Compare memória compartilhada e troca de mensagens (IPC).
8 Cite exemplos de chamadas de sistema usadas em IPC.
9 Por que é importante que o sistema operacional faça gerenciamento de processos?
10 Explique a diferença entre processos independentes e processos cooperativos.
11 O que é um processo zumbi em UNIX/Linux?
12 Explique a diferença entre chamadas bloqueantes e não bloqueantes em IPC.
13 Qual a diferença entre processo pesado (process) e thread (processo leve)?
14 Por que sistemas operacionais multiprogramados precisam de troca de contexto (context switch)?
15 Cite vantagens e desvantagens da comunicação via memória compartilhada.

Respostas: 

1- Um programa é um software desenvolvido por uma pessoa, que executa vários processos em prol de um resultado final. 
    Um processo é uma ação que o programa requisita para executar seus algoritmos.

2- Um processo possui 5 estados:
    Novo: Quando acaba de ser criado, e aguarda alocação de recursos;
    Pronto: O novo processo recebeu os recursos alocados, e está pronto para ser executado;
    Executando: O processo está sendo executado na CPU;
    Bloqueado: O processo foi interrompido e aguarda um evento externo;
    Finalizado: Todas as requisições do processo foram finalizadas, e o processo está pronto.

3- PID; Contador de Programa; Registradores; Quanta memória tem; Quais arquivos usa. 

4- Os recursos alocados são liberados e o processo é enviado ao estado de Finalizado, dando espaço aos mais prioritários.

5- fork() : Cria um novo processo filho.
    exec() : Substitui um processo

6- No Unix, todos os processos são proveientes de outro. O processo Avô(primeiro a ser ativado), é o init/systemd.

7- Na memória compartilhada, processos utilizam a mesma região da memória. É mais rápido, porém exige sincronização.
    Troca de dados é quando processos trocam dados via sistema operacional (filas, pipes, sockets); mais simples e seguro, mas geralmente mais lento.

8- Memória compartilhada: shmget, shmat, shmdt.

    Troca de mensagens: msgget, msgsnd, msgrcv.

    Pipes/Sockets: pipe, send, recv, socket.

9- Evita que processos monopolizem recursos.

    Garante isolamento e segurança.

    Controla concorrência e sincronização.

    Faz escalonamento para melhor desempenho.
10- Independentes trabalham sozinhos, sem interagir com outros processos, já os cooperativos interagem entre si, podendo afetar uns aos     outros.

11- Processo que já terminou, mas cujo pai ainda não coletou seu status de término. O PCB permanece na tabela de processos até o pai ler.

12- Bloqueante: Processo espera a operação de completar.
    Não Bloqueante: Recebe retorno imediato, independente do resultado da operação, permitindo que o processo continue trabalhando.

13- Processo: Tem espaço de endereçamento e recursos independentes.
    Thread: É uma unidade de execução dentro de um processo, que compartilha memória e recursos do processo.

14- Para alternar entre processos e compartilhar a CPU, permitindo um uso eficiente do sistema. 

15- Vantagens: É rápida e boa para grande volumes de dados.
    Desvantagens: Exige sincronização manual, é mais complexa de programar e pode gerar condições de corrida.

