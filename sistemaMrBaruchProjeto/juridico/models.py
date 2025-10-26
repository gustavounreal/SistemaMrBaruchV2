from django.db import models
from django.conf import settings
from django.utils import timezone


class Contrato(models.Model):
    STATUS_CHOICES = [
        ('AGUARDANDO_GERACAO', 'Aguardando Geração'),
        ('GERADO', 'Gerado - Pendente Assinatura'),
        ('ENVIADO', 'Enviado ao Cliente'),
        ('ASSINADO', 'Assinado pelo Cliente'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    # Relacionamentos
    venda = models.OneToOneField('vendas.Venda', on_delete=models.CASCADE, related_name='contrato')
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE, related_name='contratos')
    
    # Informações do Contrato
    numero_contrato = models.CharField(max_length=50, unique=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='AGUARDANDO_GERACAO')
    
    # Datas
    data_geracao = models.DateTimeField(null=True, blank=True)
    data_envio = models.DateTimeField(null=True, blank=True)
    data_assinatura = models.DateTimeField(null=True, blank=True)
    
    # Assinaturas
    assinatura_gov = models.BooleanField(default=False, verbose_name='Assinatura Gov.br')
    assinatura_manual = models.BooleanField(default=False, verbose_name='Assinatura Manual')
    
    # Arquivos
    arquivo_contrato = models.FileField(upload_to='contratos/', null=True, blank=True)
    arquivo_assinado = models.FileField(upload_to='contratos/assinados/', null=True, blank=True)
    
    # Observações
    observacoes = models.TextField(blank=True)
    
    # Timeline de status (JSON)
    historico_status = models.JSONField(
        default=list,
        blank=True,
        help_text='Histórico de mudanças de status com timestamps'
    )
    
    # Controle
    usuario_geracao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, 
                                       null=True, related_name='contratos_gerados')
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Contrato {self.numero_contrato or self.id} - {self.cliente.lead.nome_completo}"
    
    def gerar_numero_contrato(self):
        """Gera número único do contrato baseado na data e ID"""
        if not self.numero_contrato:
            ano = timezone.now().year
            self.numero_contrato = f"CONT-{ano}-{self.id:05d}"
            self.save()
    
    def adicionar_historico_status(self, novo_status, usuario=None, observacao=''):
        """Adiciona entrada no histórico de status"""
        if not self.historico_status:
            self.historico_status = []
        
        entrada = {
            'status': novo_status,
            'data': timezone.now().isoformat(),
            'usuario': usuario.get_full_name() if usuario else 'Sistema',
            'observacao': observacao
        }
        
        self.historico_status.append(entrada)
        self.save(update_fields=['historico_status'])
    
    def mudar_status(self, novo_status, usuario=None, observacao=''):
        """Muda status do contrato e registra no histórico"""
        status_antigo = self.status
        self.status = novo_status
        
        # Atualizar datas conforme o status
        if novo_status == 'GERADO' and not self.data_geracao:
            self.data_geracao = timezone.now()
        elif novo_status == 'ENVIADO' and not self.data_envio:
            self.data_envio = timezone.now()
        elif novo_status == 'ASSINADO' and not self.data_assinatura:
            self.data_assinatura = timezone.now()
        
        self.save()
        
        # Registrar no histórico
        obs_completa = f"Status alterado de {status_antigo} para {novo_status}"
        if observacao:
            obs_completa += f" - {observacao}"
        
        self.adicionar_historico_status(novo_status, usuario, obs_completa)
    
    @property
    def dias_com_cliente(self):
        """Calcula quantos dias o contrato está com o cliente desde o envio"""
        if self.data_envio and not self.data_assinatura:
            from django.utils import timezone
            return (timezone.now() - self.data_envio).days
        return 0
    
    @property
    def tempo_envio_formatado(self):
        """Retorna o tempo de envio formatado"""
        dias = self.dias_com_cliente
        if dias == 0:
            return "Hoje"
        elif dias == 1:
            return "1 dia"
        else:
            return f"{dias} dias"
    
    class Meta:
        verbose_name = "Contrato"
        verbose_name_plural = "Contratos"
        ordering = ['-data_criacao']


class DocumentoLegal(models.Model):
    TIPO_DOCUMENTO_CHOICES = [
        ('CONTRATO', 'Contrato'),
        ('PROCURACAO', 'Procuração'),
        ('REQUERIMENTO', 'Requerimento'),
        ('OUTROS', 'Outros'),
    ]
    
    contrato = models.ForeignKey(Contrato, on_delete=models.CASCADE, related_name='documentos')
    tipo = models.CharField(max_length=20, choices=TIPO_DOCUMENTO_CHOICES, default='OUTROS')
    nome_documento = models.CharField(max_length=255)
    arquivo = models.FileField(upload_to='documentos_legais/')
    
    # Controle
    usuario_upload = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    data_upload = models.DateTimeField(auto_now_add=True)
    observacoes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.nome_documento}"
    
    class Meta:
        verbose_name = "Documento Legal"
        verbose_name_plural = "Documentos Legais"
        ordering = ['-data_upload']