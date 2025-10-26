from django.db import models
from django.conf import settings
from django.utils import timezone


class MotivoRecusa(models.Model):
    """
    Tabela para armazenar os motivos de recusa de propostas
    Gerenciável através do painel de configurações
    """
    nome = models.CharField(max_length=100, unique=True, help_text="Nome do motivo de recusa")
    descricao = models.TextField(blank=True, help_text="Descrição detalhada (opcional)")
    ativo = models.BooleanField(default=True, help_text="Motivo está ativo para seleção")
    ordem = models.IntegerField(default=0, help_text="Ordem de exibição na lista")
    cor = models.CharField(
        max_length=7, 
        default='#ffc107', 
        help_text="Cor em hexadecimal para identificação visual"
    )
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Motivo de Recusa"
        verbose_name_plural = "Motivos de Recusa"
        ordering = ['ordem', 'nome']
    
    def __str__(self):
        return self.nome


class Servico(models.Model):
    TIPO_SERVICO_CHOICES = [
        ('LIMPA_NOME', 'Limpa Nome'),
        ('RETIRADA_TRAVAS', 'Retirada de Travas'),
        ('RECUPERACAO_SCORE', 'Recuperação de Score'),
        ('COMBINADO', 'Serviço Combinado'),
    ]
    
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=50, choices=TIPO_SERVICO_CHOICES)
    descricao = models.TextField()
    prazo_medio = models.IntegerField(help_text="Prazo em dias")  # dias
    preco_base = models.DecimalField(max_digits=10, decimal_places=2)
    ativo = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.nome} - {self.get_tipo_display()}"

class Venda(models.Model):
    STATUS_CHOICES = [
        ('ORCAMENTO', 'Orçamento'),
        ('CONTRATO_ASSINADO', 'Contrato Assinado'),
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('CONCLUIDO', 'Concluído'),
        ('CANCELADO', 'Cancelado'),
        ('INADIMPLENTE', 'Inadimplente'),
        ('QUEDA_CONTRATO', 'Quebra de Contrato'),
    ]
    
    FORMA_PAGAMENTO_CHOICES = [
        ('BOLETO', 'Boleto'),
        ('PIX', 'PIX'),
        ('DINHEIRO', 'Dinheiro'),
        ('CARTAO', 'Cartão'),
    ]
    
    FREQUENCIA_CHOICES = [
        ('SEMANAL', 'Semanal'),
        ('QUINZENAL', 'Quinzenal'),
        ('MENSAL', 'Mensal'),
    ]
    
    # Relacionamentos
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE)
    servico = models.ForeignKey(Servico, on_delete=models.CASCADE)
    captador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vendas_captador')
    consultor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='vendas_consultor')
    
    # Valores da Venda
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    valor_entrada = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    sem_entrada = models.BooleanField(default=False)
    
    # Parcelamento
    quantidade_parcelas = models.IntegerField()
    valor_parcela = models.DecimalField(max_digits=10, decimal_places=2)
    frequencia_pagamento = models.CharField(max_length=20, choices=FREQUENCIA_CHOICES, default='MENSAL')
    
    # Formas de Pagamento
    forma_entrada = models.CharField(max_length=20, choices=FORMA_PAGAMENTO_CHOICES)
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_PAGAMENTO_CHOICES)
    
    # Datas Importantes
    data_vencimento_primeira = models.DateField()
    data_inicio_servico = models.DateField(null=True, blank=True, help_text="Data de início do serviço definida pelo consultor")
    dias_para_conclusao = models.IntegerField(
        default=90, 
        help_text="Dias úteis para conclusão do serviço (escolhido pelo consultor)"
    )
    data_conclusao_prevista = models.DateField(
        null=True, 
        blank=True, 
        help_text="Data calculada automaticamente: data_inicio + dias_para_conclusao"
    )
    prazo_pagamento_total = models.IntegerField(
        null=True, 
        blank=True,
        help_text="Prazo total de pagamento em dias (calculado automaticamente)"
    )
    data_venda = models.DateField(auto_now_add=True)
    
    # ✅ SERVIÇOS CONTRATADOS (do fluxograma e versão antiga)
    limpa_nome = models.BooleanField(default=False)
    retirada_travas = models.BooleanField(default=False)
    recuperacao_score = models.BooleanField(default=False)
    
    # Status do Contrato
    contrato_assinado = models.BooleanField(default=False)
    data_assinatura = models.DateTimeField(null=True, blank=True)
    assinatura_gov = models.BooleanField(default=False)
    liminar_entregue = models.BooleanField(default=False)
    
    # Status Compliance Pós-Venda
    status_compliance_pos_venda = models.CharField(
        max_length=30,
        default='AGUARDANDO_CONFERENCIA',
        help_text='Status do processo pós-venda no Compliance'
    )
    status_pagamento_entrada = models.CharField(
        max_length=20,
        default='PENDENTE',
        help_text='Status do pagamento da entrada: SEM_ENTRADA, PENDENTE, PAGO'
    )
    
    # Status da Venda
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ORCAMENTO')
    observacoes = models.TextField(blank=True)
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        nome = self.cliente.lead.nome_completo if self.cliente and hasattr(self.cliente, 'lead') and self.cliente.lead else f"Cliente #{self.cliente.id if self.cliente else 'N/A'}"
        return f"Venda {self.id} - {nome} - R$ {self.valor_total}"
    
    class Meta:
        verbose_name = "Venda"
        verbose_name_plural = "Vendas"
        ordering = ['-data_criacao']

class Parcela(models.Model):
    STATUS_CHOICES = [
        ('ABERTA', 'Aberta'),
        ('PAGA', 'Paga'),
        ('VENCIDA', 'Vencida'),
        ('CANCELADA', 'Cancelada'),
    ]
    
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='parcelas')
    numero_parcela = models.IntegerField()
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ABERTA')
    
    # Integração Asaas 
    id_asaas = models.CharField(max_length=100, blank=True)
    url_boleto = models.URLField(blank=True)
    codigo_barras = models.TextField(blank=True)
    asaas_criado = models.BooleanField(default=False)
    
    def __str__(self):
        return f"Parcela {self.numero_parcela} - {self.venda.cliente.nome_completo}"
    
    class Meta:
        verbose_name = "Parcela"
        verbose_name_plural = "Parcelas"
        unique_together = ['venda', 'numero_parcela']
        ordering = ['venda', 'numero_parcela']

class PagamentoPIX(models.Model):
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('VENCIDO', 'Vencido'),
    ]
    
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='pagamentos_pix')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField()
    data_pagamento = models.DateField(null=True, blank=True)

    # Dados PIX
    asaas_payment_id = models.CharField(max_length=255, blank=True, null=True)
    pix_code = models.TextField(blank=True, null=True)
    pix_qr_code_url = models.TextField(blank=True, null=True)
    status_pagamento = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    
    def __str__(self):
        return f"PIX {self.venda.id} - R$ {self.valor} - {self.status_pagamento}"
    
    class Meta:
        verbose_name = "Pagamento PIX"
        verbose_name_plural = "Pagamentos PIX"


class PreVenda(models.Model):
    """
    Etapa intermediária entre Lead e Venda
    Coleta desejo do cliente e valida interesse no serviço
    """
    PRAZO_RISCO_CHOICES = [
        ('PRAZO_CURTO_RISCO_ALTO', 'Prazo Curto / Risco Alto'),
        ('PRAZO_MEDIO_RISCO_MEDIO', 'Prazo Médio / Risco Médio'),
        ('PRAZO_MEDIO_RISCO_BAIXO', 'Prazo Médio / Risco Médio-Baixo'),
    ]
    
    SERVICO_INTERESSE_CHOICES = [
        ('LIMPA_NOME', 'Limpa Nome'),
        ('RETIRADA_TRAVAS', 'Retirada de Travas'),
        ('RECUPERACAO_SCORE', 'Recuperação de Score'),
        ('RECUPERACAO_LIMPA_NOME', 'Recuperação de Score + Limpa Nome'),
        ('RETIRADA_TRAVAS_LIMPA_NOME', 'Retirada de Travas + Limpa Nome'),
        ('RECUPERACAO_RETIRADA_TRAVAS', 'Recuperação de Score + Retirada de Travas'),
        ('COMPLETO', 'Recuperação de Score + Retirada de Travas + Limpa Nome'),
    ]
    
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('ACEITO', 'Aceito'),
        ('RECUSADO', 'Recusado'),
        ('CONVERTIDO', 'Convertido em Venda'),
    ]
    
    # Relacionamento com Lead
    lead = models.ForeignKey('marketing.Lead', on_delete=models.CASCADE, related_name='pre_vendas')
    
    # Dados de qualificação (Etapa 1)
    prazo_risco = models.CharField(max_length=50, choices=PRAZO_RISCO_CHOICES)
    motivo_principal = models.ForeignKey(
        'marketing.MotivoContato',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'tipo': 'MOTIVO'},
        related_name='pre_vendas_motivo'
    )
    perfil_emocional = models.ForeignKey(
        'marketing.MotivoContato',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'tipo': 'PERFIL'},
        related_name='pre_vendas_perfil'
    )
    

    # Serviço proposto e valores
    servico_interesse = models.CharField(max_length=50, choices=SERVICO_INTERESSE_CHOICES)
    valor_proposto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    observacoes_levantamento = models.TextField(blank=True, help_text="Informações encontradas no levantamento")

    # Dados financeiros da pré-venda
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valor_entrada = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantidade_parcelas = models.PositiveIntegerField(null=True, blank=True)
    valor_parcela = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    frequencia_pagamento = models.CharField(max_length=20, blank=True, default='MENSAL')
    
    # Status e datas
    aceite_cliente = models.BooleanField(default=False, help_text="Cliente aceitou o serviço?")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    
    # Motivos de recusa
    motivo_recusa_principal = models.ForeignKey(
        'MotivoRecusa',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='pre_vendas_recusadas',
        help_text="Motivo principal da recusa"
    )
    motivo_recusa = models.TextField(blank=True, help_text="Detalhes adicionais sobre a recusa")
    
    # Responsáveis
    atendente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='pre_vendas_atendidas'
    )
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    data_aceite = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Pré-Venda {self.id} - {self.lead.nome_completo} - {self.status}"
    
    class Meta:
        verbose_name = "Pré-Venda"
        verbose_name_plural = "Pré-Vendas"
        ordering = ['-data_criacao']
        
    def converter_em_venda(self):
        """Marca a pré-venda como convertida e atualiza o status do lead"""
        self.status = 'CONVERTIDO'
        self.save()
        self.lead.status = 'QUALIFICADO'
        self.lead.save()


class DocumentoVenda(models.Model):
    """
    Armazena documentos coletados para a venda
    """
    TIPO_DOCUMENTO_CHOICES = [
        ('CPF', 'CPF'),
        ('CNPJ', 'CNPJ'),
        ('RG', 'RG'),
        ('CRNM', 'CRNM (Estrangeiros)'),
        ('COMPROVANTE_RESIDENCIA', 'Comprovante de Residência'),
        ('COMPROVANTE_RENDA', 'Comprovante de Renda'),
        ('OUTROS', 'Outros'),
    ]
    
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='documentos')
    tipo_documento = models.CharField(max_length=50, choices=TIPO_DOCUMENTO_CHOICES)
    arquivo = models.FileField(upload_to='vendas/documentos/%Y/%m/')
    observacoes = models.TextField(blank=True)
    data_upload = models.DateTimeField(auto_now_add=True)
    usuario_upload = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"{self.get_tipo_documento_display()} - Venda {self.venda.id}"
    
    class Meta:
        verbose_name = "Documento de Venda"
        verbose_name_plural = "Documentos de Venda"
        ordering = ['-data_upload']