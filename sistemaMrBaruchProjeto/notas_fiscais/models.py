from django.db import models
from django.utils import timezone
from decimal import Decimal


class NotaFiscal(models.Model):
    """
    Modelo para gerenciar Notas Fiscais emitidas via Asaas
    """
    
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente Emissão'),
        ('EM_PROCESSAMENTO', 'Processando'),
        ('EMITIDA', 'Emitida'),
        ('ENVIADA', 'Enviada por E-mail'),
        ('ERRO', 'Erro na Emissão'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    TIPO_CHOICES = [
        ('ENTRADA', 'Entrada'),
        ('PARCELA', 'Parcela'),
    ]
    
    # ========== RELACIONAMENTOS ==========
    venda = models.ForeignKey(
        'vendas.Venda', 
        on_delete=models.CASCADE, 
        related_name='notas_fiscais',
        help_text="Venda vinculada à nota fiscal"
    )
    
    parcela = models.ForeignKey(
        'vendas.Parcela', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='notas_fiscais',
        help_text="Parcela específica (se não for entrada)"
    )
    
    # ========== TIPO E STATUS ==========
    tipo = models.CharField(
        max_length=10, 
        choices=TIPO_CHOICES,
        help_text="Tipo da nota fiscal"
    )
    
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDENTE',
        help_text="Status atual da nota fiscal"
    )
    
    # ========== DADOS DA NOTA FISCAL (Asaas) ==========
    id_nf_asaas = models.CharField(
        max_length=100, 
        blank=True,
        help_text="ID da nota fiscal no Asaas"
    )
    
    numero_nf = models.CharField(
        max_length=20, 
        blank=True,
        help_text="Número da nota fiscal"
    )
    
    serie_nf = models.CharField(
        max_length=10, 
        blank=True,
        default="1",
        help_text="Série da nota fiscal"
    )
    
    codigo_verificacao = models.CharField(
        max_length=50, 
        blank=True,
        help_text="Código de verificação da NF"
    )
    
    chave_acesso = models.CharField(
        max_length=44,
        blank=True,
        help_text="Chave de acesso de 44 dígitos"
    )
    
    # ========== URLs DOS DOCUMENTOS ==========
    url_pdf = models.URLField(
        blank=True,
        help_text="URL do PDF da nota fiscal"
    )
    
    url_xml = models.URLField(
        blank=True,
        help_text="URL do XML da nota fiscal"
    )
    
    # ========== VALORES ==========
    valor_servico = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        help_text="Valor do serviço prestado"
    )
    
    aliquota_iss = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal('2.00'),
        help_text="Alíquota de ISS em porcentagem"
    )
    
    valor_iss = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=Decimal('0.00'),
        help_text="Valor do ISS calculado"
    )
    
    # ========== DESCRIÇÃO DO SERVIÇO ==========
    descricao_servico = models.TextField(
        blank=True,
        help_text="Descrição detalhada do serviço prestado"
    )
    
    codigo_servico_municipal = models.CharField(
        max_length=10,
        blank=True,
        default="01.01",
        help_text="Código do serviço conforme LC 116/2003"
    )
    
    # ========== CONTROLE DE EMISSÃO ==========
    tentativas_emissao = models.IntegerField(
        default=0,
        help_text="Número de tentativas de emissão"
    )
    
    mensagem_erro = models.TextField(
        blank=True,
        help_text="Mensagem de erro da última tentativa"
    )
    
    log_integracao = models.JSONField(
        default=dict,
        blank=True,
        help_text="Log completo das integrações com Asaas"
    )
    
    # ========== CANCELAMENTO ==========
    data_cancelamento = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Data de cancelamento da nota"
    )
    
    motivo_cancelamento = models.TextField(
        blank=True,
        help_text="Motivo do cancelamento"
    )
    
    cancelada_por = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notas_canceladas',
        help_text="Usuário que cancelou a nota"
    )
    
    # ========== E-MAIL ==========
    email_enviado = models.BooleanField(
        default=False,
        help_text="Indica se o e-mail com a NF foi enviado"
    )
    
    data_envio_email = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Data de envio do e-mail"
    )
    
    email_destinatario = models.EmailField(
        blank=True,
        help_text="E-mail para qual a NF foi enviada"
    )
    
    # ========== TIMESTAMPS ==========
    data_criacao = models.DateTimeField(
        auto_now_add=True,
        help_text="Data de criação do registro"
    )
    
    data_emissao = models.DateTimeField(
        null=True, 
        blank=True,
        help_text="Data de emissão efetiva da nota"
    )
    
    data_atualizacao = models.DateTimeField(
        auto_now=True,
        help_text="Data da última atualização"
    )
    
    class Meta:
        verbose_name = "Nota Fiscal"
        verbose_name_plural = "Notas Fiscais"
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['status', '-data_criacao']),
            models.Index(fields=['venda', 'tipo']),
            models.Index(fields=['numero_nf']),
        ]
    
    def __str__(self):
        if self.numero_nf:
            return f"NF {self.numero_nf} - Venda #{self.venda.id}"
        return f"NF Pendente #{self.id} - Venda #{self.venda.id}"
    
    def save(self, *args, **kwargs):
        # Calcular valor ISS automaticamente
        if self.valor_servico and self.aliquota_iss:
            self.valor_iss = (self.valor_servico * self.aliquota_iss) / Decimal('100')
        
        super().save(*args, **kwargs)
    
    @property
    def cliente_nome(self):
        """Retorna nome do cliente"""
        if self.venda and self.venda.cliente and self.venda.cliente.lead:
            return self.venda.cliente.lead.nome_completo
        return "Cliente não identificado"
    
    @property
    def valor_liquido(self):
        """Retorna valor líquido (valor_servico - valor_iss)"""
        return self.valor_servico - self.valor_iss
    
    @property
    def pode_cancelar(self):
        """Verifica se a nota pode ser cancelada"""
        if self.status != 'EMITIDA':
            return False
        
        # Verificar se está dentro do prazo (geralmente 24h ou conforme município)
        if self.data_emissao:
            tempo_decorrido = timezone.now() - self.data_emissao
            # Prazo de 24 horas
            return tempo_decorrido.total_seconds() < (24 * 3600)
        
        return False
    
    @property
    def status_display(self):
        """Retorna status formatado com ícone"""
        icons = {
            'PENDENTE': '⏳',
            'EM_PROCESSAMENTO': '⚙️',
            'EMITIDA': '✅',
            'ENVIADA': '📧',
            'ERRO': '❌',
            'CANCELADA': '🚫',
        }
        return f"{icons.get(self.status, '')} {self.get_status_display()}"
    
    def get_motivo_pendente(self):
        """Retorna o motivo de a nota estar pendente"""
        from .asaas_nf_service import AsaasNFService
        
        if self.status == 'ERRO':
            return self.mensagem_erro or "Erro desconhecido na emissão"
        
        if self.status == 'PENDENTE':
            # Validar dados para emissão
            service = AsaasNFService()
            is_valid, erros = service.validar_dados_emissao(self.venda)
            
            if not is_valid:
                return " | ".join(erros)
            
            return "Aguardando processamento manual"
        
        return None


class ConfiguracaoFiscal(models.Model):
    """
    Configurações fiscais da empresa para emissão de NF-e
    """
    
    # ========== DADOS DA EMPRESA ==========
    cnpj = models.CharField(
        max_length=18,
        help_text="CNPJ da empresa (formato: 00.000.000/0000-00)"
    )
    
    razao_social = models.CharField(
        max_length=200,
        help_text="Razão Social da empresa"
    )
    
    nome_fantasia = models.CharField(
        max_length=200,
        blank=True,
        help_text="Nome Fantasia"
    )
    
    inscricao_municipal = models.CharField(
        max_length=20,
        help_text="Inscrição Municipal"
    )
    
    inscricao_estadual = models.CharField(
        max_length=20,
        blank=True,
        help_text="Inscrição Estadual (se aplicável)"
    )
    
    # ========== ENDEREÇO ==========
    cep = models.CharField(max_length=10)
    logradouro = models.CharField(max_length=255)
    numero = models.CharField(max_length=10)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    uf = models.CharField(max_length=2)
    
    # ========== DADOS FISCAIS ==========
    regime_tributario = models.CharField(
        max_length=50,
        default="Simples Nacional",
        help_text="Regime Tributário"
    )
    
    aliquota_iss_padrao = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal('2.00'),
        help_text="Alíquota de ISS padrão (%)"
    )
    
    codigo_servico_padrao = models.CharField(
        max_length=10,
        default="01.01",
        help_text="Código de serviço padrão (LC 116/2003)"
    )
    
    descricao_servico_padrao = models.TextField(
        default="Consultoria Financeira e Assessoria em Crédito",
        help_text="Descrição padrão do serviço"
    )
    
    # ========== CONFIGURAÇÕES ==========
    email_remetente = models.EmailField(
        help_text="E-mail remetente das notas fiscais"
    )
    
    emissao_automatica = models.BooleanField(
        default=True,
        help_text="Emitir notas automaticamente após pagamento confirmado"
    )
    
    envio_automatico_email = models.BooleanField(
        default=True,
        help_text="Enviar e-mail automaticamente após emissão"
    )
    
    prazo_cancelamento_horas = models.IntegerField(
        default=24,
        help_text="Prazo em horas para cancelamento da NF"
    )
    
    # ========== TIMESTAMPS ==========
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuração Fiscal"
        verbose_name_plural = "Configurações Fiscais"
    
    def __str__(self):
        return f"Configurações Fiscais - {self.razao_social}"
