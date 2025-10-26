from django.db import models
from django.conf import settings
from decimal import Decimal

class ComissaoLead(models.Model):
    """
    Comissão gerada por levantamento de lead com pagamento PIX confirmado.
    O valor é configurável via Painel de Configurações (ConfiguracaoSistema).
    """
    lead = models.ForeignKey('marketing.Lead', on_delete=models.CASCADE, related_name='comissoes')
    atendente = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='comissoes_recebidas')
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_criacao = models.DateTimeField(auto_now_add=True)
    pago = models.BooleanField(default=False, help_text="Indica se a comissão já foi paga ao atendente")
    data_pagamento = models.DateField(null=True, blank=True, help_text="Data do pagamento da comissão")
    observacoes = models.TextField(blank=True, help_text="Observações sobre a comissão")

    class Meta:
        unique_together = ('lead', 'atendente')
        verbose_name = 'Comissão de Lead'
        verbose_name_plural = 'Comissões de Leads'
        ordering = ['-data_criacao']

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
        super().save(*args, **kwargs)


