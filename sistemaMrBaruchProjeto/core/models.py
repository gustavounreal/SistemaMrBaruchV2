from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ConfiguracaoSistema(models.Model):
    """Configurações globais do sistema"""
    chave = models.CharField(max_length=100, unique=True)
    valor = models.TextField()
    descricao = models.TextField(blank=True)
    ultima_atualizacao = models.DateTimeField(auto_now=True) 
    tipo = models.CharField(max_length=20, choices=[
        ('TEXTO', 'Texto'),
        ('NUMERO', 'Número'),
        ('BOOLEANO', 'Booleano'),
        ('JSON', 'JSON'),
    ], default='TEXTO')
    
    def __str__(self):
        return f"{self.chave} = {self.valor}"
    
    class Meta:
        verbose_name = "Configuração do Sistema"
        verbose_name_plural = "Configurações do Sistema"

class LogSistema(models.Model):
    """Logs de atividades do sistema"""
    NIVEL_CHOICES = [
        ('INFO', 'Informação'),
        ('WARNING', 'Aviso'),
        ('ERROR', 'Erro'),
        ('DEBUG', 'Debug'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    nivel = models.CharField(max_length=10, choices=NIVEL_CHOICES, default='INFO')
    mensagem = models.TextField()
    modulo = models.CharField(max_length=100)  # Ex: 'vendas', 'financeiro'
    acao = models.CharField(max_length=100)    # Ex: 'cadastro_venda', 'webhook_asaas'
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.modulo}.{self.acao} - {self.nivel}"
    
    class Meta:
        verbose_name = "Log do Sistema"
        verbose_name_plural = "Logs do Sistema"
        ordering = ['-data_criacao']
        indexes = [
            models.Index(fields=['modulo', 'acao']),
            models.Index(fields=['data_criacao']),
        ]

class Notificacao(models.Model):
    """Sistema de notificações para usuários"""
    TIPO_CHOICES = [
        ('SUCESSO', 'Sucesso'),
        ('ERRO', 'Erro'),
        ('AVISO', 'Aviso'),
        ('INFO', 'Informação'),
    ]
    
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    mensagem = models.TextField()
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES, default='INFO')
    lida = models.BooleanField(default=False)
    link = models.URLField(blank=True)  # Link para ação relacionada
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_leitura = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.usuario.email} - {self.titulo}"
    
    class Meta:
        verbose_name = "Notificação"
        verbose_name_plural = "Notificações"
        ordering = ['-data_criacao']


class WebhookLog(models.Model):
    """Armazena histórico completo de webhooks recebidos"""
    
    TIPO_CHOICES = [
        ('ASAAS', 'ASAAS'),
        ('OUTRO', 'Outro'),
    ]
    
    STATUS_CHOICES = [
        ('SUCCESS', 'Sucesso'),
        ('ERROR', 'Erro'),
        ('IGNORED', 'Ignorado'),
    ]
    
    tipo = models.CharField('Tipo', max_length=20, choices=TIPO_CHOICES, default='ASAAS')
    evento = models.CharField('Evento', max_length=100, blank=True)
    payload = models.JSONField('Payload Completo')
    headers = models.JSONField('Headers HTTP', blank=True, null=True)
    
    # Dados processados
    status_processamento = models.CharField('Status', max_length=20, choices=STATUS_CHOICES)
    mensagem_erro = models.TextField('Mensagem de Erro', blank=True)
    
    # Dados extraídos
    payment_id = models.CharField('Payment ID', max_length=100, blank=True, db_index=True)
    customer_id = models.CharField('Customer ID', max_length=100, blank=True, db_index=True)
    payment_status = models.CharField('Status Pagamento', max_length=50, blank=True)
    valor = models.DecimalField('Valor', max_digits=10, decimal_places=2, null=True, blank=True)
    
    # Metadados
    ip_origem = models.GenericIPAddressField('IP Origem', blank=True, null=True)
    data_recebimento = models.DateTimeField('Data Recebimento', auto_now_add=True, db_index=True)
    processado_em = models.DateTimeField('Processado em', auto_now=True)
    
    class Meta:
        db_table = 'core_webhook_log'
        verbose_name = 'Log de Webhook'
        verbose_name_plural = 'Logs de Webhooks'
        ordering = ['-data_recebimento']
        indexes = [
            models.Index(fields=['-data_recebimento']),
            models.Index(fields=['payment_id']),
            models.Index(fields=['evento']),
        ]
    
    def __str__(self):
        return f"{self.tipo} - {self.evento} - {self.data_recebimento.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def payload_formatado(self):
        """Retorna payload formatado para visualização"""
        import json
        return json.dumps(self.payload, indent=2, ensure_ascii=False)