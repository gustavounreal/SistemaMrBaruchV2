from django.db import models
from django.conf import settings


ESTADO_CIVIL_CHOICES = [
    ('solteiro', 'Solteiro(a)'),
    ('casado', 'Casado(a)'),
    ('divorciado', 'Divorciado(a)'),
    ('viuvo', 'Viúvo(a)'),
]

class Cliente(models.Model):
    lead = models.OneToOneField('marketing.Lead', on_delete=models.CASCADE, related_name='cliente')

    # Dados complementares
    rg = models.CharField(max_length=20, blank=True)
    data_nascimento = models.DateField(null=True, blank=True)
    idade = models.IntegerField(null=True, blank=True)
    nacionalidade = models.CharField(max_length=50, blank=True, default='Brasileiro(a)')
    cep = models.CharField(max_length=10, blank=True, null=True)
    rua = models.CharField(max_length=255, blank=True, null=True)
    numero = models.CharField(max_length=10, blank=True, null=True)
    bairro = models.CharField(max_length=100, blank=True, null=True)
    cidade = models.CharField(max_length=100, blank=True, null=True)
    estado = models.CharField(max_length=2, blank=True, null=True)
    estado_civil = models.CharField(max_length=20, choices=ESTADO_CIVIL_CHOICES, blank=True)    
    profissao = models.CharField(max_length=100, blank=True)
    pontuacao_score = models.IntegerField(null=True, blank=True, default=0)

    # Relacionamentos e controle
    captador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='clientes_captados')
    consultor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='clientes_consultor')
    
    # Usuário para acesso à área do cliente
    usuario_portal = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='cliente_portal',
        help_text="Usuário criado automaticamente para acesso à área do cliente"
    )

    # Status do processo
    cadastro_completo = models.BooleanField(default=False)
    ficha_associativa = models.BooleanField(default=False)
    boletos_enviados = models.BooleanField(default=False)
    primeiro_levantamento = models.BooleanField(default=False)
    documentacao_coletada = models.BooleanField(default=False)
    cliente_app = models.BooleanField(default=False)
    nada_consta_entregue = models.BooleanField(default=False)
    segundo_levantamento = models.BooleanField(default=False)
    
    # ========== DADOS PARA NOTA FISCAL ==========
    razao_social = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text="Razão Social (obrigatório para CNPJ)"
    )
    
    inscricao_municipal = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Inscrição Municipal (necessário para PJ prestador de serviço)"
    )

    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.lead.nome_completo
