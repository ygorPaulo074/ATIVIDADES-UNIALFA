prim_b = 9
segun_b = 8
terc_b = 7
quart_b = 6

media = (prim_b + segun_b + terc_b + quart_b) / 4

if media >= 7:
    print("Aprovado")
elif media >= 5:
    print("Recuperação")
else:
    print("Reprovado")
print("Média:", media)

