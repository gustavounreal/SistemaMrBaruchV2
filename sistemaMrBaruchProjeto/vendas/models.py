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
    
    STATUS_COMPLIANCE_CHOICES = [
        ('AGUARDANDO_CONFERENCIA', 'Aguardando Conferência'),
        ('CONFERENCIA_OK', 'Conferência OK'),
        ('COLETANDO_DOCUMENTOS', 'Coletando Documentos'),
        ('DOCUMENTOS_OK', 'Documentos OK'),
        ('EMITINDO_CONTRATO', 'Emitindo Contrato'),
        ('CONTRATO_ENVIADO', 'Contrato Enviado'),
        ('AGUARDANDO_ASSINATURA', 'Aguardando Assinatura'),
        ('CONTRATO_ASSINADO', 'Contrato Assinado'),
        ('CONCLUIDO', 'Concluído'),
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
        choices=STATUS_COMPLIANCE_CHOICES,
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
    
    # ========== NOTA FISCAL ==========
    cliente_quer_nf = models.BooleanField(
        default=False,
        verbose_name="Cliente deseja Nota Fiscal?",
        help_text="Marcar se cliente solicitou emissão de NF-e"
    )
    
    nf_tipo_pessoa = models.CharField(
        max_length=2,
        choices=[('PF', 'Pessoa Física'), ('PJ', 'Pessoa Jurídica')],
        blank=True,
        null=True,
        help_text="Tipo de pessoa para emissão da NF"
    )
    
    nf_email = models.EmailField(
        blank=True,
        null=True,
        help_text="E-mail para envio da Nota Fiscal (pode ser diferente do e-mail principal)"
    )
    
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

class EntradaVenda(models.Model):
    """
    Modelo para gerenciar múltiplas entradas de uma venda.
    Permite até 2 entradas com valores e datas independentes.
    """
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('PAGO', 'Pago'),
        ('VENCIDO', 'Vencido'),
        ('CANCELADO', 'Cancelado'),
    ]
    
    FORMA_PAGAMENTO_CHOICES = [
        ('BOLETO', 'Boleto'),
        ('PIX', 'PIX'),
        ('DINHEIRO', 'Dinheiro'),
        ('CARTAO', 'Cartão'),
    ]
    
    # Relacionamentos
    venda = models.ForeignKey(Venda, on_delete=models.CASCADE, related_name='entradas')
    numero_entrada = models.IntegerField(help_text='Número sequencial da entrada (1 ou 2)')
    
    # Valores e datas
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField(help_text='Data de vencimento da entrada')
    data_pagamento = models.DateTimeField(null=True, blank=True, help_text='Data do pagamento confirmado')
    
    # Forma de pagamento
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_PAGAMENTO_CHOICES, default='PIX')
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDENTE')
    
    # Integração ASAAS
    asaas_payment_id = models.CharField(max_length=255, blank=True, null=True, help_text='ID da cobrança no ASAAS')
    pix_code = models.TextField(blank=True, null=True, help_text='Código copia e cola do PIX')
    pix_qr_code_url = models.TextField(blank=True, null=True, help_text='URL da imagem do QR Code')
    url_boleto = models.URLField(blank=True, null=True, help_text='URL do boleto')
    codigo_barras = models.TextField(blank=True, null=True, help_text='Código de barras do boleto')
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Entrada de Venda"
        verbose_name_plural = "Entradas de Venda"
        unique_together = ['venda', 'numero_entrada']
        ordering = ['venda', 'numero_entrada']
    
    def __str__(self):
        return f"Entrada {self.numero_entrada} - Venda #{self.venda.id} - R$ {self.valor} - {self.status}"


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
    
    # Dados de qualificação (Etapa 1) - Campos opcionais
    prazo_risco = models.CharField(max_length=50, choices=PRAZO_RISCO_CHOICES, blank=True, null=True)
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
    FREQUENCIA_PAGAMENTO_CHOICES = [
        ('SEMANAL', 'Semanal'),
        ('QUINZENAL', 'Quinzenal'),
        ('MENSAL', 'Mensal'),
    ]
    
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valor_entrada = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantidade_parcelas = models.PositiveIntegerField(null=True, blank=True)
    valor_parcela = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    frequencia_pagamento = models.CharField(max_length=20, choices=FREQUENCIA_PAGAMENTO_CHOICES, blank=True, default='MENSAL')
    
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


class EntradaPreVenda(models.Model):
    """
    Modelo para gerenciar múltiplas entradas de uma pré-venda.
    Permite até 2 entradas com valores e datas independentes.
    Facilita a conversão para EntradaVenda quando a pré-venda for aceita.
    """
    FORMA_PAGAMENTO_CHOICES = [
        ('BOLETO', 'Boleto'),
        ('PIX', 'PIX'),
        ('DINHEIRO', 'Dinheiro'),
        ('CARTAO', 'Cartão'),
    ]
    
    # Relacionamentos
    pre_venda = models.ForeignKey(PreVenda, on_delete=models.CASCADE, related_name='entradas')
    numero_entrada = models.IntegerField(help_text='Número sequencial da entrada (1 ou 2)')
    
    # Valores e datas
    valor = models.DecimalField(max_digits=10, decimal_places=2)
    data_vencimento = models.DateField(help_text='Data de vencimento prevista da entrada')
    
    # Forma de pagamento prevista
    forma_pagamento = models.CharField(max_length=20, choices=FORMA_PAGAMENTO_CHOICES, default='PIX')
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Entrada de Pré-Venda"
        verbose_name_plural = "Entradas de Pré-Venda"
        unique_together = ['pre_venda', 'numero_entrada']
        ordering = ['pre_venda', 'numero_entrada']
    
    def __str__(self):
        return f"Entrada {self.numero_entrada} - Pré-Venda #{self.pre_venda.id} - R$ {self.valor}"


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


class EstrategiaRepescagem(models.Model):
    """
    Estratégias de repescagem configuráveis por motivo de recusa
    Gerenciável pelo grupo Administrador
    """
    motivo_recusa = models.ForeignKey(
        MotivoRecusa,
        on_delete=models.CASCADE,
        related_name='estrategias'
    )
    titulo = models.CharField(max_length=200, help_text="Título da estratégia")
    descricao = models.TextField(help_text="Descrição detalhada da estratégia")
    ordem = models.IntegerField(default=0, help_text="Ordem de exibição")
    ativo = models.BooleanField(default=True)
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Estratégia de Repescagem"
        verbose_name_plural = "Estratégias de Repescagem"
        ordering = ['motivo_recusa', 'ordem', 'titulo']
    
    def __str__(self):
        return f"{self.motivo_recusa.nome} - {self.titulo}"


class RepescagemLead(models.Model):
    """
    Registro de repescagem de leads que não fecharam na pré-venda
    Gerenciado pelo grupo Comercial2
    """
    STATUS_CHOICES = [
        ('PENDENTE', 'Pendente'),
        ('EM_CONTATO', 'Em Contato'),
        ('AGUARDANDO_RESPOSTA', 'Aguardando Resposta'),
        ('INTERESSADO', 'Interessado - Negociando'),
        ('CONDICOES_ESPECIAIS', 'Condições Especiais Aplicadas'),
        ('CONVERTIDO', 'Convertido - Enviado ao Compliance'),
        ('SEM_INTERESSE', 'Sem Interesse'),
        ('LEAD_LIXO', 'Lead Lixo'),
    ]
    
    # Relacionamentos principais
    lead = models.ForeignKey(
        'marketing.Lead',
        on_delete=models.CASCADE,
        related_name='repescagens'
    )
    pre_venda = models.ForeignKey(
        PreVenda,
        on_delete=models.CASCADE,
        related_name='repescagens'
    )
    motivo_recusa = models.ForeignKey(
        MotivoRecusa,
        on_delete=models.PROTECT,
        related_name='repescagens'
    )
    
    # Responsáveis
    consultor_original = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='repescagens_originadas',
        help_text="Consultor que atendeu originalmente"
    )
    consultor_repescagem = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='repescagens_atendidas',
        help_text="Consultor do Comercial 2 responsável pela repescagem"
    )
    
    # Status e controle
    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='PENDENTE'
    )
    tentativas_contato = models.PositiveIntegerField(default=0)
    
    # Condições especiais oferecidas
    condicoes_especiais_aplicadas = models.BooleanField(default=False)
    descricao_condicoes_especiais = models.TextField(
        blank=True,
        help_text="Detalhes das condições especiais oferecidas"
    )
    
    # Nova proposta (se houver alteração)
    novo_valor_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Novo valor total proposto"
    )
    novo_valor_entrada = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Novo valor de entrada proposto"
    )
    nova_quantidade_parcelas = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Nova quantidade de parcelas"
    )
    novo_valor_parcela = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Novo valor da parcela"
    )
    
    # Observações e histórico
    observacoes_consultor_original = models.TextField(
        blank=True,
        help_text="Observações do consultor original"
    )
    observacoes_repescagem = models.TextField(
        blank=True,
        help_text="Observações da repescagem"
    )
    resposta_lead = models.TextField(
        blank=True,
        help_text="Resposta/Feedback do lead"
    )
    proximos_passos = models.TextField(
        blank=True,
        help_text="Próximos passos planejados"
    )
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    data_primeiro_contato = models.DateTimeField(null=True, blank=True)
    data_ultimo_contato = models.DateTimeField(null=True, blank=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Repescagem de Lead"
        verbose_name_plural = "Repescagens de Leads"
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"Repescagem #{self.id} - {self.lead.nome_completo} - {self.status}"
    
    def tempo_no_comercial2(self):
        """Retorna o tempo em dias que o lead está no comercial 2"""
        if self.data_conclusao:
            delta = self.data_conclusao - self.data_criacao
        else:
            delta = timezone.now() - self.data_criacao
        return delta.days
    
    def incrementar_tentativa(self):
        """Incrementa o contador de tentativas de contato"""
        self.tentativas_contato += 1
        self.data_ultimo_contato = timezone.now()
        if self.tentativas_contato == 1:
            self.data_primeiro_contato = timezone.now()
        self.save()
    
    def marcar_como_convertido(self):
        """Marca a repescagem como convertida e atualiza o lead"""
        from compliance.models import AnaliseCompliance, StatusAnaliseCompliance
        
        self.status = 'CONVERTIDO'
        self.data_conclusao = timezone.now()
        self.save()
        
        # Atualiza o status do lead para EM_COMPLIANCE
        self.lead.status = 'EM_COMPLIANCE'
        self.lead.passou_compliance = False
        
        # INCREMENTAR CONTADOR DE REPESCAGENS
        self.lead.incrementar_repescagens()
        
        self.lead.save()
        
        # RESETAR PRÉ-VENDA ANTERIOR (se existir)
        # Quando o lead volta do Comercial 2, qualquer pré-venda anterior deve ser removida
        # para que o novo consultor possa fazer uma nova abordagem
        try:
            preventas_antigas = self.lead.pre_vendas.all()
            if preventas_antigas.exists():
                count = preventas_antigas.count()
                preventas_antigas.delete()
                # Log interno para rastreamento
                print(f"[Comercial2→Compliance] Removidas {count} pré-venda(s) antiga(s) do lead {self.lead.nome_completo}")
        except Exception as e:
            # Não bloquear o fluxo se houver problema ao deletar pré-vendas
            print(f"[AVISO] Erro ao remover pré-vendas antigas: {e}")
            pass
        
        # Criar ou atualizar análise de compliance
        analise, created = AnaliseCompliance.objects.get_or_create(
            lead=self.lead,
            defaults={
                'status': StatusAnaliseCompliance.AGUARDANDO,
                'observacoes_analise': f'Lead convertido pelo Comercial 2 (Repescagem #{self.id})'
            }
        )

        # Registrar histórico de origem (sempre que vier do Comercial 2)
        try:
            from compliance.models import HistoricoAnaliseCompliance

            HistoricoAnaliseCompliance.objects.create(
                analise=analise,
                acao='REENVIADO_COMERCIAL2',
                usuario=None,
                descricao=(
                    f'Lead reenviado do Comercial 2 (Repescagem #{self.id}). '
                    f'Origem: Repescagem - Conversão pelo Comercial 2.'
                )
            )
        except Exception:
            # Não bloquear o fluxo se houver problema no histórico
            pass

        # Se já existia, SEMPRE resetar para AGUARDANDO (pois o lead quer uma nova chance)
        if not created:
            status_anterior = analise.get_status_display()

            # Resetar análise
            analise.status = StatusAnaliseCompliance.AGUARDANDO
            analise.consultor_atribuido = None  # Remover consultor anterior
            analise.data_atribuicao = None
            analise.classificacao = 'NAO_CLASSIFICADO'  # Resetar classificação
            analise.observacoes_analise += (
                f'\n\n[{timezone.now().strftime("%d/%m/%Y %H:%M")}] '
                f'Lead retornou do Comercial 2 (Repescagem #{self.id}) '
                f'- Status anterior: {status_anterior} → Resetado para nova análise'
            )
            analise.save()
    
    def marcar_como_lead_lixo(self):
        """Marca a repescagem e o lead como lead lixo"""
        self.status = 'LEAD_LIXO'
        self.data_conclusao = timezone.now()
        self.save()
        
        # Atualiza o status do lead
        self.lead.status = 'PERDIDO'
        self.lead.save()


class HistoricoRepescagem(models.Model):
    """
    Histórico detalhado de interações durante a repescagem
    """
    TIPO_INTERACAO_CHOICES = [
        ('LIGACAO', 'Ligação'),
        ('WHATSAPP', 'WhatsApp'),
        ('EMAIL', 'E-mail'),
        ('SMS', 'SMS'),
        ('VISITA', 'Visita Presencial'),
        ('OUTROS', 'Outros'),
    ]
    
    repescagem = models.ForeignKey(
        RepescagemLead,
        on_delete=models.CASCADE,
        related_name='historico_interacoes'
    )
    tipo_interacao = models.CharField(max_length=20, choices=TIPO_INTERACAO_CHOICES)
    descricao = models.TextField(help_text="Descrição da interação")
    resultado = models.TextField(blank=True, help_text="Resultado/Resposta obtida")
    
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True
    )
    
    data_interacao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Histórico de Repescagem"
        verbose_name_plural = "Históricos de Repescagem"
        ordering = ['-data_interacao']
    
    def __str__(self):
        return f"{self.get_tipo_interacao_display()} - {self.repescagem.lead.nome_completo} - {self.data_interacao.strftime('%d/%m/%Y %H:%M')}"


class ProgressoServico(models.Model):
    """
    Controla o progresso do serviço contratado pelo cliente
    Usado na área do cliente para visualização do andamento
    """
    ETAPAS_CHOICES = [
        (0, 'Etapa 1 - Atendimento Iniciado'),
        (20, 'Etapa 2 - Elaboração e Protocolo'),
        (40, 'Etapa 3 - Análise e Retorno'),
        (60, 'Etapa 4 - Monitoramento'),
        (80, 'Etapa 5 - Conclusão das Atualizações'),
        (100, 'Etapa 6 - Encerramento Final'),
    ]
    
    venda = models.OneToOneField(
        Venda,
        on_delete=models.CASCADE,
        related_name='progresso_servico'
    )
    
    # Progresso atual
    etapa_atual = models.IntegerField(
        choices=ETAPAS_CHOICES,
        default=0,
        help_text="Etapa atual do serviço (0, 20, 40, 60, 80, 100)"
    )
    
    # Datas de cada etapa
    data_etapa_1 = models.DateTimeField(null=True, blank=True, help_text="Atendimento Iniciado")
    data_etapa_2 = models.DateTimeField(null=True, blank=True, help_text="Elaboração e Protocolo")
    data_etapa_3 = models.DateTimeField(null=True, blank=True, help_text="Análise e Retorno")
    data_etapa_4 = models.DateTimeField(null=True, blank=True, help_text="Monitoramento")
    data_etapa_5 = models.DateTimeField(null=True, blank=True, help_text="Conclusão das Atualizações")
    data_etapa_6 = models.DateTimeField(null=True, blank=True, help_text="Encerramento Final")
    
    # Observações administrativas (não visível ao cliente)
    observacoes_internas = models.TextField(
        blank=True,
        help_text="Observações internas sobre o andamento"
    )
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Progresso do Serviço"
        verbose_name_plural = "Progressos dos Serviços"
        ordering = ['-data_atualizacao']
    
    def __str__(self):
        return f"Progresso Venda #{self.venda.id} - {self.etapa_atual}%"
    
    def get_proxima_atualizacao(self):
        """Calcula a data da próxima atualização prevista (15 dias após última atualização)"""
        if self.data_atualizacao:
            from datetime import timedelta
            return self.data_atualizacao.date() + timedelta(days=15)
        return None
    
    def get_etapa_info(self):
        """Retorna informações da etapa atual"""
        etapas_info = {
            0: {
                'titulo': 'Etapa 1 — Atendimento Iniciado e Preparação da Defesa',
                'status': '✅ Concluído',
                'descricao': 'Seu atendimento foi iniciado e nossos especialistas já elaboraram o resumo técnico do caso.'
            },
            20: {
                'titulo': 'Etapa 2 — Elaboração e Protocolo da Defesa (15 dias)',
                'status': '⚙️ Em andamento',
                'descricao': 'Nossa equipe elabora a defesa administrativa personalizada e encaminha aos órgãos de proteção ao crédito.'
            },
            40: {
                'titulo': 'Etapa 3 — Análise e Retorno dos Órgãos (30 dias)',
                'status': '⚙️ Em andamento',
                'descricao': 'As defesas protocoladas estão sendo analisadas pelos órgãos competentes.'
            },
            60: {
                'titulo': 'Etapa 4 — Monitoramento das Atualizações (45 dias)',
                'status': '🔄 Em andamento',
                'descricao': 'Monitoramento constante dos sistemas de crédito para identificar eventuais alterações.'
            },
            80: {
                'titulo': 'Etapa 5 — Conclusão das Atualizações (60 dias)',
                'status': '🔄 Em andamento',
                'descricao': 'Grande parte das respostas já foram recebidas. Atuando sobre os casos pendentes.'
            },
            100: {
                'titulo': 'Etapa 6 — Encerramento e Confirmação Final (90 dias)',
                'status': '🏁 Concluído',
                'descricao': 'Validação final das atualizações e comunicação de encerramento do atendimento.'
            }
        }
        return etapas_info.get(self.etapa_atual, etapas_info[0])