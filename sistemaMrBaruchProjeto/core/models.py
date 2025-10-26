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