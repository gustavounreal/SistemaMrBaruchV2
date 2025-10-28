from django.core.management.base import BaseCommand
from marketing.models import CategoriaMotivo, MotivoContato, OrigemLead

class Command(BaseCommand):
    help = 'Popula as tabelas CategoriaMotivo, MotivoContato e OrigemLead com dados iniciais.'

    def handle(self, *args, **options):
        categorias = [
            {"nome": "PRAZO CURTO / RISCO ALTO", "descricao": ""},
            {"nome": "PRAZO MEDIO / RISCO MÉDIO", "descricao": ""},
            {"nome": "PRAZO MEDIO / RISCO MÉDIO - BAIXO", "descricao": ""},
        ]

        motivos_perfis = [
            # PRAZO CURTO / RISCO ALTO
            {"categoria": "PRAZO CURTO / RISCO ALTO", "tipo": "MOTIVO", "nome": "CONSEGUIR EMPREGO"},
            {"categoria": "PRAZO CURTO / RISCO ALTO", "tipo": "MOTIVO", "nome": "ALUGAR UM IMÓVEL"},
            {"categoria": "PRAZO CURTO / RISCO ALTO", "tipo": "MOTIVO", "nome": "CARTÃO DE CRÉDITO"},
            {"categoria": "PRAZO CURTO / RISCO ALTO", "tipo": "MOTIVO", "nome": "COMPRA PARCELADA"},
            {"categoria": "PRAZO CURTO / RISCO ALTO", "tipo": "MOTIVO", "nome": "EMPRÉSTIMO"},
            {"categoria": "PRAZO CURTO / RISCO ALTO", "tipo": "PERFIL", "nome": "DESESPERANÇA/URGÊNCIA"},
            {"categoria": "PRAZO CURTO / RISCO ALTO", "tipo": "PERFIL", "nome": "PRESSÃO POR ESTABILIDADE"},
            {"categoria": "PRAZO CURTO / RISCO ALTO", "tipo": "PERFIL", "nome": "IMPULSIVIDADE/CONSUMO"},
            {"categoria": "PRAZO CURTO / RISCO ALTO", "tipo": "PERFIL", "nome": "CONSUMO IMEDIATO"},
            {"categoria": "PRAZO CURTO / RISCO ALTO", "tipo": "PERFIL", "nome": "DESESPERO/INSTABILIDADE"},
            # PRAZO MEDIO / RISCO MÉDIO
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO", "tipo": "MOTIVO", "nome": "CONSÓRCIO"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO", "tipo": "MOTIVO", "nome": "CRÉDITO"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO", "tipo": "MOTIVO", "nome": "ABRIR EMPRESA"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO", "tipo": "MOTIVO", "nome": "TROCA DE CARRO"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO", "tipo": "MOTIVO", "nome": "VIAGEM"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO", "tipo": "PERFIL", "nome": "PLANEJAMENTO INICIAL"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO", "tipo": "PERFIL", "nome": "CONSCIÊNCIA/RECUPERAÇÃO"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO", "tipo": "PERFIL", "nome": "EMPREENDEDOR EM FASE INICIAL"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO", "tipo": "PERFIL", "nome": "OBJETIVO MATERIAL PLANEJADO"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO", "tipo": "PERFIL", "nome": "RECOMPENSA PESSOAL"},
            # PRAZO MEDIO / RISCO MÉDIO - BAIXO
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO - BAIXO", "tipo": "MOTIVO", "nome": "FINANCIAMENTO"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO - BAIXO", "tipo": "MOTIVO", "nome": "EXEMPLO FAMILIAR"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO - BAIXO", "tipo": "MOTIVO", "nome": "EVITAR PROBLEMAS FUTUROS"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO - BAIXO", "tipo": "MOTIVO", "nome": "TROCA DE CARRO MIGRAÇÃO"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO - BAIXO", "tipo": "PERFIL", "nome": "PLANEJAMENTO INICIAL"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO - BAIXO", "tipo": "PERFIL", "nome": "CONSCIÊNCIA/RECUPERAÇÃO"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO - BAIXO", "tipo": "PERFIL", "nome": "EMPREENDEDOR EM FASE INICIAL"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO - BAIXO", "tipo": "PERFIL", "nome": "OBJETIVO MATERIAL PLANEJADO"},
            {"categoria": "PRAZO MEDIO / RISCO MÉDIO - BAIXO", "tipo": "PERFIL", "nome": "PLANEJADOR/ANSIOSO"},
        ]

        origens_lead = [
            {"nome": "Instagram"},
            {"nome": "Facebook"},
            {"nome": "Indicação"},
            {"nome": "Google"},
            {"nome": "WhatsApp"},
            {"nome": "Site"},
            {"nome": "Outro"},
        ]

        # Popula categorias
        for cat in categorias:
            categoria, created = CategoriaMotivo.objects.get_or_create(nome=cat["nome"], defaults={"descricao": cat["descricao"]})
            if created:
                self.stdout.write(self.style.SUCCESS(f"Categoria criada: {categoria.nome}"))
            else:
                self.stdout.write(f"Categoria já existe: {categoria.nome}")

        # Popula motivos e perfis
        for item in motivos_perfis:
            categoria = CategoriaMotivo.objects.get(nome=item["categoria"])
            motivo, created = MotivoContato.objects.get_or_create(
                categoria=categoria,
                texto=item["nome"],
                defaults={"tipo": item["tipo"]}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Motivo/Perfil criado: {motivo.texto} ({motivo.tipo})"))
            else:
                self.stdout.write(f"Motivo/Perfil já existe: {motivo.texto} ({motivo.tipo})")

        # Popula origens de lead
        for origem in origens_lead:
            obj, created = OrigemLead.objects.get_or_create(nome=origem["nome"])
            if created:
                self.stdout.write(self.style.SUCCESS(f"Origem de Lead criada: {obj.nome}"))
            else:
                self.stdout.write(f"Origem de Lead já existe: {obj.nome}")