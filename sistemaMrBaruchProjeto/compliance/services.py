# compliance/services.py
"""
Services para lógica de negócio do módulo Compliance.
Centraliza regras complexas, cálculos e operações que não pertencem às views ou models.
"""
from django.db.models import Count, Q
from django.utils import timezone
from django.contrib.auth import get_user_model
from .models import (
    AnaliseCompliance, StatusAnaliseCompliance, 
    HistoricoAnaliseCompliance, GestaoDocumentosPosVenda,
    StatusPosVendaCompliance
)

User = get_user_model()


class ComplianceStatsService:
    """Service para cálculo de estatísticas do Compliance"""
    
    @staticmethod
    def get_dashboard_stats():
        """
        Retorna estatísticas consolidadas para o dashboard do Compliance.
        
        Returns:
            dict: Dicionário com contadores de análises por status
        """
        return {
            'total_aguardando': AnaliseCompliance.objects.filter(
                status=StatusAnaliseCompliance.AGUARDANDO
            ).count(),
            'total_em_analise': AnaliseCompliance.objects.filter(
                status=StatusAnaliseCompliance.EM_ANALISE
            ).count(),
            'total_atribuidos_hoje': AnaliseCompliance.objects.filter(
                status=StatusAnaliseCompliance.ATRIBUIDO,
                data_atribuicao__date=timezone.now().date()
            ).count(),
            'total_aprovados_aguardando': AnaliseCompliance.objects.filter(
                status=StatusAnaliseCompliance.APROVADO
            ).count(),
            'total_pos_venda_pendente': GestaoDocumentosPosVenda.objects.exclude(
                status=StatusPosVendaCompliance.CONCLUIDO
            ).count(),
        }
    
    @staticmethod
    def get_leads_aguardando(limit=10):
        """
        Retorna leads aguardando análise.
        
        Args:
            limit (int): Número máximo de registros
            
        Returns:
            QuerySet: Leads aguardando análise
        """
        return AnaliseCompliance.objects.filter(
            status=StatusAnaliseCompliance.AGUARDANDO
        ).select_related('lead', 'analista_responsavel').order_by('-data_criacao')[:limit]
    
    @staticmethod
    def get_leads_em_analise_by_user(user, limit=10):
        """
        Retorna leads em análise pelo usuário específico.
        
        Args:
            user: Usuário analista
            limit (int): Número máximo de registros
            
        Returns:
            QuerySet: Leads em análise pelo usuário
        """
        return AnaliseCompliance.objects.filter(
            status=StatusAnaliseCompliance.EM_ANALISE,
            analista_responsavel=user
        ).select_related('lead').order_by('-data_analise')[:limit]
    
    @staticmethod
    def get_historico_recente(limit=15):
        """
        Retorna histórico recente de ações no Compliance.
        
        Args:
            limit (int): Número máximo de registros
            
        Returns:
            QuerySet: Histórico ordenado por data decrescente
        """
        return HistoricoAnaliseCompliance.objects.select_related(
            'analise__lead', 'usuario'
        ).order_by('-data')[:limit]


class ComplianceAnaliseService:
    """Service para operações de análise de leads"""
    
    @staticmethod
    def filtrar_analises(status=None, classificacao=None, busca=None):
        """
        Filtra análises de compliance com múltiplos critérios.
        
        Args:
            status (str, optional): Status da análise
            classificacao (str, optional): Classificação do lead
            busca (str, optional): Termo de busca (nome/CPF do lead)
            
        Returns:
            QuerySet: Análises filtradas
        """
        analises = AnaliseCompliance.objects.select_related(
            'lead', 'consultor_atribuido', 'analista_responsavel'
        ).all()
        
        if status:
            analises = analises.filter(status=status)
        
        if classificacao:
            analises = analises.filter(classificacao=classificacao)
        
        if busca:
            analises = analises.filter(
                Q(lead__nome_completo__icontains=busca) |
                Q(lead__cpf_cnpj__icontains=busca)
            )
        
        return analises.order_by('-data_criacao')
    
    @staticmethod
    def iniciar_analise(analise, usuario, valor_divida=None, observacoes=''):
        """
        Inicia o processo de análise de um lead.
        
        Args:
            analise (AnaliseCompliance): Análise a ser iniciada
            usuario: Usuário que está iniciando a análise
            valor_divida (float, optional): Valor total da dívida
            observacoes (str): Observações da análise
            
        Returns:
            AnaliseCompliance: Análise atualizada
        """
        analise.status = StatusAnaliseCompliance.EM_ANALISE
        analise.analista_responsavel = usuario
        analise.data_analise = timezone.now()
        
        if valor_divida:
            analise.valor_divida_total = float(valor_divida)
            analise.classificar_automaticamente()
        
        analise.observacoes_analise = observacoes
        analise.save()
        
        # Registrar no histórico
        HistoricoAnaliseCompliance.objects.create(
            analise=analise,
            acao='INICIO_ANALISE',
            usuario=usuario,
            descricao=f'Análise iniciada. {observacoes}'
        )
        
        return analise
    
    @staticmethod
    def aprovar_analise(analise, usuario, observacoes=''):
        """
        Aprova uma análise de lead.
        
        Args:
            analise (AnaliseCompliance): Análise a ser aprovada
            usuario: Usuário que está aprovando
            observacoes (str): Observações da aprovação
            
        Returns:
            AnaliseCompliance: Análise atualizada
        """
        analise.status = StatusAnaliseCompliance.APROVADO
        analise.data_aprovacao = timezone.now()
        analise.observacoes_analise = observacoes
        analise.save()
        
        # Atualizar status do lead
        analise.lead.passou_compliance = True
        analise.lead.save(update_fields=['passou_compliance'])
        
        # Registrar no histórico
        HistoricoAnaliseCompliance.objects.create(
            analise=analise,
            acao='APROVACAO',
            usuario=usuario,
            descricao=f'Lead aprovado. {observacoes}'
        )
        
        return analise
    
    @staticmethod
    def reprovar_analise(analise, usuario, motivo, observacoes=''):
        """
        Reprova uma análise de lead.
        
        Args:
            analise (AnaliseCompliance): Análise a ser reprovada
            usuario: Usuário que está reprovando
            motivo (str): Motivo da reprovação
            observacoes (str): Observações adicionais
            
        Returns:
            AnaliseCompliance: Análise atualizada
        """
        analise.status = StatusAnaliseCompliance.REPROVADO
        analise.data_reprovacao = timezone.now()
        analise.motivo_reprovacao = motivo
        analise.observacoes_analise = observacoes
        analise.save()
        
        # Atualizar status do lead
        analise.lead.status = 'REPROVADO_COMPLIANCE'
        analise.lead.save(update_fields=['status'])
        
        # Registrar no histórico
        HistoricoAnaliseCompliance.objects.create(
            analise=analise,
            acao='REPROVACAO',
            usuario=usuario,
            descricao=f'Lead reprovado. Motivo: {motivo}. {observacoes}'
        )
        
        return analise


class ConsultorAtribuicaoService:
    """Service para atribuição de leads a consultores"""
    
    @staticmethod
    def listar_consultores_disponiveis():
        """
        Lista consultores disponíveis ordenados por carga de trabalho.
        
        Returns:
            QuerySet: Consultores com contagem de leads ativos
            
        Leads ativos = Leads atribuídos que ainda NÃO viraram venda
        """
        from vendas.models import Venda
        
        # Buscar IDs de leads que já têm venda cadastrada
        leads_com_venda = Venda.objects.filter(
            consultor__isnull=False
        ).values_list('cliente__lead_id', flat=True)
        
        return User.objects.filter(
            groups__name='comercial1',  # Atualizado de 'consultor' para 'comercial1'
            is_active=True
        ).annotate(
            leads_ativos=Count('leads_compliance_atribuidos', filter=Q(
                leads_compliance_atribuidos__status=StatusAnaliseCompliance.ATRIBUIDO
            ) & ~Q(
                leads_compliance_atribuidos__lead_id__in=leads_com_venda
            ))
        ).order_by('leads_ativos')
    
    @staticmethod
    def atribuir_lead_consultor(analise, consultor, usuario):
        """
        Atribui um lead aprovado para um consultor.
        
        Args:
            analise (AnaliseCompliance): Análise aprovada
            consultor: Consultor que receberá o lead
            usuario: Usuário que está fazendo a atribuição
            
        Returns:
            AnaliseCompliance: Análise atualizada
        """
        # Usar o método do model que já existe
        analise.atribuir_consultor(consultor, usuario)
        
        # Registrar no histórico (já é criado dentro do método atribuir_consultor, então comentamos aqui)
        # HistoricoAnaliseCompliance.objects.create(
        #     analise=analise,
        #     acao='ATRIBUICAO',
        #     usuario=usuario,
        #     descricao=f'Lead atribuído ao consultor {consultor.username}'
        # )
        
        return analise
