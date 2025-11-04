from django.db import models
from django.conf import settings

class OrigemContato(models.Model):
    """Tabela para origens do lead (Instagram, Facebook, etc.)"""
    nome = models.CharField(max_length=50, unique=True)
    ativo = models.BooleanField(default=True)
    ordem = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['ordem', 'nome']
        verbose_name = "Origem de Contato"
        verbose_name_plural = "Origens de Contato"
    
    def __str__(self):
        return self.nome

class CategoriaMotivo(models.Model):
    """Categorias de motivação (Prazo Curto, Prazo Médio, etc.)"""
    nome = models.CharField(max_length=50, unique=True)
    descricao = models.TextField(blank=True)
    ordem = models.IntegerField(default=0)
    ativo = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['ordem', 'nome']
        verbose_name = "Categoria de Motivo"
        verbose_name_plural = "Categorias de Motivo"
    
    def __str__(self):
        return self.nome

class MotivoContato(models.Model):
    """Tabela para motivos e perfis emocionais"""
    TIPO_CHOICES = [
        ('MOTIVO', 'Motivo'),
        ('PERFIL', 'Perfil Emocional'),
    ]
    
    categoria = models.ForeignKey(CategoriaMotivo, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    texto = models.CharField(max_length=100)
    ativo = models.BooleanField(default=True)
    ordem = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['categoria', 'tipo', 'ordem']
        verbose_name = "Motivo de Contato"
        verbose_name_plural = "Motivos de Contato"
        unique_together = ['categoria', 'tipo', 'texto']
    
    def __str__(self):
        return f"{self.categoria} - {self.texto}"


class OrigemLead(models.Model):
    """Tabela para armazenar as origens dos leads"""
    nome = models.CharField(max_length=50, unique=True)
    ativo = models.BooleanField(default=True)
    ordem = models.IntegerField(default=0, help_text="Ordem de exibição")

    class Meta:
        ordering = ['ordem', 'nome']
        verbose_name = "Origem de Lead"
        verbose_name_plural = "Origens de Lead"

    def __str__(self):
        return self.nome    
    
from django.conf import settings
from django.db import models

class Lead(models.Model):
    fez_levantamento = models.BooleanField(default=False, help_text="Indica se o lead pagou o levantamento.")
    passou_compliance = models.BooleanField(
        default=False, 
        help_text="Indica se o lead já passou pela análise de Compliance e foi aprovado para pré-venda."
    )

    STATUS_CHOICES = [
        ('NOVO', 'Novo'),                       
        ('CONTATADO', 'Contatado'),             
        ('INTERESSADO', 'Interessado'),        
        ('LEVANTAMENTO_PENDENTE', 'Levantamento Pendente'),  
        ('LEVANTAMENTO_PAGO', 'Levantamento Pago'),
        ('EM_COMPLIANCE', 'Em Análise Compliance'),
        ('APROVADO_COMPLIANCE', 'Aprovado - Aguardando Consultor'),          
        ('QUALIFICADO', 'Qualificado'),         
        ('CONTRATADO', 'Contratado'),           
        ('PERDIDO', 'Perdido'),                 
    ]

    # --- A) Identificação e contato ---
    nome_completo = models.CharField(max_length=200)
    cpf_cnpj = models.CharField(max_length=20, blank=True, null=True)
    data_nascimento = models.DateField(blank=True, null=True, help_text="Data de nascimento do lead (opcional)")
    email = models.EmailField(blank=True, null=True)
    telefone = models.CharField(max_length=20)

    # --- B) Dados de marketing / qualificação ---
    origem = models.ForeignKey(
        'marketing.OrigemLead',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="leads"
    )
    motivo_principal = models.ForeignKey(
        'marketing.MotivoContato',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'tipo': 'MOTIVO'},
        related_name='leads_motivo'
    )
    perfil_emocional = models.ForeignKey(
        'marketing.MotivoContato',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'tipo': 'PERFIL'},
        related_name='leads_perfil'
    )
    atendente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='leads_atendimento'
    )

    captador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads_captados',
        help_text="Usuário que indicou o serviço (captador)"
    )

    # --- C) Dados operacionais / integração ---
    cliente_asaas = models.ForeignKey(
        'financeiro.ClienteAsaas',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads_associados'
    )

    status = models.CharField(
        max_length=25,
        choices=STATUS_CHOICES,
        default='NOVO'
    )
    
    # Contador de repescagens (Comercial 2)
    numero_repescagens = models.PositiveIntegerField(
        default=0,
        help_text="Quantidade de vezes que este lead foi enviado ao Comercial 2 (repescagem)"
    )

    observacoes = models.TextField(blank=True, null=True)

    data_cadastro = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Lead'
        verbose_name_plural = 'Leads'
        ordering = ['-data_cadastro']

    def __str__(self):
        return f"{self.nome_completo} ({self.status})"

    def get_cpf_cnpj_display(self):
        """Retorna o CPF ou CNPJ formatado para exibição.

        - Remove caracteres não numéricos
        - Formata CPF (XXX.XXX.XXX-XX) quando 11 dígitos
        - Formata CNPJ (XX.XXX.XXX/XXXX-XX) quando 14 dígitos
        - Retorna 'Não Informado' quando vazio
        """
        raw = self.cpf_cnpj or ''
        raw = str(raw)
        # remover qualquer caractere que não seja número
        cleaned = ''.join(ch for ch in raw if ch.isdigit())
        if not cleaned:
            return 'Não Informado'
        if len(cleaned) == 11:
            return f"{cleaned[:3]}.{cleaned[3:6]}.{cleaned[6:9]}-{cleaned[9:]}"
        if len(cleaned) == 14:
            return f"{cleaned[:2]}.{cleaned[2:5]}.{cleaned[5:8]}/{cleaned[8:12]}-{cleaned[12:]}"
        # fallback: retornar o valor original sem alteração
        return self.cpf_cnpj
    
    def incrementar_repescagens(self):
        """Incrementa o contador de repescagens do lead"""
        self.numero_repescagens += 1
        self.save(update_fields=['numero_repescagens'])
    
    def get_badge_repescagem(self):
        """Retorna badge HTML para exibir quantidade de repescagens"""
        if self.numero_repescagens == 0:
            return ''
        elif self.numero_repescagens == 1:
            return '<span class="badge bg-warning">1ª Repescagem</span>'
        elif self.numero_repescagens == 2:
            return '<span class="badge bg-danger">2ª Repescagem</span>'
        else:
            return f'<span class="badge bg-dark">{self.numero_repescagens}ª Repescagem ⚠️</span>'


class Campanha(models.Model):
    nome = models.CharField(max_length=255)
    descricao = models.TextField()
    data_inicio = models.DateField()
    data_fim = models.DateField(null=True, blank=True)
    ativa = models.BooleanField(default=True)
    
    def __str__(self):
        return self.nome