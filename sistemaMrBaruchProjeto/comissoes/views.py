from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import ComissaoLead
from core.models import ConfiguracaoSistema
from financeiro.models import Comissao

@login_required
def painel_comissoes(request):
    """Painel principal de comissões com visão geral"""
    
    # Estatísticas de comissões de leads (atendentes)
    comissoes_atendentes = ComissaoLead.objects.aggregate(
        total=Sum('valor'),
        quantidade=Count('id'),
        pagas=Count('id', filter=Q(status='PAGO')),
        pendentes=Count('id', filter=Q(status__in=['DISPONIVEL', 'AUTORIZADO']))
    )
    
    # Estatísticas de comissões de consultores e captadores (do financeiro)
    comissoes_consultores = Comissao.objects.filter(tipo_comissao='consultor').aggregate(
        quantidade=Count('id')
    )
    
    comissoes_captadores = Comissao.objects.filter(tipo_comissao='captador').aggregate(
        quantidade=Count('id')
    )
    
    # Total geral combinado
    total_valor_atendentes = comissoes_atendentes.get('total') or 0
    total_valor_outros = Comissao.objects.aggregate(total=Sum('valor_comissao')).get('total') or 0
    
    total_comissoes = {
        'total': total_valor_atendentes + total_valor_outros,
        'quantidade': (comissoes_atendentes.get('quantidade') or 0) + 
                      (comissoes_consultores.get('quantidade') or 0) + 
                      (comissoes_captadores.get('quantidade') or 0),
        'pagas': comissoes_atendentes.get('pagas') or 0,
        'pendentes': comissoes_atendentes.get('pendentes') or 0,
        'atendentes': comissoes_atendentes.get('quantidade') or 0,
        'consultores': comissoes_consultores.get('quantidade') or 0,
        'captadores': comissoes_captadores.get('quantidade') or 0,
    }
    
    # Comissões do mês atual
    hoje = timezone.now()
    primeiro_dia_mes = hoje.replace(day=1)
    comissoes_mes_atendentes = ComissaoLead.objects.filter(
        data_criacao__gte=primeiro_dia_mes
    ).aggregate(
        total=Sum('valor'),
        quantidade=Count('id')
    )
    
    comissoes_mes_outros = Comissao.objects.filter(
        data_calculada__gte=primeiro_dia_mes
    ).aggregate(
        total=Sum('valor_comissao'),
        quantidade=Count('id')
    )
    
    comissoes_mes = {
        'total': (comissoes_mes_atendentes.get('total') or 0) + (comissoes_mes_outros.get('total') or 0),
        'quantidade': (comissoes_mes_atendentes.get('quantidade') or 0) + (comissoes_mes_outros.get('quantidade') or 0)
    }
    
    # Obter valor configurado de comissão
    try:
        config_valor = ConfiguracaoSistema.objects.get(chave='COMISSAO_ATENDENTE_VALOR_FIXO')
        valor_comissao_atual = config_valor.valor
    except ConfiguracaoSistema.DoesNotExist:
        valor_comissao_atual = '0.50'
    
    context = {
        'total_comissoes': total_comissoes,
        'comissoes_mes': comissoes_mes,
        'valor_comissao_atual': valor_comissao_atual,
    }
    
    return render(request, 'comissoes/painel_comissoes.html', context)


@login_required
def painel_comissoes_leads(request):
    """Painel específico para comissões de leads"""
    
    # Filtros
    periodo = request.GET.get('periodo', '30')  # últimos 30 dias por padrão
    atendente_id = request.GET.get('atendente')
    status_pagamento = request.GET.get('status')  # 'PAGO', 'DISPONIVEL', 'AUTORIZADO', 'todos'
    
    # Query base
    hoje = timezone.now()
    data_inicio = hoje - timedelta(days=int(periodo))
    comissoes = ComissaoLead.objects.filter(data_criacao__gte=data_inicio).select_related('lead', 'atendente')
    
    # Aplicar filtros
    if atendente_id:
        comissoes = comissoes.filter(atendente_id=atendente_id)
    
    if status_pagamento == 'PAGO':
        comissoes = comissoes.filter(status='PAGO')
    elif status_pagamento == 'DISPONIVEL':
        comissoes = comissoes.filter(status='DISPONIVEL')
    elif status_pagamento == 'AUTORIZADO':
        comissoes = comissoes.filter(status='AUTORIZADO')
    elif status_pagamento == 'pendente':
        comissoes = comissoes.filter(status__in=['DISPONIVEL', 'AUTORIZADO'])
    
    # Estatísticas do período filtrado
    stats = comissoes.aggregate(
        total_valor=Sum('valor'),
        total_quantidade=Count('id'),
        total_pagas=Sum('valor', filter=Q(status='PAGO')),
        total_pendentes=Sum('valor', filter=Q(status__in=['DISPONIVEL', 'AUTORIZADO'])),
        qtd_pagas=Count('id', filter=Q(status='PAGO')),
        qtd_pendentes=Count('id', filter=Q(status__in=['DISPONIVEL', 'AUTORIZADO']))
    )
    
    # Ranking de atendentes
    ranking_atendentes = ComissaoLead.objects.filter(
        data_criacao__gte=data_inicio
    ).values(
        'atendente__first_name', 
        'atendente__last_name', 
        'atendente__username'
    ).annotate(
        total_comissoes=Sum('valor'),
        quantidade=Count('id')
    ).order_by('-total_comissoes')[:10]
    
    # Obter configuração atual
    try:
        config_valor = ConfiguracaoSistema.objects.get(chave='COMISSAO_ATENDENTE_VALOR_FIXO')
        valor_comissao_config = config_valor.valor
        config_ativa = ConfiguracaoSistema.objects.get(chave='COMISSAO_ATIVA').valor == 'true'
    except ConfiguracaoSistema.DoesNotExist:
        valor_comissao_config = '0.50'
        config_ativa = True
    
    context = {
        'comissoes': comissoes.order_by('-data_criacao')[:100],  # últimas 100
        'stats': stats,
        'ranking_atendentes': ranking_atendentes,
        'valor_comissao_config': valor_comissao_config,
        'config_ativa': config_ativa,
        'periodo_selecionado': periodo,
        'status_selecionado': status_pagamento,
    }
    
    return render(request, 'comissoes/painel_leads.html', context)


@login_required
def relatorio_comissoes(request):
    """Relatório detalhado de comissões (para futuro)"""
    return render(request, 'comissoes/relatorio.html')

