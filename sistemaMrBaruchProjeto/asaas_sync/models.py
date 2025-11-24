"""
Models para armazenar dados sincronizados do Asaas
Tabelas separadas para não misturar com os dados do sistema
"""
from django.db import models
from django.utils import timezone


class AsaasClienteSyncronizado(models.Model):
    """Clientes baixados do Asaas"""
    
    # Dados do Asaas
    asaas_customer_id = models.CharField('ID Asaas', max_length=100, unique=True, db_index=True)
    
    # Dados pessoais
    nome = models.CharField('Nome', max_length=255)
    cpf_cnpj = models.CharField('CPF/CNPJ', max_length=18, blank=True, null=True, db_index=True)
    email = models.EmailField('E-mail', blank=True, null=True)
    telefone = models.CharField('Telefone', max_length=20, blank=True, null=True)
    celular = models.CharField('Celular', max_length=20, blank=True, null=True)
    
    # Endereço
    cep = models.CharField('CEP', max_length=10, blank=True, null=True)
    endereco = models.CharField('Endereço', max_length=255, blank=True, null=True)
    numero = models.CharField('Número', max_length=20, blank=True, null=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True, null=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True, null=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True, null=True)
    estado = models.CharField('UF', max_length=2, blank=True, null=True)
    
    # Dados adicionais
    inscricao_municipal = models.CharField('Inscrição Municipal', max_length=50, blank=True, null=True)
    inscricao_estadual = models.CharField('Inscrição Estadual', max_length=50, blank=True, null=True)
    observacoes = models.TextField('Observações', blank=True, null=True)
    external_reference = models.CharField('Referência Externa', max_length=100, blank=True, null=True)
    
    # Metadados do Asaas
    data_criacao_asaas = models.DateTimeField('Criado no Asaas', blank=True, null=True)
    notificacoes_desabilitadas = models.BooleanField('Notificações Desabilitadas', default=False)
    
    # Campos de controle interno
    consultor_responsavel = models.CharField('Consultor Responsável', max_length=255, blank=True, null=True)
    servico_concluido = models.BooleanField('Serviço Concluído', default=False)
    
    # Serviços contratados pelo cliente
    servico_limpa_nome = models.BooleanField('Limpa Nome', default=False)
    servico_retirada_travas = models.BooleanField('Retirada de Travas', default=False)
    servico_restauracao_score = models.BooleanField('Restauração de Score', default=False)
    
    # Controle de sincronização
    sincronizado_em = models.DateTimeField('Sincronizado em', auto_now=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    
    class Meta:
        db_table = 'asaas_sync_clientes'
        verbose_name = 'Cliente Asaas (Sincronizado)'
        verbose_name_plural = 'Clientes Asaas (Sincronizados)'
        ordering = ['-sincronizado_em']
        indexes = [
            models.Index(fields=['cpf_cnpj']),
            models.Index(fields=['asaas_customer_id']),
            models.Index(fields=['-sincronizado_em']),
        ]
    
    def __str__(self):
        return f"{self.nome} ({self.asaas_customer_id})"
    
    def get_valor_total_servico(self):
        """Calcula o valor total de todas as cobranças do cliente"""
        from django.db.models import Sum
        total = self.cobrancas.aggregate(total=Sum('valor'))['total']
        return total or 0
    
    def get_cobrancas_vencidas(self):
        """Retorna cobranças vencidas (OVERDUE) do cliente"""
        return self.cobrancas.filter(status='OVERDUE')
    
    def esta_inadimplente(self):
        """Verifica se o cliente tem cobranças vencidas"""
        return self.get_cobrancas_vencidas().exists()
    
    def get_periodo_inadimplencia(self):
        """Retorna o período de inadimplência (data mais antiga até mais recente)"""
        cobrancas_vencidas = self.get_cobrancas_vencidas().order_by('data_vencimento')
        if not cobrancas_vencidas.exists():
            return None
        
        primeira = cobrancas_vencidas.first().data_vencimento
        ultima = cobrancas_vencidas.last().data_vencimento
        
        if primeira == ultima:
            return primeira.strftime('%d/%m/%Y')
        return f"{primeira.strftime('%d/%m/%Y')} a {ultima.strftime('%d/%m/%Y')}"
    
    def get_valor_inadimplente(self):
        """Retorna o valor total das cobranças vencidas"""
        from django.db.models import Sum
        total = self.get_cobrancas_vencidas().aggregate(total=Sum('valor'))['total']
        return total or 0
    
    def get_cobrancas_pendentes(self):
        """Retorna cobranças pendentes de pagamento (PENDING e OVERDUE)"""
        return self.cobrancas.filter(status__in=['PENDING', 'OVERDUE'])
    
    def get_quantidade_boletos_pendentes(self):
        """Retorna a quantidade de boletos pendentes de pagamento (inclui vencidos)"""
        return self.get_cobrancas_pendentes().count()
    
    def get_servicos_contratados(self):
        """Retorna lista de serviços contratados pelo cliente"""
        servicos = []
        if self.servico_limpa_nome:
            servicos.append('Limpa Nome')
        if self.servico_retirada_travas:
            servicos.append('Retirada de Travas')
        if self.servico_restauracao_score:
            servicos.append('Restauração de Score')
        return servicos
    
    def get_servicos_contratados_display(self):
        """Retorna string formatada dos serviços contratados"""
        servicos = self.get_servicos_contratados()
        if not servicos:
            return 'Nenhum serviço cadastrado'
        return ', '.join(servicos)


class AsaasCobrancaSyncronizada(models.Model):
    """Cobranças/Vendas baixadas do Asaas"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('RECEIVED', 'Recebida'),
        ('CONFIRMED', 'Confirmada'),
        ('OVERDUE', 'Vencida'),
        ('REFUNDED', 'Estornada'),
        ('RECEIVED_IN_CASH', 'Recebida em Dinheiro'),
        ('REFUND_REQUESTED', 'Estorno Solicitado'),
        ('CHARGEBACK_REQUESTED', 'Chargeback Solicitado'),
        ('CHARGEBACK_DISPUTE', 'Disputa de Chargeback'),
        ('AWAITING_CHARGEBACK_REVERSAL', 'Aguardando Reversão de Chargeback'),
        ('DUNNING_REQUESTED', 'Negativação Solicitada'),
        ('DUNNING_RECEIVED', 'Negativação Recebida'),
        ('AWAITING_RISK_ANALYSIS', 'Aguardando Análise de Risco'),
    ]
    
    TIPO_COBRANCA_CHOICES = [
        ('BOLETO', 'Boleto'),
        ('CREDIT_CARD', 'Cartão de Crédito'),
        ('PIX', 'PIX'),
        ('UNDEFINED', 'Indefinido'),
    ]
    
    # Dados do Asaas
    asaas_payment_id = models.CharField('ID Cobrança Asaas', max_length=100, unique=True, db_index=True)
    cliente = models.ForeignKey(
        AsaasClienteSyncronizado,
        on_delete=models.CASCADE,
        related_name='cobrancas',
        verbose_name='Cliente'
    )
    
    # Dados da cobrança
    tipo_cobranca = models.CharField('Tipo', max_length=20, choices=TIPO_COBRANCA_CHOICES)
    status = models.CharField('Status', max_length=50, choices=STATUS_CHOICES, db_index=True)
    valor = models.DecimalField('Valor', max_digits=10, decimal_places=2)
    valor_liquido = models.DecimalField('Valor Líquido', max_digits=10, decimal_places=2, blank=True, null=True)
    descricao = models.TextField('Descrição', blank=True, null=True)
    
    # Datas
    data_vencimento = models.DateField('Data de Vencimento', db_index=True)
    data_pagamento = models.DateField('Data de Pagamento', blank=True, null=True)
    data_criacao_asaas = models.DateTimeField('Criado no Asaas', blank=True, null=True)
    
    # Links de pagamento
    invoice_url = models.URLField('URL da Fatura', blank=True, null=True, max_length=500)
    bank_slip_url = models.URLField('URL do Boleto', blank=True, null=True, max_length=500)
    pix_qrcode_url = models.URLField('URL QR Code PIX', blank=True, null=True, max_length=500)
    pix_copy_paste = models.TextField('PIX Copia e Cola', blank=True, null=True)
    
    # Parcelamento
    numero_parcela = models.IntegerField('Nº Parcela', blank=True, null=True)
    total_parcelas = models.IntegerField('Total de Parcelas', blank=True, null=True)
    
    # Referência externa
    external_reference = models.CharField('Referência Externa', max_length=100, blank=True, null=True)
    
    # Controle de sincronização
    sincronizado_em = models.DateTimeField('Sincronizado em', auto_now=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    
    class Meta:
        db_table = 'asaas_sync_cobrancas'
        verbose_name = 'Cobrança Asaas (Sincronizada)'
        verbose_name_plural = 'Cobranças Asaas (Sincronizadas)'
        ordering = ['-data_vencimento']
        indexes = [
            models.Index(fields=['asaas_payment_id']),
            models.Index(fields=['status']),
            models.Index(fields=['-data_vencimento']),
            models.Index(fields=['cliente', '-data_vencimento']),
        ]
    
    def __str__(self):
        return f"{self.cliente.nome} - {self.valor} - {self.get_status_display()}"
    
    @property
    def esta_vencida(self):
        """Verifica se a cobrança está vencida"""
        if self.status in ['RECEIVED', 'CONFIRMED']:
            return False
        return self.data_vencimento < timezone.now().date()
    
    @property
    def dias_vencimento(self):
        """Dias até o vencimento (negativo se vencido)"""
        delta = self.data_vencimento - timezone.now().date()
        return delta.days
    
    @property
    def dias_vencimento_abs(self):
        """Dias até o vencimento em valor absoluto"""
        return abs(self.dias_vencimento)


class AsaasSyncronizacaoLog(models.Model):
    """Log de sincronizações realizadas"""
    
    STATUS_CHOICES = [
        ('SUCESSO', 'Sucesso'),
        ('ERRO', 'Erro'),
        ('PARCIAL', 'Parcial'),
        ('EM_ANDAMENTO', 'Em Andamento'),
    ]
    
    TIPO_CHOICES = [
        ('COMPLETO', 'Sincronização Completa'),
        ('BOLETOS_FALTANTES', 'Boletos Faltantes'),
        ('ALTERNATIVO', 'Sincronização Alternativa'),
    ]
    
    # Dados da sincronização
    tipo_sincronizacao = models.CharField('Tipo', max_length=30, choices=TIPO_CHOICES, default='COMPLETO')
    data_inicio = models.DateTimeField('Início', auto_now_add=True)
    data_fim = models.DateTimeField('Fim', blank=True, null=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES)
    
    # Estatísticas
    total_clientes = models.IntegerField('Total de Clientes', default=0)
    clientes_novos = models.IntegerField('Clientes Novos', default=0)
    clientes_atualizados = models.IntegerField('Clientes Atualizados', default=0)
    
    total_cobrancas = models.IntegerField('Total de Cobranças', default=0)
    cobrancas_novas = models.IntegerField('Cobranças Novas', default=0)
    cobrancas_atualizadas = models.IntegerField('Cobranças Atualizadas', default=0)
    
    # Mensagens e erros
    mensagem = models.TextField('Mensagem', blank=True, null=True)
    erros = models.TextField('Erros', blank=True, null=True)
    
    # Controle
    usuario = models.CharField('Usuário', max_length=100, blank=True, null=True)
    duracao_segundos = models.IntegerField('Duração (s)', blank=True, null=True)
    
    class Meta:
        db_table = 'asaas_sync_logs'
        verbose_name = 'Log de Sincronização'
        verbose_name_plural = 'Logs de Sincronização'
        ordering = ['-data_inicio']
    
    def __str__(self):
        return f"Sync {self.data_inicio.strftime('%d/%m/%Y %H:%M')} - {self.get_status_display()}"
    
    def calcular_duracao(self):
        """Calcula a duração da sincronização"""
        if self.data_fim and self.data_inicio:
            delta = self.data_fim - self.data_inicio
            self.duracao_segundos = int(delta.total_seconds())
            self.save(update_fields=['duracao_segundos'])


class DocumentoClienteAsaas(models.Model):
    """Documentos anexados aos clientes Asaas"""
    
    TIPO_DOCUMENTO_CHOICES = [
        ('RG', 'RG'),
        ('CPF', 'CPF'),
        ('CNH', 'CNH'),
        ('COMPROVANTE_RESIDENCIA', 'Comprovante de Residência'),
        ('CONTRATO', 'Contrato'),
        ('PROCURACAO', 'Procuração'),
        ('CARTA_AUTORIZACAO', 'Carta de Autorização'),
        ('EXTRATO_BANCARIO', 'Extrato Bancário'),
        ('RELATORIO', 'Relatório'),
        ('OUTROS', 'Outros'),
    ]
    
    cliente = models.ForeignKey(
        AsaasClienteSyncronizado,
        on_delete=models.CASCADE,
        related_name='documentos',
        verbose_name='Cliente'
    )
    tipo = models.CharField('Tipo', max_length=50, choices=TIPO_DOCUMENTO_CHOICES)
    arquivo = models.FileField('Arquivo', upload_to='asaas_clientes_docs/%Y/%m/')
    descricao = models.CharField('Descrição', max_length=255, blank=True, null=True)
    
    # Metadados
    tamanho_original = models.BigIntegerField('Tamanho Original (bytes)', blank=True, null=True)
    tamanho_final = models.BigIntegerField('Tamanho Final (bytes)', blank=True, null=True)
    comprimido = models.BooleanField('Foi Comprimido', default=False)
    
    # Controle
    enviado_por = models.CharField('Enviado por', max_length=100)
    data_upload = models.DateTimeField('Data Upload', auto_now_add=True)
    
    class Meta:
        db_table = 'asaas_sync_documentos_clientes'
        verbose_name = 'Documento Cliente Asaas'
        verbose_name_plural = 'Documentos Clientes Asaas'
        ordering = ['-data_upload']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.cliente.nome}"
    
    def get_tamanho_mb(self):
        """Retorna tamanho do arquivo em MB"""
        if self.arquivo and self.arquivo.size:
            return round(self.arquivo.size / (1024 * 1024), 2)
        return 0
    
    def get_percentual_compressao(self):
        """Retorna percentual de compressão"""
        if self.tamanho_original and self.tamanho_final:
            reducao = ((self.tamanho_original - self.tamanho_final) / self.tamanho_original) * 100
            return round(reducao, 1)
        return 0


# ===================================
# MODELS PARA ASAAS 2 (ALTERNATIVO)
# ===================================

class AsaasClienteSyncronizado2(models.Model):
    """Clientes baixados do Asaas 2 (Alternativo)"""
    
    # Dados do Asaas
    asaas_customer_id = models.CharField('ID Asaas', max_length=100, unique=True, db_index=True)
    
    # Dados pessoais
    nome = models.CharField('Nome', max_length=255)
    cpf_cnpj = models.CharField('CPF/CNPJ', max_length=18, blank=True, null=True, db_index=True)
    email = models.EmailField('E-mail', blank=True, null=True)
    telefone = models.CharField('Telefone', max_length=20, blank=True, null=True)
    celular = models.CharField('Celular', max_length=20, blank=True, null=True)
    
    # Endereço
    cep = models.CharField('CEP', max_length=10, blank=True, null=True)
    endereco = models.CharField('Endereço', max_length=255, blank=True, null=True)
    numero = models.CharField('Número', max_length=20, blank=True, null=True)
    complemento = models.CharField('Complemento', max_length=100, blank=True, null=True)
    bairro = models.CharField('Bairro', max_length=100, blank=True, null=True)
    cidade = models.CharField('Cidade', max_length=100, blank=True, null=True)
    estado = models.CharField('UF', max_length=2, blank=True, null=True)
    
    # Dados adicionais
    inscricao_municipal = models.CharField('Inscrição Municipal', max_length=50, blank=True, null=True)
    inscricao_estadual = models.CharField('Inscrição Estadual', max_length=50, blank=True, null=True)
    observacoes = models.TextField('Observações', blank=True, null=True)
    external_reference = models.CharField('Referência Externa', max_length=100, blank=True, null=True)
    
    # Metadados do Asaas
    data_criacao_asaas = models.DateTimeField('Criado no Asaas', blank=True, null=True)
    notificacoes_desabilitadas = models.BooleanField('Notificações Desabilitadas', default=False)
    
    # Campos de controle interno
    consultor_responsavel = models.CharField('Consultor Responsável', max_length=255, blank=True, null=True)
    servico_concluido = models.BooleanField('Serviço Concluído', default=False)
    
    # Serviços contratados
    servico_limpa_nome = models.BooleanField('Limpa Nome', default=False)
    servico_retirada_travas = models.BooleanField('Retirada de Travas', default=False)
    servico_restauracao_score = models.BooleanField('Restauração de Score', default=False)
    
    # Controle de sincronização
    sincronizado_em = models.DateTimeField('Sincronizado em', auto_now=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    
    class Meta:
        db_table = 'asaas_sync_clientes2'
        verbose_name = 'Cliente Asaas 2 (Sincronizado)'
        verbose_name_plural = 'Clientes Asaas 2 (Sincronizados)'
        ordering = ['-sincronizado_em']
        indexes = [
            models.Index(fields=['cpf_cnpj']),
            models.Index(fields=['asaas_customer_id']),
            models.Index(fields=['-sincronizado_em']),
        ]
    
    def __str__(self):
        return f"{self.nome} ({self.asaas_customer_id})"
    
    def get_valor_total_servico(self):
        """Calcula o valor total de todas as cobranças do cliente"""
        from django.db.models import Sum
        total = self.cobrancas.aggregate(total=Sum('valor'))['total']
        return total or 0
    
    def get_cobrancas_vencidas(self):
        """Retorna cobranças vencidas (OVERDUE) do cliente"""
        return self.cobrancas.filter(status='OVERDUE')
    
    def esta_inadimplente(self):
        """Verifica se o cliente tem cobranças vencidas"""
        return self.get_cobrancas_vencidas().exists()
    
    def get_periodo_inadimplencia(self):
        """Retorna o período de inadimplência (data mais antiga até mais recente)"""
        cobrancas_vencidas = self.get_cobrancas_vencidas().order_by('data_vencimento')
        if not cobrancas_vencidas.exists():
            return None
        
        primeira = cobrancas_vencidas.first().data_vencimento
        ultima = cobrancas_vencidas.last().data_vencimento
        
        if primeira == ultima:
            return primeira.strftime('%d/%m/%Y')
        return f"{primeira.strftime('%d/%m/%Y')} a {ultima.strftime('%d/%m/%Y')}"
    
    def get_valor_inadimplente(self):
        """Retorna o valor total das cobranças vencidas"""
        from django.db.models import Sum
        total = self.get_cobrancas_vencidas().aggregate(total=Sum('valor'))['total']
        return total or 0
    
    def get_quantidade_boletos_pendentes(self):
        """Retorna quantidade de boletos com status PENDING"""
        return self.cobrancas.filter(status='PENDING').count()
    
    def get_servicos_contratados(self):
        """Retorna lista de serviços contratados"""
        servicos = []
        if self.servico_limpa_nome:
            servicos.append('Limpa Nome')
        if self.servico_retirada_travas:
            servicos.append('Retirada de Travas')
        if self.servico_restauracao_score:
            servicos.append('Restauração de Score')
        return servicos
    
    def get_servicos_contratados_display(self):
        """Retorna string com serviços contratados separados por vírgula"""
        servicos = self.get_servicos_contratados()
        return ', '.join(servicos) if servicos else 'Nenhum'


class AsaasCobrancaSyncronizada2(models.Model):
    """Cobranças baixadas do Asaas 2 (Alternativo)"""
    
    STATUS_CHOICES = [
        ('PENDING', 'Pendente'),
        ('RECEIVED', 'Recebida'),
        ('CONFIRMED', 'Confirmada'),
        ('OVERDUE', 'Vencida'),
        ('REFUNDED', 'Estornada'),
        ('RECEIVED_IN_CASH', 'Recebida em Dinheiro'),
        ('REFUND_REQUESTED', 'Estorno Solicitado'),
        ('CHARGEBACK_REQUESTED', 'Chargeback Solicitado'),
        ('CHARGEBACK_DISPUTE', 'Disputa de Chargeback'),
        ('AWAITING_CHARGEBACK_REVERSAL', 'Aguardando Reversão de Chargeback'),
        ('DUNNING_REQUESTED', 'Negativação Solicitada'),
        ('DUNNING_RECEIVED', 'Negativação Recebida'),
        ('AWAITING_RISK_ANALYSIS', 'Aguardando Análise de Risco'),
    ]
    
    TIPO_COBRANCA_CHOICES = [
        ('BOLETO', 'Boleto'),
        ('CREDIT_CARD', 'Cartão de Crédito'),
        ('PIX', 'PIX'),
        ('UNDEFINED', 'Indefinido'),
    ]
    
    # Dados do Asaas
    asaas_payment_id = models.CharField('ID Cobrança Asaas', max_length=100, unique=True, db_index=True)
    cliente = models.ForeignKey(
        AsaasClienteSyncronizado2,
        on_delete=models.CASCADE,
        related_name='cobrancas',
        verbose_name='Cliente'
    )
    
    # Dados da cobrança
    tipo_cobranca = models.CharField('Tipo', max_length=20, choices=TIPO_COBRANCA_CHOICES)
    status = models.CharField('Status', max_length=50, choices=STATUS_CHOICES, db_index=True)
    valor = models.DecimalField('Valor', max_digits=10, decimal_places=2)
    valor_liquido = models.DecimalField('Valor Líquido', max_digits=10, decimal_places=2, blank=True, null=True)
    descricao = models.TextField('Descrição', blank=True, null=True)
    
    # Datas
    data_vencimento = models.DateField('Data de Vencimento', db_index=True)
    data_pagamento = models.DateField('Data de Pagamento', blank=True, null=True)
    data_criacao_asaas = models.DateTimeField('Criado no Asaas', blank=True, null=True)
    
    # Links de pagamento
    invoice_url = models.URLField('URL da Fatura', blank=True, null=True, max_length=500)
    bank_slip_url = models.URLField('URL do Boleto', blank=True, null=True, max_length=500)
    pix_qrcode_url = models.URLField('URL QR Code PIX', blank=True, null=True, max_length=500)
    pix_copy_paste = models.TextField('PIX Copia e Cola', blank=True, null=True)
    
    # Parcelamento
    numero_parcela = models.IntegerField('Nº Parcela', blank=True, null=True)
    total_parcelas = models.IntegerField('Total de Parcelas', blank=True, null=True)
    
    # Referência externa
    external_reference = models.CharField('Referência Externa', max_length=100, blank=True, null=True)
    
    # Controle de sincronização
    sincronizado_em = models.DateTimeField('Sincronizado em', auto_now=True)
    criado_em = models.DateTimeField('Criado em', auto_now_add=True)
    
    class Meta:
        db_table = 'asaas_sync_cobrancas2'
        verbose_name = 'Cobrança Asaas 2 (Sincronizada)'
        verbose_name_plural = 'Cobranças Asaas 2 (Sincronizadas)'
        ordering = ['-data_vencimento']
        indexes = [
            models.Index(fields=['asaas_payment_id']),
            models.Index(fields=['status']),
            models.Index(fields=['-data_vencimento']),
            models.Index(fields=['cliente', '-data_vencimento']),
        ]
    
    def __str__(self):
        return f"{self.cliente.nome} - {self.valor} - {self.get_status_display()}"
    
    @property
    def esta_vencida(self):
        """Verifica se a cobrança está vencida"""
        if self.status in ['RECEIVED', 'CONFIRMED']:
            return False
        return self.data_vencimento < timezone.now().date()
    
    @property
    def dias_vencimento(self):
        """Dias até o vencimento (negativo se vencido)"""
        delta = self.data_vencimento - timezone.now().date()
        return delta.days
    
    @property
    def status_cor(self):
        """Cor do badge de status"""
        cores = {
            'RECEIVED': 'success',
            'CONFIRMED': 'success',
            'PENDING': 'warning',
            'OVERDUE': 'danger',
            'REFUNDED': 'info',
        }
        return cores.get(self.status, 'secondary')
