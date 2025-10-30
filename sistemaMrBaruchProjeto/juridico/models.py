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


class Distrato(models.Model):
    """Modelo para gestão de distratos contratuais"""
    STATUS_CHOICES = [
        ('TENTATIVA_ACORDO', 'Tentativa de Acordo'),
        ('ACORDO_RECUSADO', 'Acordo Recusado'),
        ('MULTA_GERADA', 'Multa Gerada'),
        ('MULTA_PAGA', 'Multa Paga'),
        ('MULTA_VENCIDA', 'Multa Vencida'),
        ('ENVIADO_JURIDICO', 'Enviado ao Jurídico'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    # Relacionamentos
    venda = models.ForeignKey('vendas.Venda', on_delete=models.CASCADE, related_name='distratos')
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE, related_name='distratos')
    contrato = models.ForeignKey(Contrato, on_delete=models.SET_NULL, null=True, blank=True, related_name='distratos')
    
    # Informações do Distrato
    numero_distrato = models.CharField(max_length=50, unique=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='TENTATIVA_ACORDO')
    
    # Acordo
    tentativa_acordo = models.BooleanField(default=True, verbose_name='Tentou acordo?')
    acordo_aceito = models.BooleanField(default=False, verbose_name='Acordo aceito?')
    detalhes_acordo = models.TextField(blank=True, verbose_name='Detalhes da tentativa de acordo')
    
    # Multa
    valor_multa = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    data_vencimento_multa = models.DateField(null=True, blank=True)
    data_pagamento_multa = models.DateField(null=True, blank=True)
    boleto_multa_codigo = models.CharField(max_length=100, blank=True, verbose_name='ID Boleto ASAAS')
    boleto_multa_url = models.URLField(blank=True, verbose_name='URL Boleto ASAAS')
    boleto_multa_linha_digitavel = models.CharField(max_length=200, blank=True, verbose_name='Linha Digitável')
    
    # Arquivos
    arquivo_distrato = models.FileField(upload_to='distratos/', null=True, blank=True)
    arquivo_boleto_multa = models.FileField(upload_to='distratos/boletos/', null=True, blank=True)
    
    # Datas importantes
    data_solicitacao = models.DateTimeField(auto_now_add=True)
    data_tentativa_acordo = models.DateTimeField(null=True, blank=True)
    data_recusa_acordo = models.DateTimeField(null=True, blank=True)
    data_geracao_multa = models.DateTimeField(null=True, blank=True)
    data_envio_juridico = models.DateTimeField(null=True, blank=True)
    
    # Controle
    usuario_solicitacao = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True,
        related_name='distratos_solicitados'
    )
    
    # Observações
    observacoes = models.TextField(blank=True)
    historico = models.JSONField(default=list, blank=True)
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Distrato {self.numero_distrato or self.id} - {self.cliente.lead.nome_completo}"
    
    def gerar_numero_distrato(self):
        """Gera número único do distrato"""
        if not self.numero_distrato:
            ano = timezone.now().year
            self.numero_distrato = f"DIST-{ano}-{self.id:05d}"
            self.save()
    
    def adicionar_historico(self, acao, usuario=None, detalhes=''):
        """Adiciona entrada no histórico"""
        if not self.historico:
            self.historico = []
        
        entrada = {
            'acao': acao,
            'data': timezone.now().isoformat(),
            'usuario': usuario.get_full_name() if usuario else 'Sistema',
            'detalhes': detalhes
        }
        
        self.historico.append(entrada)
        self.save(update_fields=['historico'])
    
    @property
    def multa_vencida(self):
        """Verifica se a multa está vencida"""
        if self.data_vencimento_multa and not self.data_pagamento_multa:
            from django.utils import timezone
            return timezone.now().date() > self.data_vencimento_multa
        return False
    
    @property
    def dias_multa_vencida(self):
        """Calcula dias de atraso da multa"""
        if self.multa_vencida:
            from django.utils import timezone
            return (timezone.now().date() - self.data_vencimento_multa).days
        return 0
    
    class Meta:
        verbose_name = "Distrato"
        verbose_name_plural = "Distratos"
        ordering = ['-data_criacao']


class ProcessoJuridico(models.Model):
    """Modelo para gestão de processos jurídicos"""
    STATUS_CHOICES = [
        ('EM_ANDAMENTO', 'Em Andamento'),
        ('AGUARDANDO_ASSINATURA', 'Aguardando Assinatura Cliente'),
        ('ASSINADO', 'Assinado pelo Cliente'),
        ('CONCLUIDO', 'Concluído'),
        ('ARQUIVADO', 'Arquivado'),
    ]
    
    TIPO_PROCESSO_CHOICES = [
        ('DISTRATO', 'Distrato Contratual'),
        ('COBRANCA', 'Cobrança Judicial'),
        ('OUTROS', 'Outros'),
    ]
    
    # Relacionamentos
    distrato = models.OneToOneField(Distrato, on_delete=models.CASCADE, related_name='processo_juridico')
    cliente = models.ForeignKey('clientes.Cliente', on_delete=models.CASCADE, related_name='processos_juridicos')
    venda = models.ForeignKey('vendas.Venda', on_delete=models.CASCADE, related_name='processos_juridicos')
    
    # Identificação do Processo
    numero_processo = models.CharField(max_length=50, unique=True, blank=True)
    tipo_processo = models.CharField(max_length=20, choices=TIPO_PROCESSO_CHOICES, default='DISTRATO')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='EM_ANDAMENTO')
    
    # Datas do Processo
    data_inicio = models.DateTimeField(auto_now_add=True)
    data_envio_juridico = models.DateTimeField(null=True, blank=True)
    data_assinatura_cliente = models.DateTimeField(null=True, blank=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)
    
    # Assinaturas
    assinatura_cliente = models.BooleanField(default=False)
    arquivo_assinado = models.FileField(upload_to='processos/assinados/', null=True, blank=True)
    
    # Documentos do Processo
    arquivo_processo = models.FileField(upload_to='processos/', null=True, blank=True)
    
    # Controle
    usuario_responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='processos_responsavel'
    )
    
    # Observações e Histórico
    observacoes = models.TextField(blank=True)
    historico = models.JSONField(default=list, blank=True)
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Processo {self.numero_processo or self.id} - {self.cliente.lead.nome_completo}"
    
    def gerar_numero_processo(self):
        """Gera número único do processo"""
        if not self.numero_processo:
            ano = timezone.now().year
            self.numero_processo = f"PROC-{ano}-{self.id:05d}"
            self.save()
    
    def adicionar_historico(self, acao, usuario=None, detalhes=''):
        """Adiciona entrada no histórico"""
        if not self.historico:
            self.historico = []
        
        entrada = {
            'acao': acao,
            'data': timezone.now().isoformat(),
            'usuario': usuario.get_full_name() if usuario else 'Sistema',
            'detalhes': detalhes
        }
        
        self.historico.append(entrada)
        self.save(update_fields=['historico'])
    
    def mudar_status(self, novo_status, usuario=None, observacao=''):
        """Muda status do processo"""
        status_antigo = self.status
        self.status = novo_status
        
        # Atualizar datas conforme o status
        if novo_status == 'AGUARDANDO_ASSINATURA' and not self.data_envio_juridico:
            self.data_envio_juridico = timezone.now()
        elif novo_status == 'ASSINADO' and not self.data_assinatura_cliente:
            self.data_assinatura_cliente = timezone.now()
            self.assinatura_cliente = True
        elif novo_status == 'CONCLUIDO' and not self.data_conclusao:
            self.data_conclusao = timezone.now()
        
        self.save()
        
        # Registrar no histórico
        obs_completa = f"Status alterado de {status_antigo} para {novo_status}"
        if observacao:
            obs_completa += f" - {observacao}"
        
        self.adicionar_historico('mudanca_status', usuario, obs_completa)
    
    @property
    def dias_em_andamento(self):
        """Calcula dias desde o início do processo"""
        if self.data_inicio:
            from django.utils import timezone
            if self.data_conclusao:
                return (self.data_conclusao - self.data_inicio).days
            return (timezone.now() - self.data_inicio).days
        return 0
    
    @property
    def distrato_pago(self):
        """Verifica se o distrato foi pago"""
        return self.distrato.data_pagamento_multa is not None
    
    class Meta:
        verbose_name = "Processo Jurídico"
        verbose_name_plural = "Processos Jurídicos"
        ordering = ['-data_inicio']
