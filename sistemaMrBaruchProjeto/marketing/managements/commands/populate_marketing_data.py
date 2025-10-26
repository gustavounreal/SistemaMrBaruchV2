from marketing.models import CategoriaMotivo, MotivoContato

def populate_data():
    # Define categories
    categories = [
        {"nome": "PRAZO CURTO / RISCO ALTO", "descricao": ""},
        {"nome": "PRAZO MEDIO / RISCO MÉDIO", "descricao": ""},
        {"nome": "PRAZO MEDIO / RISCO MÉDIO - BAIXO", "descricao": ""},
    ]

    # Define motives and profiles
    motives_profiles = [
        {"categoria": "PRAZO CURTO / RISCO ALTO", "tipo": "MOTIVO", "nome": "CONSEGUIR EMPREGO"},
        {"categoria": "PRAZO CURTO / RISCO ALTO", "tipo": "MOTIVO", "nome": "ALUGAR UM IMÓVEL"},
        {"categoria": "PRAZO CURTO / RISCO ALTO", "tipo": "MOTIVO", "nome": "CARTÃO DE CRÉDITO"},
        {"categoria": "PRAZO CURTO / RISCO ALTO", "tipo": "PERFIL", "nome": "DESESPERANÇA/URGÊNCIA"},
        {"categoria": "PRAZO MEDIO / RISCO MÉDIO", "tipo": "MOTIVO", "nome": "CONSÓRCIO"},
        {"categoria": "PRAZO MEDIO / RISCO MÉDIO", "tipo": "PERFIL", "nome": "PLANEJAMENTO INICIAL"},
        {"categoria": "PRAZO MEDIO / RISCO MÉDIO - BAIXO", "tipo": "MOTIVO", "nome": "FINANCIAMENTO"},
        {"categoria": "PRAZO MEDIO / RISCO MÉDIO - BAIXO", "tipo": "PERFIL", "nome": "PLANEJADOR/ANSIOSO"},
    ]

    # Populate categories
    for cat in categories:
        categoria, created = CategoriaMotivo.objects.get_or_create(nome=cat["nome"], defaults={"descricao": cat["descricao"]})
        if created:
            print(f"Categoria criada: {categoria.nome}")

    # Populate motives and profiles
    for item in motives_profiles:
        categoria = CategoriaMotivo.objects.get(nome=item["categoria"])
        motivo, created = MotivoContato.objects.get_or_create(
            categoria=categoria,
            nome=item["nome"],
            defaults={"tipo": item["tipo"]}
        )
        if created:
            print(f"Motivo/Perfil criado: {motivo.nome} ({motivo.tipo})")

if __name__ == "__main__":
    populate_data()