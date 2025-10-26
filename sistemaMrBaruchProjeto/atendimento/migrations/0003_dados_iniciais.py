# atendimento/migrations/0003_dados_iniciais.py
from django.db import migrations

def criar_dados_iniciais(apps, schema_editor):
    OrigemContato = apps.get_model('atendimento', 'OrigemContato')
    CategoriaMotivo = apps.get_model('atendimento', 'CategoriaMotivo')
    MotivoContato = apps.get_model('atendimento', 'MotivoContato')
    
    # Origens de contato
    origens = [
        ('Instagram', 1),
        ('Facebook', 2),
        ('TikTok', 3),
        ('YouTube', 4),
        ('Google', 5),
        ('Indicação', 6),
        ('Site', 7),
        ('WhatsApp', 8),
        ('Outros', 9),
    ]
    
    for nome, ordem in origens:
        OrigemContato.objects.get_or_create(nome=nome, defaults={'ordem': ordem})
    
    # Categorias de motivo
    categorias = [
        ('PRAZO CURTO / RISCO ALTO', 'Clientes com urgência e alto risco', 1),
        ('PRAZO MÉDIO / RISCO MÉDIO', 'Clientes com planejamento médio prazo', 2),
        ('PRAZO MÉDIO / RISCO MÉDIO-BAIXO', 'Clientes com bom planejamento', 3),
    ]
    
    for nome, descricao, ordem in categorias:
        cat, _ = CategoriaMotivo.objects.get_or_create(
            nome=nome, 
            defaults={'descricao': descricao, 'ordem': ordem}
        )
    
    # Motivos de contato
    motivos_data = [
        # PRAZO CURTO / RISCO ALTO
        ('PRAZO CURTO / RISCO ALTO', 'MOTIVO', 'Conseguir Emprego', 1),
        ('PRAZO CURTO / RISCO ALTO', 'MOTIVO', 'Alugar um Imóvel', 2),
        ('PRAZO CURTO / RISCO ALTO', 'MOTIVO', 'Cartão de Crédito', 3),
        ('PRAZO CURTO / RISCO ALTO', 'MOTIVO', 'Compra Parcelada', 4),
        ('PRAZO CURTO / RISCO ALTO', 'MOTIVO', 'Empréstimo', 5),
        ('PRAZO CURTO / RISCO ALTO', 'PERFIL', 'Desesperança/Urgência', 1),
        ('PRAZO CURTO / RISCO ALTO', 'PERFIL', 'Pressão por Estabilidade', 2),
        ('PRAZO CURTO / RISCO ALTO', 'PERFIL', 'Impulsividade/Consumo', 3),
        ('PRAZO CURTO / RISCO ALTO', 'PERFIL', 'Consumo Imediato', 4),
        ('PRAZO CURTO / RISCO ALTO', 'PERFIL', 'Desespero/Instabilidade', 5),
        
        # PRAZO MÉDIO / RISCO MÉDIO
        ('PRAZO MÉDIO / RISCO MÉDIO', 'MOTIVO', 'Consórcio', 1),
        ('PRAZO MÉDIO / RISCO MÉDIO', 'MOTIVO', 'Crédito', 2),
        ('PRAZO MÉDIO / RISCO MÉDIO', 'MOTIVO', 'Abrir Empresa', 3),
        ('PRAZO MÉDIO / RISCO MÉDIO', 'MOTIVO', 'Troca de Carro', 4),
        ('PRAZO MÉDIO / RISCO MÉDIO', 'MOTIVO', 'Viagem', 5),
        ('PRAZO MÉDIO / RISCO MÉDIO', 'PERFIL', 'Planejamento Inicial', 1),
        ('PRAZO MÉDIO / RISCO MÉDIO', 'PERFIL', 'Consciência/Recuperação', 2),
        ('PRAZO MÉDIO / RISCO MÉDIO', 'PERFIL', 'Empreendedor em Fase Inicial', 3),
        ('PRAZO MÉDIO / RISCO MÉDIO', 'PERFIL', 'Objetivo Material Planejado', 4),
        ('PRAZO MÉDIO / RISCO MÉDIO', 'PERFIL', 'Recompensa Pessoal', 5),
        
        # PRAZO MÉDIO / RISCO MÉDIO-BAIXO
        ('PRAZO MÉDIO / RISCO MÉDIO-BAIXO', 'MOTIVO', 'Financiamento', 1),
        ('PRAZO MÉDIO / RISCO MÉDIO-BAIXO', 'MOTIVO', 'Exemplo Familiar', 2),
        ('PRAZO MÉDIO / RISCO MÉDIO-BAIXO', 'MOTIVO', 'Evitar Problemas Futuros', 3),
        ('PRAZO MÉDIO / RISCO MÉDIO-BAIXO', 'MOTIVO', 'Troca de Carro', 4),
        ('PRAZO MÉDIO / RISCO MÉDIO-BAIXO', 'MOTIVO', 'Migração', 5),
        ('PRAZO MÉDIO / RISCO MÉDIO-BAIXO', 'PERFIL', 'Planejamento Inicial', 1),
        ('PRAZO MÉDIO / RISCO MÉDIO-BAIXO', 'PERFIL', 'Consciência/Recuperação', 2),
        ('PRAZO MÉDIO / RISCO MÉDIO-BAIXO', 'PERFIL', 'Empreendedor em Fase Inicial', 3),
        ('PRAZO MÉDIO / RISCO MÉDIO-BAIXO', 'PERFIL', 'Objetivo Material Planejado', 4),
        ('PRAZO MÉDIO / RISCO MÉDIO-BAIXO', 'PERFIL', 'Planejador/Ansioso', 5),
    ]
    
    for cat_nome, tipo, texto, ordem in motivos_data:
        categoria = CategoriaMotivo.objects.get(nome=cat_nome)
        MotivoContato.objects.get_or_create(
            categoria=categoria,
            tipo=tipo,
            texto=texto,
            defaults={'ordem': ordem}
        )

class Migration(migrations.Migration):
    dependencies = [
        ('atendimento', '0002_categoriamotivo_origemcontato_motivocontato_and_more'),  # Ajuste para a migration anterior
    ]
    
    operations = [
        migrations.RunPython(criar_dados_iniciais),
    ]