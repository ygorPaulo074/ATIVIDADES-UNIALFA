'''
Esta atividade consiste num sistema simples de cadastros, 
de acordo com a criatividade do aluno.

Alunos participantes:
Paulo Ygor Oliveira Araújo
André Felipe dos Santos
Data: 27-10-2025
'''

# Criação de Lista vazia para armazenar clientes
clientes = []

# Criação de Classe - Cliente

class Cliente:
    # Construtor
    def __init__(self):
        
    # Atributos
        self.nome = ""
        self.idade = 0
        self.email = ""
        # Observe que temos antes de cada nome de atributo o 'self.'
        # Isto indica que estes atributos pertencem ao objeto que será criado a partir desta classe.

    # Métodos
    def cadastrar(self, nome, idade, email):
        self.nome = nome
        self.idade = idade
        self.email = email
        print("Cliente cadastrado com sucesso!")
    # Aqui, o método 'cadastrar' recebe três parâmetros e atribui seus valores aos atributos do objeto.

    def exibir_dados(self):
        print("Nome:", self.nome)
        print("Idade:", self.idade)
        print("Email:", self.email)
    # O método 'exibir_dados' imprime os dados do cliente na tela.

    # O programa consiste em criar um objeto da classe Cliente,
    # cadastrar um cliente e exibir seus dados.
    # O responsável por criar o objeto será o usuário do sistema, 
    # que fará isso através de inputs no console.

# Bloco principal do programa

# O if __name__ == "__main__": garante que o código abaixo só será executado
# quando o arquivo for executado diretamente, e não quando for importado como módulo.

if __name__ == "__main__":
    # Criação do objeto cliente
    cliente1 = Cliente()

print("Bem-vindo ao sistema de cadastro de clientes!")

at_work = True

while at_work:  
    # Inicialização do programa

    print("O que deseja fazer?")
    print("1 - Cadastrar cliente")
    print("2 - Exibir os clientes cadastrados")
    print("3 - Sair")
    escolha = input("Digite o número da opção desejada: ")

    # Estrutura condicional para escolher a ação
    if escolha == "1":
        nome = input("Digite o nome do cliente: ")  # Input do nome
        idade = int(input("Digite a idade do cliente: ")) # Input da idade
        email = input("Digite o email do cliente: ") # Input do email
        cliente1.cadastrar(nome, idade, email) # Chamada do método cadastrar
        clientes.append(cliente1) # Adiciona o cliente à lista de clientes

    elif escolha == "2":

        if not clientes: # Verifica se a lista de clientes está vazia
            print("Nenhum cliente cadastrado.")

        else: # Exibe os dados de todos os clientes cadastrados

            for index, cliente in enumerate(clientes):
                # Explicação: enumerate() retorna tanto o índice quanto o objeto cliente
                # index é usado para mostrar o número do cliente na lista
                # cliente é o objeto da classe Cliente
                # Resumo da linha:
                # Para cada cliente na lista de clientes, exiba seus dados

                print(f"\nCliente {index + 1}:")
                cliente.exibir_dados() # Chamada do método exibir_dados

    elif escolha == "3": # Opção para sair do programa
        print("Saindo do sistema. Até mais!")
        at_work = False
        break

    else:
        print("Opção inválida. Por favor, escolha 1,2 ou 3.")