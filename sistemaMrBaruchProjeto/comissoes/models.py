from django.db import models
from django.conf import settings
from decimal import Decimal
from django.utils import timezone

class ComissaoLead(models.Model):
    """
    Comissão gerada por levantamento de lead com pagamento PIX confirmado.
    O valor é configurável via Painel de Configurações (ConfiguracaoSistema).
    
    WORKFLOW:
    1. DISPONIVEL - Comissão gerada automaticamente quando pagamento confirmado
    2. AUTORIZADO - Comissão autorizada para pagamento pelo gestor
    3. PAGO - Comissão paga ao atendente
    4. CANCELADO - Comissão cancelada
    """
    STATUS_CHOICES = [
        ('DISPONIVEL', 'Disponível'),
        ('AUTORIZADO', 'Autorizado'),
        ('PAGO', 'Pago'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    lead = models.ForeignKey('marketing.Lead', on_delete=models.CASCADE, related_name='comissoes')
    atendente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comissoes_recebidas')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DISPONIVEL')
    competencia = models.DateField(null=True, blank=True, help_text="Mês/ano de referência para pagamento")
    
    # Datas e controles
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_autorizacao = models.DateTimeField(null=True, blank=True)
    autorizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='comissoes_autorizadas')
    data_pagamento = models.DateField(null=True, blank=True, help_text="Data do pagamento da comissão")
    pago_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='comissoes_pagas')
    
    observacoes = models.TextField(blank=True, help_text="Observações sobre a comissão")

    class Meta:
        unique_together = ('lead', 'atendente')
        verbose_name = 'Comissão de Lead'
        verbose_name_plural = 'Comissões de Leads'
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['atendente', 'status']),
            models.Index(fields=['competencia', 'status']),
        ]

    def __str__(self):
        return f"Comissão R$ {self.valor} para {self.atendente.get_full_name() or self.atendente.username} - Lead #{self.lead_id}"
    
    @classmethod
    def obter_valor_comissao(cls):
        """Obtém o valor da comissão do sistema de configurações"""
        from core.models import ConfiguracaoSistema
        try:
            config = ConfiguracaoSistema.objects.get(chave='COMISSAO_ATENDENTE_VALOR_FIXO')
            return Decimal(config.valor)
        except ConfiguracaoSistema.DoesNotExist:
            # Valor padrão caso não esteja configurado
            return Decimal('0.50')
    
    def save(self, *args, **kwargs):
        # Se o valor não foi definido, busca da configuração
        if not self.valor:
            self.valor = self.obter_valor_comissao()
        # Se não tem competência, define como mês atual
        if not self.competencia:
            self.competencia = timezone.now().date().replace(day=1)
        super().save(*args, **kwargs)


class ComissaoConsultor(models.Model):
    """
    Comissão gerada por vendas fechadas pelo consultor.
    Calculada com base no valor da venda e percentual configurado.
    
    WORKFLOW:
    1. DISPONIVEL - Comissão gerada automaticamente quando pagamento confirmado
    2. AUTORIZADO - Comissão autorizada para pagamento
    3. PAGO - Comissão paga
    4. CANCELADO - Comissão cancelada
    """
    STATUS_CHOICES = [
        ('DISPONIVEL', 'Disponível'),
        ('AUTORIZADO', 'Autorizado'),
        ('PAGO', 'Pago'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    venda = models.ForeignKey('vendas.Venda', on_delete=models.CASCADE, related_name='comissoes_consultor')
    parcela = models.ForeignKey('vendas.Parcela', on_delete=models.CASCADE, null=True, blank=True, related_name='comissoes_consultor')
    consultor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comissoes_consultor')
    valor = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor da comissão")
    valor_venda = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Valor da venda/parcela")
    percentual = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Percentual aplicado sobre a venda")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DISPONIVEL')
    competencia = models.DateField(null=True, blank=True, help_text="Mês/ano de referência para pagamento")
    
    # Datas e controles
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_autorizacao = models.DateTimeField(null=True, blank=True)
    autorizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='comissoes_consultor_autorizadas')
    data_pagamento = models.DateField(null=True, blank=True, help_text="Data do pagamento da comissão")
    pago_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='comissoes_consultor_pagas')
    
    observacoes = models.TextField(blank=True, help_text="Observações sobre a comissão")

    class Meta:
        verbose_name = 'Comissão de Consultor'
        verbose_name_plural = 'Comissões de Consultores'
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['consultor', 'status']),
            models.Index(fields=['competencia', 'status']),
        ]

    def __str__(self):
        return f"Comissão R$ {self.valor} para {self.consultor.get_full_name() or self.consultor.username} - Venda #{self.venda_id}"
    
    def save(self, *args, **kwargs):
        # Se não tem competência, define como mês atual
        if not self.competencia:
            self.competencia = timezone.now().date().replace(day=1)
        super().save(*args, **kwargs)


class ComissaoCaptador(models.Model):
    """
    Comissão gerada por indicações/captação de clientes.
    Calculada com base no valor da venda e percentual do captador.
    
    WORKFLOW:
    1. DISPONIVEL - Comissão gerada automaticamente quando pagamento confirmado
    2. AUTORIZADO - Comissão autorizada para pagamento
    3. PAGO - Comissão paga
    4. CANCELADO - Comissão cancelada
    """
    STATUS_CHOICES = [
        ('DISPONIVEL', 'Disponível'),
        ('AUTORIZADO', 'Autorizado'),
        ('PAGO', 'Pago'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    venda = models.ForeignKey('vendas.Venda', on_delete=models.CASCADE, related_name='comissoes_captador')
    parcela = models.ForeignKey('vendas.Parcela', on_delete=models.CASCADE, null=True, blank=True, related_name='comissoes_captador')
    captador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comissoes_captador')
    valor = models.DecimalField(max_digits=10, decimal_places=2, help_text="Valor da comissão")
    valor_venda = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), help_text="Valor da venda/parcela")
    percentual = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), help_text="Percentual aplicado sobre a venda")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='DISPONIVEL')
    competencia = models.DateField(null=True, blank=True, help_text="Mês/ano de referência para pagamento")
    
    # Datas e controles
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_autorizacao = models.DateTimeField(null=True, blank=True)
    autorizado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='comissoes_captador_autorizadas')
    data_pagamento = models.DateField(null=True, blank=True, help_text="Data do pagamento da comissão")
    pago_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='comissoes_captador_pagas')
    
    observacoes = models.TextField(blank=True, help_text="Observações sobre a comissão")

    class Meta:
        verbose_name = 'Comissão de Captador'
        verbose_name_plural = 'Comissões de Captadores'
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['captador', 'status']),
            models.Index(fields=['competencia', 'status']),
        ]

    def __str__(self):
        return f"Comissão R$ {self.valor} para {self.captador.get_full_name() or self.captador.username} - Venda #{self.venda_id}"
    
    def save(self, *args, **kwargs):
        # Se não tem competência, define como mês atual
        if not self.competencia:
            self.competencia = timezone.now().date().replace(day=1)
        super().save(*args, **kwargs)


class PagamentoComissao(models.Model):
    """
    Registro de pagamento em lote de comissões.
    Agrupa múltiplas comissões pagas em uma única operação.
    """
    TIPO_CHOICES = [
        ('atendente', 'Atendente'),
        ('consultor', 'Consultor'),
        ('captador', 'Captador'),
    ]
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    competencia = models.DateField(help_text="Mês/ano de referência")
    data_pagamento = models.DateField(auto_now_add=True)
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    quantidade_comissoes = models.IntegerField(default=0)
    responsavel = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pagamentos_realizados')
    observacoes = models.TextField(blank=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Pagamento de Comissão'
        verbose_name_plural = 'Pagamentos de Comissões'
        ordering = ['-data_pagamento']

    def __str__(self):
        return f"Pagamento {self.get_tipo_display()} - {self.competencia.strftime('%m/%Y')} - R$ {self.valor_total}"


