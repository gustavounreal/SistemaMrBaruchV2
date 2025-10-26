from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType


class Command(BaseCommand):
    help = 'Cria os grupos Compliance e Consultor com permissões adequadas'

    def handle(self, *args, **kwargs):
        # Criar grupo Compliance
        compliance_group, created = Group.objects.get_or_create(name='compliance')
        if created:
            self.stdout.write(self.style.SUCCESS('Grupo "compliance" criado com sucesso'))
        else:
            self.stdout.write(self.style.WARNING('Grupo "compliance" já existe'))
        
        # Adicionar permissões ao grupo Compliance
        from compliance.models import AnaliseCompliance, GestaoDocumentosPosVenda
        compliance_ct = ContentType.objects.get_for_model(AnaliseCompliance)
        gestao_ct = ContentType.objects.get_for_model(GestaoDocumentosPosVenda)
        
        compliance_permissions = Permission.objects.filter(
            content_type__in=[compliance_ct, gestao_ct]
        )
        compliance_group.permissions.set(compliance_permissions)
        
        # Criar grupo Consultor
        consultor_group, created = Group.objects.get_or_create(name='consultor')
        if created:
            self.stdout.write(self.style.SUCCESS('Grupo "consultor" criado com sucesso'))
        else:
            self.stdout.write(self.style.WARNING('Grupo "consultor" já existe'))
        
        # Adicionar permissões ao grupo Consultor
        from vendas.models import PreVenda
        from marketing.models import Lead
        pre_venda_ct = ContentType.objects.get_for_model(PreVenda)
        lead_ct = ContentType.objects.get_for_model(Lead)
        
        consultor_permissions = Permission.objects.filter(
            content_type__in=[pre_venda_ct, lead_ct],
            codename__in=['view_prevenda', 'change_prevenda', 'view_lead']
        )
        consultor_group.permissions.set(consultor_permissions)
        
        self.stdout.write(self.style.SUCCESS('Grupos configurados com sucesso!'))
        self.stdout.write(self.style.SUCCESS('Use: python manage.py criar_grupos_compliance'))
