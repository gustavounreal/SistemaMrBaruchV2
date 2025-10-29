from django.db import models
from django.conf import settings
from vendas.models import Venda

class Parcela(models.Model):
    STATUS_CHOICES = [
        ('aberta', 'Aberta'),
        ('paga', 'Paga'), 
        ('vencida', 'Vencida'),
        ('cancelada', 'Cancelada'),
    ]
    
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE)
    numero_parcela = models.IntegerField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='aberta')
    
    # Integração Asaas
    id_asaas = models.CharField(max_length=100, blank=True)
    url_boleto = models.URLField(blank=True)
    codigo_barras = models.TextField(blank=True)
    
    # Controle de envio ao ASAAS (novo)
    enviado_asaas = models.BooleanField(default=False, help_text='Indica se a cobrança foi enviada para o ASAAS')
    data_envio_asaas = models.DateTimeField(null=True, blank=True, help_text='Data/hora do envio para ASAAS')
    
    class Meta:
        ordering = ['venda', 'numero_parcela']
        verbose_name = 'Parcela'
        verbose_name_plural = 'Parcelas'
    
    def __str__(self):
        return f"Parcela {self.numero_parcela} - Venda #{self.venda.id} - R$ {self.valor}"

class PagamentoPIX(models.Model):
    # Mantido da versão antiga
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    asaas_payment_id = models.CharField(max_length=255, blank=True, null=True)
    pix_code = models.TextField(blank=True, null=True)
    pix_qr_code_url = models.TextField(blank=True, null=True)
    status_pagamento = models.CharField(max_length=20, choices=[('pendente', 'Pendente'), ('pago', 'Pago')], default='pendente')

class Comissao(models.Model):
    """
    Comissões sobre vendas (captador + consultor).
    
    Regras (Out/2025):
    - CAPTADOR: Escala progressiva baseada em faturamento mensal (2% a 10%)
    - CONSULTOR: Fixo 3% sobre valor recebido
    """
    TIPO_CHOICES = [
        ('CAPTADOR_ENTRADA', 'Captador - Entrada'),
        ('CAPTADOR_PARCELA', 'Captador - Parcela'),
        ('CONSULTOR_ENTRADA', 'Consultor - Entrada'),
        ('CONSULTOR_PARCELA', 'Consultor - Parcela'),
    ]
    
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('paga', 'Paga'),
        ('cancelada', 'Cancelada'),
    ]
    
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comissoes_venda')
    venda = models.ForeignKey('vendas.Venda', on_delete=models.CASCADE, related_name='comissoes')
    parcela = models.ForeignKey('Parcela', on_delete=models.CASCADE, null=True, blank=True, related_name='comissoes')
    tipo_comissao = models.CharField(max_length=30, choices=TIPO_CHOICES, default='CAPTADOR_ENTRADA')
    valor_comissao = models.DecimalField(max_digits=10, decimal_places=2)
    percentual_comissao = models.DecimalField(max_digits=5, decimal_places=2, help_text='Percentual aplicado no momento do cálculo')
    data_calculada = models.DateTimeField(auto_now_add=True)
    data_pagamento = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    observacoes = models.TextField(blank=True, help_text='Detalhes do cálculo (faturamento mensal, escala, etc)')
    
    class Meta:
        verbose_name = 'Comissão de Venda'
        verbose_name_plural = 'Comissões de Vendas'
        ordering = ['-data_calculada']
        indexes = [
            models.Index(fields=['usuario', 'data_calculada']),
            models.Index(fields=['venda', 'tipo_comissao']),
            models.Index(fields=['status', 'data_calculada']),
        ]
    
    def __str__(self):
        tipo_display = dict(self.TIPO_CHOICES).get(self.tipo_comissao, self.tipo_comissao)
        return f"{tipo_display} - {self.usuario.get_full_name() or self.usuario.email} - R$ {self.valor_comissao:.2f}"

class ClienteAsaas(models.Model):
    lead = models.OneToOneField('marketing.Lead', on_delete=models.CASCADE, related_name='asaas')
    asaas_customer_id = models.CharField(max_length=100, unique=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Asaas: {self.lead.nome_completo}"

    

class PixLevantamento(models.Model):
    lead = models.ForeignKey('marketing.Lead', on_delete=models.CASCADE, related_name='pix_levantamentos')
    asaas_payment_id = models.CharField(max_length=255, unique=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    pix_code = models.TextField()
    pix_qr_code_url = models.TextField()
    status_pagamento = models.CharField(
        max_length=20,
        choices=[
            ('pendente', 'Pendente'), 
            ('pago', 'Pago'),
            ('vencido', 'Vencido')
        ],
        default='pendente'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PIX Levantamento: {self.asaas_payment_id} - {self.status_pagamento}"


class PixEntrada(models.Model):
    """PIX gerado para entrada de venda"""
    venda = models.ForeignKey('vendas.Venda', on_delete=models.CASCADE, related_name='pix_entradas')
    asaas_payment_id = models.CharField(max_length=255, unique=True)
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    pix_code = models.TextField(help_text='Código copia e cola do PIX')
    pix_qr_code_url = models.TextField(help_text='URL da imagem do QR Code')
    status_pagamento = models.CharField(
        max_length=20,
        choices=[
            ('pendente', 'Pendente'), 
            ('pago', 'Pago'),
            ('vencido', 'Vencido'),
            ('cancelado', 'Cancelado')
        ],
        default='pendente'
    )
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_pagamento = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'PIX de Entrada'
        verbose_name_plural = 'PIX de Entradas'
        ordering = ['-data_criacao']

    def __str__(self):
        return f"PIX Entrada Venda #{self.venda.id} - R$ {self.valor} - {self.status_pagamento}"


class Renegociacao(models.Model):
    """
    Histórico de renegociações de dívidas
    """
    STATUS_CHOICES = [
        ('em_negociacao', 'Em Negociação'),
        ('aceita', 'Aceita pelo Cliente'),
        ('recusada', 'Recusada pelo Cliente'),
        ('efetivada', 'Efetivada no ASAAS'),
        ('cancelada', 'Cancelada'),
    ]
    
    TIPO_CHOICES = [
        ('desconto', 'Desconto sobre Parcelas'),
        ('nova_parcela', 'Nova Parcelamento'),
        ('prorrogacao', 'Prorrogação de Vencimento'),
        ('combinada', 'Renegociação Combinada'),
    ]
    
    venda = models.ForeignKey('vendas.Venda', on_delete=models.CASCADE, related_name='renegociacoes')
    tipo_renegociacao = models.CharField(max_length=20, choices=TIPO_CHOICES, default='desconto')
    
    # Dados da Dívida Original
    parcelas_original = models.ManyToManyField('Parcela', related_name='renegociacoes_original', blank=True)
    valor_total_divida = models.DecimalField(max_digits=10, decimal_places=2, help_text='Valor total da dívida original')
    
    # Dados da Nova Negociação
    valor_desconto = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Valor de desconto concedido')
    percentual_desconto = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='% de desconto')
    valor_novo_total = models.DecimalField(max_digits=10, decimal_places=2, help_text='Novo valor total após negociação')
    numero_novas_parcelas = models.IntegerField(default=1, help_text='Quantidade de novas parcelas')
    data_primeira_parcela = models.DateField(help_text='Vencimento da primeira parcela renegociada')
    
    # Controle
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='renegociacoes_financeiro')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='em_negociacao')
    observacoes = models.TextField(blank=True, help_text='Observações sobre a negociação')
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    data_efetivacao = models.DateTimeField(null=True, blank=True, help_text='Quando a renegociação foi efetivada no ASAAS')
    
    # Controle ASAAS
    asaas_ids_cancelados = models.TextField(blank=True, help_text='IDs das cobranças canceladas no ASAAS (JSON)')
    asaas_ids_novos = models.TextField(blank=True, help_text='IDs das novas cobranças no ASAAS (JSON)')
    
    class Meta:
        verbose_name = 'Renegociação'
        verbose_name_plural = 'Renegociações'
        ordering = ['-data_criacao']
        
    def __str__(self):
        return f"Renegociação Venda #{self.venda.id} - {self.get_status_display()}"


class HistoricoContatoRetencao(models.Model):
    """
    Registro de contatos feitos pela equipe de retenção
    """
    TIPO_CONTATO_CHOICES = [
        ('telefone', 'Telefone'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'E-mail'),
        ('sms', 'SMS'),
    ]
    
    RESULTADO_CHOICES = [
        ('contato_sucesso', 'Contato com Sucesso'),
        ('nao_atendeu', 'Não Atendeu'),
        ('promessa_pagamento', 'Promessa de Pagamento'),
        ('negociacao_iniciada', 'Negociação Iniciada'),
        ('recusa_negociacao', 'Recusa de Negociação'),
        ('numero_invalido', 'Número Inválido'),
    ]
    
    venda = models.ForeignKey('vendas.Venda', on_delete=models.CASCADE, related_name='historico_retencao')
    renegociacao = models.ForeignKey(Renegociacao, on_delete=models.SET_NULL, null=True, blank=True, related_name='contatos')
    
    tipo_contato = models.CharField(max_length=20, choices=TIPO_CONTATO_CHOICES)
    resultado = models.CharField(max_length=30, choices=RESULTADO_CHOICES)
    observacoes = models.TextField(help_text='Detalhes do contato')
    
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='contatos_retencao')
    data_contato = models.DateTimeField(auto_now_add=True)
    data_proxima_tentativa = models.DateField(null=True, blank=True, help_text='Agendamento para próximo contato')
    
    class Meta:
        verbose_name = 'Histórico de Contato - Retenção'
        verbose_name_plural = 'Históricos de Contato - Retenção'
        ordering = ['-data_contato']
        
    def __str__(self):
        return f"{self.get_tipo_contato_display()} - Venda #{self.venda.id} - {self.get_resultado_display()}"
        
