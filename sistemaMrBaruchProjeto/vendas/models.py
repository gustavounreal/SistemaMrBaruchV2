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
    
    # Dados de qualificação (Etapa 1)
    prazo_risco = models.CharField(max_length=50, choices=PRAZO_RISCO_CHOICES)
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
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    valor_entrada = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    quantidade_parcelas = models.PositiveIntegerField(null=True, blank=True)
    valor_parcela = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    frequencia_pagamento = models.CharField(max_length=20, blank=True, default='MENSAL')
    
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