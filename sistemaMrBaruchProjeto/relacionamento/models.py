from django.db import models
from django.contrib.auth import get_user_model
from vendas.models import Venda
from clientes.models import Cliente

User = get_user_model()


class CanalComunicacao(models.Model):
    """Canais de comunicação disponíveis"""
    TIPO_CHOICES = [
        ('whatsapp', 'WhatsApp'),
        ('email', 'E-mail'),
        ('telefone', 'Telefone'),
        ('sms', 'SMS'),
        ('presencial', 'Presencial'),
    ]
    
    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    ativo = models.BooleanField(default=True)
    descricao = models.TextField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Canal de Comunicação'
        verbose_name_plural = 'Canais de Comunicação'
    
    def __str__(self):
        return f"{self.nome} ({self.get_tipo_display()})"


class InteracaoCliente(models.Model):
    """Registro de todas as interações com clientes"""
    TIPO_CHOICES = [
        ('boas_vindas', 'Boas-vindas'),
        ('followup', 'Follow-up'),
        ('cobranca', 'Cobrança'),
        ('suporte', 'Suporte'),
        ('pesquisa', 'Pesquisa de Satisfação'),
        ('aniversario', 'Aniversário'),
        ('indicacao', 'Solicitação de Indicação'),
        ('atualizacao', 'Atualização de Status'),
        ('outros', 'Outros'),
    ]
    
    STATUS_CHOICES = [
        ('agendada', 'Agendada'),
        ('realizada', 'Realizada'),
        ('cancelada', 'Cancelada'),
        ('sem_resposta', 'Sem Resposta'),
    ]
    
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='interacoes')
    venda = models.ForeignKey(Venda, on_delete=models.SET_NULL, null=True, blank=True, related_name='interacoes')
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    canal = models.ForeignKey(CanalComunicacao, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='agendada')
    
    data_agendada = models.DateTimeField(null=True, blank=True)
    data_realizada = models.DateTimeField(null=True, blank=True)
    
    assunto = models.CharField(max_length=200)
    mensagem = models.TextField()
    resposta_cliente = models.TextField(blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    
    responsavel = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='interacoes_responsavel')
    criado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='interacoes_criadas')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Interação com Cliente'
        verbose_name_plural = 'Interações com Clientes'
        ordering = ['-data_agendada', '-criado_em']
    
    def __str__(self):
        return f"{self.cliente.lead.nome_completo} - {self.get_tipo_display()} ({self.data_agendada or self.criado_em})"


class PesquisaSatisfacao(models.Model):
    """Pesquisas de satisfação enviadas aos clientes"""
    NOTA_CHOICES = [(i, str(i)) for i in range(1, 11)]
    
    interacao = models.OneToOneField(InteracaoCliente, on_delete=models.CASCADE, related_name='pesquisa')
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pesquisas')
    venda = models.ForeignKey(Venda, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Perguntas
    nota_atendimento = models.IntegerField(choices=NOTA_CHOICES, null=True, blank=True, help_text="1-10")
    nota_produto = models.IntegerField(choices=NOTA_CHOICES, null=True, blank=True, help_text="1-10")
    nota_geral = models.IntegerField(choices=NOTA_CHOICES, null=True, blank=True, help_text="1-10")
    
    recomendaria = models.BooleanField(null=True, blank=True, help_text="Recomendaria a empresa?")
    comentarios = models.TextField(blank=True, null=True)
    
    enviada_em = models.DateTimeField(auto_now_add=True)
    respondida_em = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = 'Pesquisa de Satisfação'
        verbose_name_plural = 'Pesquisas de Satisfação'
        ordering = ['-enviada_em']
    
    def __str__(self):
        return f"Pesquisa - {self.cliente.lead.nome_completo} - {self.enviada_em.strftime('%d/%m/%Y')}"
    
    @property
    def respondida(self):
        return self.respondida_em is not None
    
    @property
    def media_notas(self):
        notas = [n for n in [self.nota_atendimento, self.nota_produto, self.nota_geral] if n]
        return sum(notas) / len(notas) if notas else None


class Indicacao(models.Model):
    """Indicações feitas por clientes"""
    STATUS_CHOICES = [
        ('pendente', 'Pendente'),
        ('contatado', 'Contatado'),
        ('agendado', 'Agendado'),
        ('convertido', 'Convertido'),
        ('perdido', 'Perdido'),
    ]
    
    cliente_indicador = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='indicacoes_feitas')
    venda_indicador = models.ForeignKey(Venda, on_delete=models.SET_NULL, null=True, blank=True)
    
    nome_indicado = models.CharField(max_length=200)
    telefone_indicado = models.CharField(max_length=20)
    email_indicado = models.CharField(max_length=200, blank=True, null=True)
    observacoes = models.TextField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pendente')
    venda_gerada = models.ForeignKey(Venda, on_delete=models.SET_NULL, null=True, blank=True, related_name='indicacao_origem')
    
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Indicação'
        verbose_name_plural = 'Indicações'
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"{self.nome_indicado} (indicado por {self.cliente_indicador.lead.nome_completo})"


class ProgramaFidelidade(models.Model):
    """Pontos e benefícios do programa de fidelidade"""
    cliente = models.OneToOneField(Cliente, on_delete=models.CASCADE, related_name='fidelidade')
    
    pontos_totais = models.IntegerField(default=0)
    pontos_disponiveis = models.IntegerField(default=0)
    pontos_utilizados = models.IntegerField(default=0)
    
    nivel = models.CharField(max_length=50, default='Bronze', help_text="Bronze, Prata, Ouro, Diamante")
    
    total_indicacoes = models.IntegerField(default=0)
    total_vendas_geradas = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    ativo = models.BooleanField(default=True)
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Programa de Fidelidade'
        verbose_name_plural = 'Programas de Fidelidade'
    
    def __str__(self):
        return f"{self.cliente.lead.nome_completo} - {self.nivel} ({self.pontos_disponiveis} pontos)"
    
    def adicionar_pontos(self, pontos, descricao=""):
        """Adiciona pontos ao cliente"""
        self.pontos_totais += pontos
        self.pontos_disponiveis += pontos
        self.save()
        
        # Registra movimentação
        MovimentacaoPontos.objects.create(
            fidelidade=self,
            tipo='credito',
            pontos=pontos,
            descricao=descricao
        )
    
    def utilizar_pontos(self, pontos, descricao=""):
        """Utiliza pontos do cliente"""
        if pontos > self.pontos_disponiveis:
            raise ValueError("Pontos insuficientes")
        
        self.pontos_utilizados += pontos
        self.pontos_disponiveis -= pontos
        self.save()
        
        # Registra movimentação
        MovimentacaoPontos.objects.create(
            fidelidade=self,
            tipo='debito',
            pontos=pontos,
            descricao=descricao
        )


class MovimentacaoPontos(models.Model):
    """Histórico de movimentação de pontos"""
    TIPO_CHOICES = [
        ('credito', 'Crédito'),
        ('debito', 'Débito'),
    ]
    
    fidelidade = models.ForeignKey(ProgramaFidelidade, on_delete=models.CASCADE, related_name='movimentacoes')
    tipo = models.CharField(max_length=10, choices=TIPO_CHOICES)
    pontos = models.IntegerField()
    descricao = models.CharField(max_length=200)
    
    criado_em = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Movimentação de Pontos'
        verbose_name_plural = 'Movimentações de Pontos'
        ordering = ['-criado_em']
    
    def __str__(self):
        return f"{self.get_tipo_display()} - {self.pontos} pontos - {self.fidelidade.cliente.lead.nome_completo}"
