from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    """Usuário personalizado do sistema"""
    
    email = models.EmailField(unique=True)
    google_id = models.CharField(max_length=100, blank=True, unique=True, null=True)
    avatar_url = models.URLField(blank=True)
    telefone = models.CharField(max_length=20, blank=True)
    cargo = models.CharField(max_length=50, blank=True)
    data_admissao = models.DateField(null=True, blank=True)
    ativo = models.BooleanField(default=True)     
    cpf = models.CharField(max_length=14, blank=True, null=True)
    rg = models.CharField(max_length=20, blank=True, null=True)
    endereco_completo = models.TextField(blank=True, null=True)
    cep = models.CharField(max_length=9, blank=True, null=True)
    chave_pix = models.CharField(max_length=255, blank=True, null=True)
    conta_bancaria = models.JSONField(blank=True, null=True)  # {banco, agencia, conta}
    nome_completo = models.CharField(max_length=150, blank=True, null=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}" if self.first_name else self.email

class DadosUsuario(models.Model):
    """Dados adicionais do usuário + DADOS FINANCEIROS"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='dados')
    
    bio = models.TextField(blank=True)
    ultimo_acesso = models.DateTimeField(auto_now=True)    
    whatsapp_pessoal = models.CharField(max_length=20, blank=True)
    contato_recado = models.CharField(max_length=20, blank=True)
    id_captador = models.CharField(max_length=50, blank=True)  # ID automático
    id_consultor = models.CharField(max_length=50, blank=True)  # ID automático
    
    # Métricas de performance (podem ser calculadas, mas útil ter aqui)
    total_vendas = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total_comissao_recebida = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    quantidade_clientes = models.IntegerField(default=0)
    
    def __str__(self):
        return f"Dados de {self.user.email}"
    
    class Meta:
        verbose_name = "Dados do Usuário"
        verbose_name_plural = "Dados dos Usuários"