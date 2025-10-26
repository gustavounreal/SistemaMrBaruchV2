from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import timedelta
from .models import ComissaoLead
from core.models import ConfiguracaoSistema

@login_required
def painel_comissoes(request):
    """Painel principal de comissões com visão geral"""
    
    # Estatísticas gerais
    total_comissoes = ComissaoLead.objects.aggregate(
        total=Sum('valor'),
        quantidade=Count('id'),
        pagas=Count('id', filter=Q(pago=True)),
        pendentes=Count('id', filter=Q(pago=False))
    )
    
    # Comissões do mês atual
    hoje = timezone.now()
    primeiro_dia_mes = hoje.replace(day=1)
    comissoes_mes = ComissaoLead.objects.filter(
        data_criacao__gte=primeiro_dia_mes
    ).aggregate(
        total=Sum('valor'),
        quantidade=Count('id')
    )
    
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
    status_pagamento = request.GET.get('status')  # 'pago', 'pendente', 'todos'
    
    # Query base
    hoje = timezone.now()
    data_inicio = hoje - timedelta(days=int(periodo))
    comissoes = ComissaoLead.objects.filter(data_criacao__gte=data_inicio).select_related('lead', 'atendente')
    
    # Aplicar filtros
    if atendente_id:
        comissoes = comissoes.filter(atendente_id=atendente_id)
    
    if status_pagamento == 'pago':
        comissoes = comissoes.filter(pago=True)
    elif status_pagamento == 'pendente':
        comissoes = comissoes.filter(pago=False)
    
    # Estatísticas do período filtrado
    stats = comissoes.aggregate(
        total_valor=Sum('valor'),
        total_quantidade=Count('id'),
        total_pagas=Sum('valor', filter=Q(pago=True)),
        total_pendentes=Sum('valor', filter=Q(pago=False)),
        qtd_pagas=Count('id', filter=Q(pago=True)),
        qtd_pendentes=Count('id', filter=Q(pago=False))
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

