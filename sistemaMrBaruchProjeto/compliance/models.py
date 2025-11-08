from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from marketing.models import Lead
from vendas.models import PreVenda

User = get_user_model()


class ClassificacaoLead(models.TextChoices):
    """Classificações de perfil do lead baseado em valor de dívida"""
    BRONZE = 'BRONZE', 'Bronze (até R$ 10.000)'
    PRATA = 'PRATA', 'Prata (R$ 10.001 a R$ 50.000)'
    OURO = 'OURO', 'Ouro (R$ 50.001 a R$ 100.000)'
    PLATINA = 'PLATINA', 'Platina (acima de R$ 100.000)'
    NAO_CLASSIFICADO = 'NAO_CLASSIFICADO', 'Não Classificado'


class StatusAnaliseCompliance(models.TextChoices):
    """Status da análise de compliance"""
    AGUARDANDO = 'AGUARDANDO', 'Aguardando Análise'
    EM_ANALISE = 'EM_ANALISE', 'Em Análise'
    APROVADO = 'APROVADO', 'Aprovado - Aguardando Atribuição'
    ATRIBUIDO = 'ATRIBUIDO', 'Atribuído ao Consultor'
    REPROVADO = 'REPROVADO', 'Reprovado'
    EM_PRE_VENDA = 'EM_PRE_VENDA', 'Em Pré-Venda'


class StatusPosVendaCompliance(models.TextChoices):
    """Status das etapas pós-venda (após conversão)"""
    AGUARDANDO_CONFERENCIA = 'AGUARDANDO_CONFERENCIA', 'Aguardando Conferência'
    CONFERENCIA_OK = 'CONFERENCIA_OK', 'Conferência OK'
    COLETANDO_DOCUMENTOS = 'COLETANDO_DOCUMENTOS', 'Coletando Documentos'
    DOCUMENTOS_OK = 'DOCUMENTOS_OK', 'Documentos OK'
    EMITINDO_CONTRATO = 'EMITINDO_CONTRATO', 'Emitindo Contrato'
    CONTRATO_ENVIADO = 'CONTRATO_ENVIADO', 'Contrato Enviado'
    AGUARDANDO_ASSINATURA = 'AGUARDANDO_ASSINATURA', 'Aguardando Assinatura'
    CONTRATO_ASSINADO = 'CONTRATO_ASSINADO', 'Contrato Assinado'
    CONCLUIDO = 'CONCLUIDO', 'Concluído'


class AnaliseCompliance(models.Model):
    """
    Análise de Compliance do Lead após pagamento do levantamento.
    Responsável por classificar o lead e atribuir ao consultor adequado.
    """
    lead = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='analises_compliance')
    
    # Análise pré-venda
    classificacao = models.CharField(
        max_length=20,
        choices=ClassificacaoLead.choices,
        default=ClassificacaoLead.NAO_CLASSIFICADO,
        verbose_name='Classificação do Lead'
    )
    valor_divida_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name='Valor Total da Dívida'
    )
    status = models.CharField(
        max_length=20,
        choices=StatusAnaliseCompliance.choices,
        default=StatusAnaliseCompliance.AGUARDANDO,
        verbose_name='Status da Análise'
    )
    
    # Atribuição ao consultor
    consultor_atribuido = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='leads_compliance_atribuidos',
        verbose_name='Consultor Atribuído'
    )
    data_atribuicao = models.DateTimeField(null=True, blank=True, verbose_name='Data de Atribuição')
    
    # Análise e observações
    analista_responsavel = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analises_compliance_realizadas',
        verbose_name='Analista Responsável'
    )
    observacoes_analise = models.TextField(blank=True, verbose_name='Observações da Análise')
    motivo_reprovacao = models.TextField(blank=True, verbose_name='Motivo da Reprovação')
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True, verbose_name='Data de Criação')
    data_analise = models.DateTimeField(null=True, blank=True, verbose_name='Data da Análise')
    data_atualizacao = models.DateTimeField(auto_now=True, verbose_name='Última Atualização')
    
    # Integração com pré-venda
    pre_venda = models.ForeignKey(
        PreVenda,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='analise_compliance',
        verbose_name='Pré-Venda Associada'
    )

    class Meta:
        verbose_name = 'Análise de Compliance'
        verbose_name_plural = 'Análises de Compliance'
        ordering = ['-data_criacao']

    def __str__(self):
        return f"Análise {self.id} - {self.lead.nome_completo} - {self.get_status_display()}"

    def classificar_automaticamente(self):
        """Classifica o lead automaticamente baseado no valor da dívida"""
        if not self.valor_divida_total:
            self.classificacao = ClassificacaoLead.NAO_CLASSIFICADO
        elif self.valor_divida_total <= 10000:
            self.classificacao = ClassificacaoLead.BRONZE
        elif self.valor_divida_total <= 50000:
            self.classificacao = ClassificacaoLead.PRATA
        elif self.valor_divida_total <= 100000:
            self.classificacao = ClassificacaoLead.OURO
        else:
            self.classificacao = ClassificacaoLead.PLATINA
        self.save()

    def atribuir_consultor(self, consultor, analista):
        """Atribui o lead a um consultor e marca como aprovado pelo Compliance"""
        self.consultor_atribuido = consultor
        self.data_atribuicao = timezone.now()
        self.status = StatusAnaliseCompliance.ATRIBUIDO
        self.analista_responsavel = analista
        self.save()
        
        # Atualiza o lead para indicar que passou pelo Compliance e está QUALIFICADO
        self.lead.passou_compliance = True
        self.lead.status = 'QUALIFICADO'  # ✅ CORRIGIDO: Agora usa QUALIFICADO (na mão do consultor)
        self.lead.save(update_fields=['passou_compliance', 'status'])
        
        # Registra no histórico
        HistoricoAnaliseCompliance.objects.create(
            analise=self,
            acao='ATRIBUICAO',
            usuario=analista,
            descricao=f'Lead atribuído ao consultor {consultor.get_full_name() or consultor.username}'
        )


class GestaoDocumentosPosVenda(models.Model):
    """
    Gestão de documentos e conferência pós-venda (após conversão).
    Reaproveita lógica do módulo jurídico.
    """
    analise_compliance = models.OneToOneField(
        AnaliseCompliance,
        on_delete=models.CASCADE,
        related_name='gestao_pos_venda',
        verbose_name='Análise de Compliance'
    )
    pre_venda = models.ForeignKey(
        PreVenda,
        on_delete=models.CASCADE,
        related_name='gestao_compliance',
        verbose_name='Pré-Venda'
    )
    
    # Status do processo pós-venda
    status = models.CharField(
        max_length=30,
        choices=StatusPosVendaCompliance.choices,
        default=StatusPosVendaCompliance.AGUARDANDO_CONFERENCIA,
        verbose_name='Status'
    )
    
    # Conferência de cadastro
    cadastro_conferido = models.BooleanField(default=False, verbose_name='Cadastro Conferido')
    data_conferencia_cadastro = models.DateTimeField(null=True, blank=True)
    observacoes_cadastro = models.TextField(blank=True)
    
    # Documentos
    documentos_coletados = models.BooleanField(default=False, verbose_name='Documentos Coletados')
    data_coleta_documentos = models.DateTimeField(null=True, blank=True)
    lista_documentos = models.JSONField(default=list, blank=True, verbose_name='Lista de Documentos')
    
    # Contrato
    contrato_emitido = models.BooleanField(default=False, verbose_name='Contrato Emitido')
    data_emissao_contrato = models.DateTimeField(null=True, blank=True)
    contrato_enviado = models.BooleanField(default=False, verbose_name='Contrato Enviado')
    data_envio_contrato = models.DateTimeField(null=True, blank=True)
    contrato_assinado = models.BooleanField(default=False, verbose_name='Contrato Assinado')
    data_assinatura_contrato = models.DateTimeField(null=True, blank=True)
    
    # Responsável
    responsavel = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='gestoes_pos_venda',
        verbose_name='Responsável'
    )
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    data_conclusao = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Gestão Pós-Venda'
        verbose_name_plural = 'Gestões Pós-Venda'
        ordering = ['-data_criacao']

    def __str__(self):
        return f"Gestão Pós-Venda - {self.pre_venda.lead.nome_completo}"

    def conferir_cadastro(self, usuario, observacoes=''):
        """Marca cadastro como conferido"""
        self.cadastro_conferido = True
        self.data_conferencia_cadastro = timezone.now()
        self.observacoes_cadastro = observacoes
        self.status = StatusPosVendaCompliance.CONFERENCIA_OK
        self.responsavel = usuario
        self.save()

    def registrar_coleta_documentos(self, usuario, documentos_lista):
        """Registra coleta de documentos"""
        self.documentos_coletados = True
        self.data_coleta_documentos = timezone.now()
        self.lista_documentos = documentos_lista
        self.status = StatusPosVendaCompliance.DOCUMENTOS_OK
        self.responsavel = usuario
        self.save()

    def emitir_contrato(self, usuario):
        """Marca contrato como emitido"""
        self.contrato_emitido = True
        self.data_emissao_contrato = timezone.now()
        self.status = StatusPosVendaCompliance.EMITINDO_CONTRATO
        self.responsavel = usuario
        self.save()

    def enviar_contrato(self, usuario):
        """Marca contrato como enviado"""
        self.contrato_enviado = True
        self.data_envio_contrato = timezone.now()
        self.status = StatusPosVendaCompliance.CONTRATO_ENVIADO
        self.responsavel = usuario
        self.save()

    def confirmar_assinatura(self, usuario):
        """Confirma assinatura do contrato"""
        self.contrato_assinado = True
        self.data_assinatura_contrato = timezone.now()
        self.status = StatusPosVendaCompliance.CONTRATO_ASSINADO
        self.data_conclusao = timezone.now()
        self.responsavel = usuario
        self.save()


class HistoricoAnaliseCompliance(models.Model):
    """Histórico de ações na análise de compliance"""
    analise = models.ForeignKey(
        AnaliseCompliance,
        on_delete=models.CASCADE,
        related_name='historico'
    )
    acao = models.CharField(max_length=50, verbose_name='Ação')
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    descricao = models.TextField(verbose_name='Descrição')
    data = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Histórico de Análise'
        verbose_name_plural = 'Históricos de Análises'
        ordering = ['-data']

    def __str__(self):
        return f"{self.acao} - {self.analise.lead.nome_completo} - {self.data}"


class TipoDocumentoLevantamento(models.TextChoices):
    """Tipos de documentos de levantamento"""
    RELATORIO_COMPLETO = 'RELATORIO_COMPLETO', 'Levantamento'
    EXTRATO_BANCARIO = 'EXTRATO_BANCARIO', 'Extrato Bancário'
    CARTAO_CREDITO = 'CARTAO_CREDITO', 'Cartão de Crédito'
    EMPRESTIMO = 'EMPRESTIMO', 'Empréstimo'
    FINANCIAMENTO = 'FINANCIAMENTO', 'Financiamento'
    OUTROS = 'OUTROS', 'Outros'


class DocumentoLevantamentoCompliance(models.Model):
    """
    Documentos de levantamento enviados pelo Compliance.
    Armazena os documentos coletados durante a análise do lead.
    """
    analise = models.ForeignKey(
        AnaliseCompliance,
        on_delete=models.CASCADE,
        related_name='documentos_levantamento',
        verbose_name='Análise de Compliance'
    )
    tipo = models.CharField(
        max_length=30,
        choices=TipoDocumentoLevantamento.choices,
        default=TipoDocumentoLevantamento.RELATORIO_COMPLETO,
        verbose_name='Tipo de Documento'
    )
    arquivo = models.FileField(
        upload_to='compliance/levantamentos/%Y/%m/',
        verbose_name='Arquivo'
    )
    descricao = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Descrição'
    )
    
    # Metadados
    enviado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='documentos_levantamento_enviados',
        verbose_name='Enviado Por'
    )
    data_upload = models.DateTimeField(auto_now_add=True, verbose_name='Data de Upload')
    tamanho_arquivo = models.IntegerField(null=True, blank=True, verbose_name='Tamanho (bytes)')
    
    class Meta:
        verbose_name = 'Documento de Levantamento'
        verbose_name_plural = 'Documentos de Levantamento'
        ordering = ['-data_upload']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.analise.lead.nome_completo}"
    
    def save(self, *args, **kwargs):
        """Salva o tamanho do arquivo automaticamente"""
        if self.arquivo:
            self.tamanho_arquivo = self.arquivo.size
        super().save(*args, **kwargs)


# ============================================================================
# MODELOS PARA GESTÃO PÓS-VENDA
# ============================================================================

class StatusPagamentoEntrada(models.TextChoices):
    """Status do pagamento da entrada"""
    SEM_ENTRADA = 'SEM_ENTRADA', 'Sem Entrada'
    PENDENTE = 'PENDENTE', 'Pagamento Pendente'
    PAGO = 'PAGO', 'Pagamento Pago'


class StatusConferencia(models.TextChoices):
    """Status específicos da conferência"""
    AGUARDANDO = 'AGUARDANDO', 'Aguardando Conferência'
    EM_ANALISE = 'EM_ANALISE', 'Em Análise'
    PENDENTE_CORRECAO = 'PENDENTE_CORRECAO', 'Pendente de Correção'
    APROVADO = 'APROVADO', 'Aprovado'
    REPROVADO = 'REPROVADO', 'Reprovado'


class ConferenciaVendaCompliance(models.Model):
    """
    Conferência completa da venda pelo Compliance.
    Controla todo o fluxo pós-venda desde a conferência até o contrato assinado.
    """
    venda = models.OneToOneField('vendas.Venda', on_delete=models.CASCADE, related_name='conferencia_compliance')
    analista = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='conferencias_realizadas')
    
    # Status Geral
    status = models.CharField(
        max_length=30,
        choices=StatusPosVendaCompliance.choices,
        default=StatusPosVendaCompliance.AGUARDANDO_CONFERENCIA
    )
    status_pagamento_entrada = models.CharField(
        max_length=20,
        choices=StatusPagamentoEntrada.choices,
        default=StatusPagamentoEntrada.PENDENTE
    )
    
    # Conferência de Dados do Cliente
    dados_cliente_conferidos = models.BooleanField(default=False)
    nome_ok = models.BooleanField(default=False)
    cpf_ok = models.BooleanField(default=False)
    telefone_ok = models.BooleanField(default=False)
    email_ok = models.BooleanField(default=False)
    endereco_ok = models.BooleanField(default=False)
    rg_ok = models.BooleanField(default=False)
    profissao_ok = models.BooleanField(default=False)
    nacionalidade_ok = models.BooleanField(default=False)
    estado_civil_ok = models.BooleanField(default=False)
    
    # Conferência de Dados da Venda
    dados_venda_conferidos = models.BooleanField(default=False)
    servico_ok = models.BooleanField(default=False)
    valores_ok = models.BooleanField(default=False)
    parcelas_ok = models.BooleanField(default=False)
    forma_pagamento_ok = models.BooleanField(default=False)
    datas_ok = models.BooleanField(default=False)
    
    # Observações e Pendências
    observacoes_conferencia = models.TextField(blank=True, verbose_name='Observações da Conferência')
    pendencias = models.TextField(blank=True, verbose_name='Pendências Identificadas')
    motivo_reprovacao = models.TextField(blank=True, verbose_name='Motivo da Reprovação')
    
    # Datas de Conferência
    data_inicio_conferencia = models.DateTimeField(auto_now_add=True)
    data_aprovacao_conferencia = models.DateTimeField(null=True, blank=True)
    data_reprovacao = models.DateTimeField(null=True, blank=True)
    
    # Status de Documentos
    todos_documentos_ok = models.BooleanField(default=False)
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    # Histórico de ações (JSON)
    historico = models.JSONField(default=list, blank=True, verbose_name='Histórico de Ações')
    
    class Meta:
        verbose_name = 'Conferência de Venda'
        verbose_name_plural = 'Conferências de Vendas'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"Conferência #{self.id} - Venda #{self.venda.id} - {self.get_status_display()}"
    
    def adicionar_historico(self, acao, usuario=None, descricao=''):
        """Adiciona entrada no histórico de ações"""
        if not self.historico:
            self.historico = []
        
        entrada = {
            'acao': acao,
            'data': timezone.now().isoformat(),
            'usuario': usuario.get_full_name() if usuario else 'Sistema',
            'descricao': descricao
        }
        
        self.historico.append(entrada)
        self.save(update_fields=['historico'])
    
    def aprovar_conferencia(self, usuario):
        """Aprova a conferência e avança para coleta de documentos"""
        self.status = StatusPosVendaCompliance.COLETANDO_DOCUMENTOS
        self.data_aprovacao_conferencia = timezone.now()
        self.save()

        # Espelhar status na venda para que o painel pós-venda reflita imediatamente
        try:
            self.venda.status_compliance_pos_venda = StatusPosVendaCompliance.COLETANDO_DOCUMENTOS
            self.venda.save(update_fields=['status_compliance_pos_venda'])
        except Exception:
            # Evitar quebra caso venda não esteja acessível por algum motivo inesperado
            pass
        
        self.adicionar_historico(
            acao='CONFERENCIA_APROVADA',
            usuario=usuario,
            descricao='Conferência de cadastro aprovada. Avançando para coleta de documentos.'
        )
    
    def reprovar_conferencia(self, usuario, motivo):
        """Reprova a conferência e notifica consultor"""
        self.status = StatusPosVendaCompliance.AGUARDANDO_CONFERENCIA
        self.motivo_reprovacao = motivo
        self.data_reprovacao = timezone.now()
        self.save()

        # Atualizar status da venda para manter consistência no painel
        try:
            self.venda.status_compliance_pos_venda = StatusPosVendaCompliance.AGUARDANDO_CONFERENCIA
            self.venda.save(update_fields=['status_compliance_pos_venda'])
        except Exception:
            pass
        
        self.adicionar_historico(
            acao='CONFERENCIA_REPROVADA',
            usuario=usuario,
            descricao=f'Conferência reprovada. Motivo: {motivo}'
        )


class TipoDocumento(models.TextChoices):
    """Tipos de documentos necessários"""
    RG_FRENTE = 'RG_FRENTE', 'RG - Frente'
    RG_VERSO = 'RG_VERSO', 'RG - Verso'
    CPF = 'CPF', 'CPF'
    COMP_RESIDENCIA = 'COMP_RESIDENCIA', 'Comprovante de Residência'
    SELFIE_DOC = 'SELFIE_DOC', 'Selfie com Documento'
    CERTIDAO_CASAMENTO = 'CERTIDAO_CASAMENTO', 'Certidão de Casamento'
    CERTIDAO_DIVORCIO = 'CERTIDAO_DIVORCIO', 'Certidão de Divórcio'
    DECLARACAO_UNIAO = 'DECLARACAO_UNIAO', 'Declaração de União Estável'
    PROCURACAO = 'PROCURACAO', 'Procuração'
    COMP_RENDA = 'COMP_RENDA', 'Comprovante de Renda'
    OUTRO = 'OUTRO', 'Outro'


class StatusDocumento(models.TextChoices):
    """Status do documento"""
    PENDENTE = 'PENDENTE', 'Pendente de Upload'
    RECEBIDO = 'RECEBIDO', 'Recebido - Aguardando Validação'
    APROVADO = 'APROVADO', 'Aprovado'
    REJEITADO = 'REJEITADO', 'Rejeitado'


class DocumentoVendaCompliance(models.Model):
    """
    Documentos coletados para a venda.
    Cada documento passa por validação do Compliance.
    """
    conferencia = models.ForeignKey(
        ConferenciaVendaCompliance,
        on_delete=models.CASCADE,
        related_name='documentos'
    )
    tipo = models.CharField(max_length=30, choices=TipoDocumento.choices)
    arquivo = models.FileField(upload_to='documentos_vendas/%Y/%m/', null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=StatusDocumento.choices,
        default=StatusDocumento.PENDENTE
    )
    obrigatorio = models.BooleanField(default=True, verbose_name='Documento Obrigatório')
    
    # Validação
    observacao = models.TextField(blank=True, verbose_name='Observação')
    motivo_rejeicao = models.TextField(blank=True, verbose_name='Motivo da Rejeição')
    validado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='documentos_validados'
    )
    
    # Datas
    data_upload = models.DateTimeField(null=True, blank=True)
    data_validacao = models.DateTimeField(null=True, blank=True)
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Documento da Venda'
        verbose_name_plural = 'Documentos das Vendas'
        ordering = ['obrigatorio', 'tipo']
        unique_together = ['conferencia', 'tipo']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.get_status_display()}"
    
    def aprovar(self, usuario):
        """Aprova o documento"""
        self.status = StatusDocumento.APROVADO
        self.validado_por = usuario
        self.data_validacao = timezone.now()
        self.save()
        
        self.conferencia.adicionar_historico(
            acao='DOCUMENTO_APROVADO',
            usuario=usuario,
            descricao=f'Documento {self.get_tipo_display()} aprovado'
        )
    
    def rejeitar(self, usuario, motivo):
        """Rejeita o documento"""
        self.status = StatusDocumento.REJEITADO
        self.motivo_rejeicao = motivo
        self.validado_por = usuario
        self.data_validacao = timezone.now()
        self.save()
        
        self.conferencia.adicionar_historico(
            acao='DOCUMENTO_REJEITADO',
            usuario=usuario,
            descricao=f'Documento {self.get_tipo_display()} rejeitado. Motivo: {motivo}'
        )


class StatusContrato(models.TextChoices):
    """Status do contrato"""
    AGUARDANDO_GERACAO = 'AGUARDANDO_GERACAO', 'Aguardando Geração'
    GERADO = 'GERADO', 'Gerado'
    ENVIADO_WHATSAPP = 'ENVIADO_WHATSAPP', 'Enviado por WhatsApp'
    ENVIADO_EMAIL = 'ENVIADO_EMAIL', 'Enviado por Email'
    ENVIADO_AMBOS = 'ENVIADO_AMBOS', 'Enviado por WhatsApp e Email'
    AGUARDANDO_ASSINATURA = 'AGUARDANDO_ASSINATURA', 'Aguardando Assinatura'
    ASSINADO_GOV = 'ASSINADO_GOV', 'Assinado via Gov.br'
    ASSINADO_MANUAL = 'ASSINADO_MANUAL', 'Assinado Manualmente'
    VALIDADO = 'VALIDADO', 'Validado'
    CANCELADO = 'CANCELADO', 'Cancelado'


class TipoAssinatura(models.TextChoices):
    """Tipos de assinatura"""
    GOV_BR = 'GOV_BR', 'Gov.br (Digital)'
    MANUAL = 'MANUAL', 'Manual (Upload)'


class ContratoCompliance(models.Model):
    """
    Gestão completa de contratos pelo Compliance.
    Migrado do módulo Jurídico para centralizar no Compliance.
    """
    conferencia = models.OneToOneField(
        ConferenciaVendaCompliance,
        on_delete=models.CASCADE,
        related_name='contrato'
    )
    venda = models.OneToOneField(
        'vendas.Venda',
        on_delete=models.CASCADE,
        related_name='contrato_compliance'
    )
    numero_contrato = models.CharField(max_length=50, unique=True, blank=True)
    
    # Geração do Contrato
    template_utilizado = models.CharField(max_length=100, blank=True)
    arquivo_gerado = models.FileField(
        upload_to='contratos/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Arquivo do Contrato Gerado'
    )
    data_geracao = models.DateTimeField(null=True, blank=True)
    gerado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='contratos_gerados_compliance'
    )
    
    # Envio do Contrato
    enviado_whatsapp = models.BooleanField(default=False)
    data_envio_whatsapp = models.DateTimeField(null=True, blank=True)
    numero_whatsapp = models.CharField(max_length=20, blank=True)
    
    enviado_email = models.BooleanField(default=False)
    data_envio_email = models.DateTimeField(null=True, blank=True)
    email_destino = models.EmailField(blank=True)
    
    # Assinatura
    tipo_assinatura = models.CharField(
        max_length=20,
        choices=TipoAssinatura.choices,
        null=True,
        blank=True
    )
    arquivo_assinado = models.FileField(
        upload_to='contratos/assinados/%Y/%m/',
        null=True,
        blank=True,
        verbose_name='Arquivo do Contrato Assinado'
    )
    data_assinatura = models.DateTimeField(null=True, blank=True)
    link_assinatura_gov = models.URLField(blank=True, verbose_name='Link Assinatura Gov.br')
    
    # Validação
    validado = models.BooleanField(default=False)
    validado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='contratos_validados_compliance'
    )
    data_validacao = models.DateTimeField(null=True, blank=True)
    
    # Status e Observações
    status = models.CharField(
        max_length=30,
        choices=StatusContrato.choices,
        default=StatusContrato.AGUARDANDO_GERACAO
    )
    observacoes = models.TextField(blank=True, verbose_name='Observações')
    
    # Histórico
    historico_status = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Histórico de Status'
    )
    
    # Timestamps
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Contrato'
        verbose_name_plural = 'Contratos'
        ordering = ['-data_criacao']
    
    def __str__(self):
        return f"Contrato {self.numero_contrato or self.id} - Venda #{self.venda.id}"
    
    def gerar_numero_contrato(self):
        """Gera número único do contrato"""
        if not self.numero_contrato:
            ano = timezone.now().year
            # Buscar último contrato do ano
            ultimo = ContratoCompliance.objects.filter(
                numero_contrato__startswith=f"CONT-{ano}"
            ).order_by('-numero_contrato').first()
            
            if ultimo and ultimo.numero_contrato:
                try:
                    ultimo_num = int(ultimo.numero_contrato.split('-')[-1])
                    proximo_num = ultimo_num + 1
                except:
                    proximo_num = 1
            else:
                proximo_num = 1
            
            self.numero_contrato = f"CONT-{ano}-{proximo_num:05d}"
            self.save(update_fields=['numero_contrato'])
    
    def adicionar_historico(self, novo_status, usuario=None, observacao=''):
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
    
    def marcar_como_gerado(self, usuario):
        """Marca contrato como gerado"""
        self.status = StatusContrato.GERADO
        self.data_geracao = timezone.now()
        self.gerado_por = usuario
        self.save()
        
        self.adicionar_historico(StatusContrato.GERADO, usuario, 'Contrato gerado com sucesso')
        self.conferencia.adicionar_historico(
            acao='CONTRATO_GERADO',
            usuario=usuario,
            descricao=f'Contrato {self.numero_contrato} gerado'
        )
    
    def marcar_envio_whatsapp(self, usuario, numero):
        """Marca envio por WhatsApp"""
        self.enviado_whatsapp = True
        self.data_envio_whatsapp = timezone.now()
        self.numero_whatsapp = numero
        
        if self.enviado_email:
            self.status = StatusContrato.ENVIADO_AMBOS
        else:
            self.status = StatusContrato.ENVIADO_WHATSAPP
        
        self.save()
        
        self.adicionar_historico(
            self.status,
            usuario,
            f'Contrato enviado via WhatsApp para {numero}'
        )
    
    def marcar_envio_email(self, usuario, email):
        """Marca envio por Email"""
        self.enviado_email = True
        self.data_envio_email = timezone.now()
        self.email_destino = email
        
        if self.enviado_whatsapp:
            self.status = StatusContrato.ENVIADO_AMBOS
        else:
            self.status = StatusContrato.ENVIADO_EMAIL
        
        self.save()
        
        self.adicionar_historico(
            self.status,
            usuario,
            f'Contrato enviado via Email para {email}'
        )
    
    def marcar_como_assinado(self, usuario, tipo_assinatura):
        """Marca contrato como assinado"""
        self.tipo_assinatura = tipo_assinatura
        self.data_assinatura = timezone.now()
        
        if tipo_assinatura == TipoAssinatura.GOV_BR:
            self.status = StatusContrato.ASSINADO_GOV
        else:
            self.status = StatusContrato.ASSINADO_MANUAL
        
        self.save()
        
        self.adicionar_historico(
            self.status,
            usuario,
            f'Contrato assinado via {self.get_tipo_assinatura_display()}'
        )
    
    def validar_assinatura(self, usuario):
        """Valida a assinatura do contrato"""
        self.validado = True
        self.validado_por = usuario
        self.data_validacao = timezone.now()
        self.status = StatusContrato.VALIDADO
        self.save()
        
        # Atualizar status da conferência
        self.conferencia.status = StatusPosVendaCompliance.CONCLUIDO
        self.conferencia.save()
        
        # Atualizar venda
        self.venda.contrato_assinado = True
        self.venda.data_assinatura = timezone.now()
        self.venda.status = 'CONTRATO_ASSINADO'
        self.venda.save()
        
        self.adicionar_historico(
            StatusContrato.VALIDADO,
            usuario,
            'Assinatura validada. Processo pós-venda concluído.'
        )
        
        self.conferencia.adicionar_historico(
            acao='PROCESSO_CONCLUIDO',
            usuario=usuario,
            descricao='Contrato assinado e validado. Processo pós-venda finalizado.'
        )
