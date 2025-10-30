from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, Avg, F
from django.utils import timezone
from datetime import timedelta, datetime
from django.http import HttpResponse, JsonResponse
import csv
import json
from collections import defaultdict

# Importando modelos necessários
from marketing.models import Lead
from comissoes.models import ComissaoLead
from vendas.models import Venda, PreVenda
from financeiro.models import Parcela, PixLevantamento
from django.contrib.auth import get_user_model

User = get_user_model()


@login_required
def painel_relatorios(request):
    """
    Painel principal de relatórios com resumo geral e acesso aos relatórios específicos.
    """
    # Período padrão: últimos 30 dias
    data_inicio = timezone.now() - timedelta(days=30)
    data_fim = timezone.now()
    
    # Estatísticas gerais
    total_leads = Lead.objects.count()
    leads_periodo = Lead.objects.filter(data_cadastro__gte=data_inicio).count()
    leads_pagos = Lead.objects.filter(status='PAGO').count()
    taxa_conversao = (leads_pagos / total_leads * 100) if total_leads > 0 else 0
    
    # Comissões
    total_comissoes = ComissaoLead.objects.aggregate(total=Sum('valor'))['total'] or 0
    comissoes_pagas = ComissaoLead.objects.filter(pago=True).aggregate(total=Sum('valor'))['total'] or 0
    comissoes_pendentes = ComissaoLead.objects.filter(pago=False).aggregate(total=Sum('valor'))['total'] or 0
    
    # Top atendentes
    top_atendentes = ComissaoLead.objects.values(
        'atendente__first_name', 'atendente__last_name'
    ).annotate(
        total=Sum('valor'),
        quantidade=Count('id')
    ).order_by('-total')[:5]
    
    context = {
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'total_leads': total_leads,
        'leads_periodo': leads_periodo,
        'leads_pagos': leads_pagos,
        'taxa_conversao': round(taxa_conversao, 2),
        'total_comissoes': total_comissoes,
        'comissoes_pagas': comissoes_pagas,
        'comissoes_pendentes': comissoes_pendentes,
        'top_atendentes': top_atendentes,
    }
    
    return render(request, 'relatorios/painel_relatorios.html', context)


@login_required
def relatorio_leads(request):
    """
    Relatório detalhado de leads com filtros e análises.
    """
    # Filtros
    periodo = request.GET.get('periodo', '30')  # dias
    status_filtro = request.GET.get('status', 'todos')
    atendente_id = request.GET.get('atendente')
    
    # Data inicial baseada no período
    if periodo == 'todos':
        data_inicio = None
    else:
        try:
            dias = int(periodo)
            data_inicio = timezone.now() - timedelta(days=dias)
        except ValueError:
            data_inicio = timezone.now() - timedelta(days=30)
    
    # Query base
    leads = Lead.objects.all()
    
    if data_inicio:
        leads = leads.filter(data_cadastro__gte=data_inicio)
    
    if status_filtro != 'todos':
        leads = leads.filter(status=status_filtro)
    
    if atendente_id:
        leads = leads.filter(captador_id=atendente_id)
    
    # Ordenar por data mais recente
    leads = leads.order_by('-data_cadastro')
    
    # Estatísticas do período
    total_leads = leads.count()
    leads_pagos = leads.filter(status='PAGO').count()
    leads_pendentes = leads.filter(status='PENDENTE').count()
    leads_expirados = leads.filter(status='EXPIRADO').count()
    
    # Valor total (assumindo R$ 50,00 por lead pago)
    valor_total = leads_pagos * 50.00
    
    # Atendentes para filtro
    atendentes = User.objects.filter(
        id__in=Lead.objects.values_list('captador', flat=True).distinct()
    ).order_by('first_name')
    
    # Distribuição por status
    distribuicao_status = leads.values('status').annotate(
        quantidade=Count('id')
    ).order_by('-quantidade')
    
    context = {
        'leads': leads[:100],  # Limitar a 100 registros para performance
        'total_leads': total_leads,
        'leads_pagos': leads_pagos,
        'leads_pendentes': leads_pendentes,
        'leads_expirados': leads_expirados,
        'valor_total': valor_total,
        'atendentes': atendentes,
        'distribuicao_status': distribuicao_status,
        'periodo_selecionado': periodo,
        'status_selecionado': status_filtro,
        'atendente_selecionado': atendente_id,
    }
    
    return render(request, 'relatorios/relatorio_leads.html', context)


@login_required
def relatorio_vendas(request):
    """
    Relatório de vendas (placeholder - a ser implementado quando houver módulo de vendas).
    """
    context = {
        'em_breve': True,
        'titulo': 'Relatório de Vendas',
        'descricao': 'Análise detalhada de vendas, propostas e contratos comerciais.',
    }
    return render(request, 'relatorios/relatorio_em_breve.html', context)


@login_required
def relatorio_comissoes(request):
    """
    Relatório de comissões com análises financeiras.
    """
    # Filtros
    periodo = request.GET.get('periodo', '30')  # dias
    status_pago = request.GET.get('pago', 'todos')
    atendente_id = request.GET.get('atendente')
    
    # Data inicial
    if periodo == 'todos':
        data_inicio = None
    else:
        try:
            dias = int(periodo)
            data_inicio = timezone.now() - timedelta(days=dias)
        except ValueError:
            data_inicio = timezone.now() - timedelta(days=30)
    
    # Query base
    comissoes = ComissaoLead.objects.select_related('atendente', 'lead')
    
    if data_inicio:
        comissoes = comissoes.filter(data_criacao__gte=data_inicio)
    
    if status_pago == 'pago':
        comissoes = comissoes.filter(pago=True)
    elif status_pago == 'pendente':
        comissoes = comissoes.filter(pago=False)
    
    if atendente_id:
        comissoes = comissoes.filter(atendente_id=atendente_id)
    
    comissoes = comissoes.order_by('-data_criacao')
    
    # Estatísticas
    total_comissoes = comissoes.aggregate(total=Sum('valor'))['total'] or 0
    total_pagas = comissoes.filter(pago=True).aggregate(total=Sum('valor'))['total'] or 0
    total_pendentes = comissoes.filter(pago=False).aggregate(total=Sum('valor'))['total'] or 0
    quantidade_total = comissoes.count()
    quantidade_pagas = comissoes.filter(pago=True).count()
    quantidade_pendentes = comissoes.filter(pago=False).count()
    
    # Ranking de atendentes
    ranking = comissoes.values(
        'atendente__first_name', 'atendente__last_name', 'atendente_id'
    ).annotate(
        total_valor=Sum('valor'),
        quantidade=Count('id'),
        pagas=Count('id', filter=Q(pago=True)),
        pendentes=Count('id', filter=Q(pago=False))
    ).order_by('-total_valor')[:10]
    
    # Atendentes para filtro
    atendentes = User.objects.filter(
        id__in=ComissaoLead.objects.values_list('atendente', flat=True).distinct()
    ).order_by('first_name')
    
    context = {
        'comissoes': comissoes[:100],
        'total_comissoes': total_comissoes,
        'total_pagas': total_pagas,
        'total_pendentes': total_pendentes,
        'quantidade_total': quantidade_total,
        'quantidade_pagas': quantidade_pagas,
        'quantidade_pendentes': quantidade_pendentes,
        'ranking': ranking,
        'atendentes': atendentes,
        'periodo_selecionado': periodo,
        'pago_selecionado': status_pago,
        'atendente_selecionado': atendente_id,
    }
    
    return render(request, 'relatorios/relatorio_comissoes.html', context)


@login_required
def relatorio_financeiro(request):
    """
    Relatório financeiro (placeholder - a ser implementado quando houver módulo financeiro).
    """
    context = {
        'em_breve': True,
        'titulo': 'Relatório Financeiro',
        'descricao': 'Análise de contas a pagar, receber e demonstrativos.',
    }
    return render(request, 'relatorios/relatorio_em_breve.html', context)


@login_required
def exportar_relatorio(request, tipo):
    """
    Exporta relatórios em formato CSV.
    Tipos suportados: leads, comissoes
    """
    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="relatorio_{tipo}_{timezone.now().strftime("%Y%m%d_%H%M%S")}.csv"'
    
    # BOM para Excel reconhecer UTF-8
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    if tipo == 'leads':
        # Cabeçalho
        writer.writerow(['ID', 'Nome Completo', 'Telefone', 'CPF', 'Status', 'Valor', 'Data Cadastro', 'Atendente'])
        
        # Dados
        leads = Lead.objects.select_related('captador').order_by('-data_cadastro')
        for lead in leads:
            writer.writerow([
                lead.id,
                lead.nome_completo,
                lead.telefone,
                lead.cpf or '',
                lead.status,
                'R$ 50,00' if lead.status == 'PAGO' else 'R$ 0,00',
                lead.data_cadastro.strftime('%d/%m/%Y %H:%M'),
                lead.captador.get_full_name() if lead.captador else 'N/A'
            ])
    
    elif tipo == 'comissoes':
        # Cabeçalho
        writer.writerow(['ID', 'Atendente', 'Lead', 'Valor', 'Status Pagamento', 'Data Criação', 'Data Pagamento', 'Observações'])
        
        # Dados
        comissoes = ComissaoLead.objects.select_related('atendente', 'lead').order_by('-data_criacao')
        for comissao in comissoes:
            writer.writerow([
                comissao.id,
                comissao.atendente.get_full_name(),
                comissao.lead.nome_completo,
                f'R$ {comissao.valor:.2f}',
                'Pago' if comissao.pago else 'Pendente',
                comissao.data_criacao.strftime('%d/%m/%Y %H:%M'),
                comissao.data_pagamento.strftime('%d/%m/%Y') if comissao.data_pagamento else 'N/A',
                comissao.observacoes or ''
            ])
    
    else:
        writer.writerow(['Erro', 'Tipo de relatório não suportado'])
    
    return response


@login_required
def dashboard_graficos(request):
    """
    Dashboard com gráficos visuais impressionantes para análise de métricas.
    """
    # Período: últimos 12 meses
    hoje = timezone.now()
    data_inicio = hoje - timedelta(days=365)
    
    # ========== GRÁFICO 1: LEADS POR MÊS (Linha) ==========
    leads_por_mes = []
    labels_meses = []
    
    for i in range(11, -1, -1):
        mes_data = hoje - timedelta(days=30*i)
        inicio_mes = mes_data.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if mes_data.month == 12:
            fim_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1)
        else:
            fim_mes = inicio_mes.replace(month=inicio_mes.month + 1)
        
        count = Lead.objects.filter(
            data_cadastro__gte=inicio_mes,
            data_cadastro__lt=fim_mes
        ).count()
        
        leads_por_mes.append(count)
        labels_meses.append(inicio_mes.strftime('%b/%y'))
    
    # ========== GRÁFICO 2: LEADS POR STATUS (Pizza) ==========
    status_counts = Lead.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    status_labels = [item['status'] for item in status_counts]
    status_values = [item['count'] for item in status_counts]
    
    # ========== GRÁFICO 3: LEADS POR ORIGEM (Doughnut) ==========
    origem_counts = Lead.objects.values('origem').annotate(
        count=Count('id')
    ).order_by('-count')[:10]
    
    origem_labels = [item['origem'] for item in origem_counts]
    origem_values = [item['count'] for item in origem_counts]
    
    # ========== GRÁFICO 4: TOP 10 CAPTADORES (Barra Horizontal) ==========
    top_captadores = Lead.objects.filter(
        captador__isnull=False
    ).values(
        'captador__first_name', 'captador__last_name'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    captadores_labels = [
        f"{item['captador__first_name']} {item['captador__last_name']}" 
        for item in top_captadores
    ]
    captadores_values = [item['total'] for item in top_captadores]
    
    # ========== GRÁFICO 5: TOP 10 ATENDENTES (Barra Horizontal) ==========
    top_atendentes = Lead.objects.filter(
        atendente__isnull=False
    ).values(
        'atendente__first_name', 'atendente__last_name'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:10]
    
    atendentes_labels = [
        f"{item['atendente__first_name']} {item['atendente__last_name']}" 
        for item in top_atendentes
    ]
    atendentes_values = [item['total'] for item in top_atendentes]
    
    # ========== GRÁFICO 6: FUNIL DE CONVERSÃO (Funil) ==========
    total_leads = Lead.objects.count()
    leads_levantamento = Lead.objects.filter(fez_levantamento=True).count()
    leads_pix_pago = Lead.objects.filter(status='LEVANTAMENTO_PAGO').count()
    pre_vendas = PreVenda.objects.count()
    vendas_fechadas = Venda.objects.count()
    
    funil_labels = ['Leads Totais', 'Fez Levantamento', 'PIX Pago', 'Pré-Vendas', 'Vendas Fechadas']
    funil_values = [total_leads, leads_levantamento, leads_pix_pago, pre_vendas, vendas_fechadas]
    
    # ========== GRÁFICO 7: PIX LEVANTAMENTO - STATUS (Pizza) ==========
    pix_status = PixLevantamento.objects.values('status_pagamento').annotate(
        count=Count('id')
    ).order_by('-count')
    
    pix_labels = [item['status_pagamento'].title() for item in pix_status]
    pix_values = [item['count'] for item in pix_status]
    
    # ========== GRÁFICO 8: RECEITA POR MÊS (Barra) ==========
    receita_por_mes = []
    
    for i in range(11, -1, -1):
        mes_data = hoje - timedelta(days=30*i)
        inicio_mes = mes_data.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if mes_data.month == 12:
            fim_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1)
        else:
            fim_mes = inicio_mes.replace(month=inicio_mes.month + 1)
        
        receita = Parcela.objects.filter(
            status='paga',
            data_pagamento__gte=inicio_mes.date(),
            data_pagamento__lt=fim_mes.date()
        ).aggregate(total=Sum('valor'))['total'] or 0
        
        receita_por_mes.append(float(receita))
    
    # ========== GRÁFICO 9: PARCELAS POR STATUS (Doughnut) ==========
    parcelas_status = Parcela.objects.values('status').annotate(
        count=Count('id')
    ).order_by('-count')
    
    parcelas_labels = [item['status'].title() for item in parcelas_status]
    parcelas_values = [item['count'] for item in parcelas_status]
    
    # ========== GRÁFICO 10: TAXA DE CONVERSÃO POR ETAPA (Linha + Barra) ==========
    conversao_labels = ['Lead', 'Levantamento', 'PIX Pago', 'Pré-Venda', 'Venda']
    conversao_counts = [total_leads, leads_levantamento, leads_pix_pago, pre_vendas, vendas_fechadas]
    conversao_taxa = []
    
    for i, count in enumerate(conversao_counts):
        if i == 0:
            conversao_taxa.append(100)
        else:
            taxa = (count / conversao_counts[i-1] * 100) if conversao_counts[i-1] > 0 else 0
            conversao_taxa.append(round(taxa, 2))
    
    # ========== GRÁFICO 11: LEADS POR DIA DA SEMANA (Radar) ==========
    dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
    leads_por_dia = []
    
    for dia in range(7):
        # 0 = Monday, 6 = Sunday
        count = Lead.objects.filter(data_cadastro__week_day=dia+2).count()  # Django week_day: 1=Sunday
        leads_por_dia.append(count)
    
    # ========== GRÁFICO 12: TEMPO MÉDIO POR ETAPA (Barra) ==========
    # Calculando tempos médios (simulado para demonstração)
    tempo_labels = ['Lead → Levantamento', 'Levantamento → PIX', 'PIX → Pré-Venda', 'Pré-Venda → Venda']
    tempo_values = [2.5, 1.2, 3.8, 5.5]  # Dias (pode ser calculado com datas reais)
    
    # ========== KPIs PRINCIPAIS ==========
    kpis = {
        'total_leads': total_leads,
        'total_vendas': vendas_fechadas,
        'taxa_conversao_geral': round((vendas_fechadas / total_leads * 100) if total_leads > 0 else 0, 2),
        'receita_total': sum(receita_por_mes),
        'ticket_medio': round(sum(receita_por_mes) / vendas_fechadas if vendas_fechadas > 0 else 0, 2),
        'leads_mes_atual': leads_por_mes[-1] if leads_por_mes else 0,
    }
    
    context = {
        # Gráfico 1: Linha - Leads por Mês
        'leads_por_mes': json.dumps(leads_por_mes),
        'labels_meses': json.dumps(labels_meses),
        
        # Gráfico 2: Pizza - Status
        'status_labels': json.dumps(status_labels),
        'status_values': json.dumps(status_values),
        
        # Gráfico 3: Doughnut - Origem
        'origem_labels': json.dumps(origem_labels),
        'origem_values': json.dumps(origem_values),
        
        # Gráfico 4: Barra - Top Captadores
        'captadores_labels': json.dumps(captadores_labels),
        'captadores_values': json.dumps(captadores_values),
        
        # Gráfico 5: Barra - Top Atendentes
        'atendentes_labels': json.dumps(atendentes_labels),
        'atendentes_values': json.dumps(atendentes_values),
        
        # Gráfico 6: Funil
        'funil_labels': json.dumps(funil_labels),
        'funil_values': json.dumps(funil_values),
        
        # Gráfico 7: Pizza - PIX Status
        'pix_labels': json.dumps(pix_labels),
        'pix_values': json.dumps(pix_values),
        
        # Gráfico 8: Barra - Receita
        'receita_por_mes': json.dumps(receita_por_mes),
        
        # Gráfico 9: Doughnut - Parcelas
        'parcelas_labels': json.dumps(parcelas_labels),
        'parcelas_values': json.dumps(parcelas_values),
        
        # Gráfico 10: Conversão
        'conversao_labels': json.dumps(conversao_labels),
        'conversao_counts': json.dumps(conversao_counts),
        'conversao_taxa': json.dumps(conversao_taxa),
        
        # Gráfico 11: Radar - Dias da Semana
        'dias_semana': json.dumps(dias_semana),
        'leads_por_dia': json.dumps(leads_por_dia),
        
        # Gráfico 12: Barra - Tempo
        'tempo_labels': json.dumps(tempo_labels),
        'tempo_values': json.dumps(tempo_values),
        
        # KPIs
        'kpis': kpis,
    }
    
    return render(request, 'relatorios/dashboard_graficos.html', context)


@login_required
def painel_central(request):
    """
    Painel central de relatórios - hub principal para acessar todos os relatórios
    """
    return render(request, 'relatorios/painel_central.html')


@login_required
def grafico_evolucao_leads(request):
    """
    Página dedicada ao gráfico de evolução de leads nos últimos 12 meses.
    """
    # Período: últimos 12 meses
    hoje = timezone.now()
    data_inicio = hoje - timedelta(days=365)
    
    # ========== GRÁFICO: LEADS POR MÊS (Linha) ==========
    leads_por_mes = []
    labels_meses = []
    
    for i in range(11, -1, -1):
        mes_data = hoje - timedelta(days=30*i)
        inicio_mes = mes_data.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if mes_data.month == 12:
            fim_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1)
        else:
            fim_mes = inicio_mes.replace(month=inicio_mes.month + 1)
        
        count = Lead.objects.filter(
            data_cadastro__gte=inicio_mes,
            data_cadastro__lt=fim_mes
        ).count()
        
        leads_por_mes.append(count)
        labels_meses.append(inicio_mes.strftime('%b/%y'))
    
    # ========== CÁLCULOS DE RECEITA ==========
    receita_total = 0
    for i in range(11, -1, -1):
        mes_data = hoje - timedelta(days=30*i)
        inicio_mes = mes_data.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if mes_data.month == 12:
            fim_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1)
        else:
            fim_mes = inicio_mes.replace(month=inicio_mes.month + 1)
        
        receita = Parcela.objects.filter(
            status='paga',
            data_pagamento__gte=inicio_mes.date(),
            data_pagamento__lt=fim_mes.date()
        ).aggregate(total=Sum('valor'))['total'] or 0
        
        receita_total += float(receita)
    
    # ========== KPIs ==========
    total_leads = Lead.objects.count()
    vendas_fechadas = Venda.objects.count()
    taxa_conversao = round((vendas_fechadas / total_leads * 100) if total_leads > 0 else 0, 2)
    ticket_medio = round(receita_total / vendas_fechadas if vendas_fechadas > 0 else 0, 2)
    leads_mes_atual = leads_por_mes[-1] if leads_por_mes else 0
    
    # Crescimento percentual (comparar último mês com penúltimo)
    if len(leads_por_mes) >= 2 and leads_por_mes[-2] > 0:
        crescimento = ((leads_por_mes[-1] - leads_por_mes[-2]) / leads_por_mes[-2]) * 100
        crescimento_percentual = round(crescimento, 1)
    else:
        crescimento_percentual = 0
    
    kpis = {
        'total_leads': total_leads,
        'total_vendas': vendas_fechadas,
        'taxa_conversao_geral': taxa_conversao,
        'receita_total': receita_total,
        'ticket_medio': ticket_medio,
        'leads_mes_atual': leads_mes_atual,
        'crescimento_percentual': crescimento_percentual,
    }
    
    context = {
        'leads_por_mes': json.dumps(leads_por_mes),
        'labels_meses': json.dumps(labels_meses),
        'kpis': kpis,
    }
    
    return render(request, 'relatorios/grafico_evolucao_leads.html', context)


@login_required
def dashboard_kpis_comercial2(request):
    """
    Dashboard com KPIs e métricas do Comercial 2
    Migrado de vendas para relatórios
    """
    from vendas.models import RepescagemLead
    from django.db.models import Count, Avg, Q, F
    
    # Filtros de período
    periodo = request.GET.get('periodo', '30')  # Default 30 dias
    try:
        dias = int(periodo)
    except:
        dias = 30
    
    data_inicio = timezone.now() - timedelta(days=dias)
    
    # === ESTATÍSTICAS GERAIS ===
    total_repescagens = RepescagemLead.objects.count()
    repescagens_periodo = RepescagemLead.objects.filter(data_criacao__gte=data_inicio)
    
    stats = {
        'total_geral': total_repescagens,
        'total_periodo': repescagens_periodo.count(),
        'pendentes': RepescagemLead.objects.filter(status='PENDENTE').count(),
        'em_contato': RepescagemLead.objects.filter(status='EM_CONTATO').count(),
        'convertidos': RepescagemLead.objects.filter(status='CONVERTIDO').count(),
        'convertidos_periodo': repescagens_periodo.filter(status='CONVERTIDO').count(),
        'sem_interesse': RepescagemLead.objects.filter(status='SEM_INTERESSE').count(),
        'lead_lixo': RepescagemLead.objects.filter(status='LEAD_LIXO').count(),
    }
    
    # === TAXA DE CONVERSÃO ===
    total_finalizados = RepescagemLead.objects.filter(
        Q(status='CONVERTIDO') | Q(status='SEM_INTERESSE') | Q(status='LEAD_LIXO')
    ).count()
    
    if total_finalizados > 0:
        stats['taxa_conversao'] = round((stats['convertidos'] / total_finalizados) * 100, 1)
    else:
        stats['taxa_conversao'] = 0
    
    # Taxa de conversão no período
    total_finalizados_periodo = repescagens_periodo.filter(
        Q(status='CONVERTIDO') | Q(status='SEM_INTERESSE') | Q(status='LEAD_LIXO')
    ).count()
    
    if total_finalizados_periodo > 0:
        stats['taxa_conversao_periodo'] = round(
            (stats['convertidos_periodo'] / total_finalizados_periodo) * 100, 1
        )
    else:
        stats['taxa_conversao_periodo'] = 0
    
    # === TEMPO MÉDIO DE REPESCAGEM ===
    repescagens_concluidas = RepescagemLead.objects.filter(
        data_conclusao__isnull=False
    )
    
    if repescagens_concluidas.exists():
        tempos = []
        for r in repescagens_concluidas:
            delta = r.data_conclusao - r.data_criacao
            tempos.append(delta.total_seconds() / 86400)  # Converter para dias
        stats['tempo_medio_dias'] = round(sum(tempos) / len(tempos), 1)
    else:
        stats['tempo_medio_dias'] = 0
    
    # === DISTRIBUIÇÃO POR STATUS (para gráfico de pizza) ===
    distribuicao_status = RepescagemLead.objects.values('status').annotate(
        total=Count('id')
    ).order_by('-total')
    
    # === TOP 5 MOTIVOS DE RECUSA QUE MAIS CONVERTEM ===
    motivos_conversao = RepescagemLead.objects.filter(
        status='CONVERTIDO'
    ).values(
        'motivo_recusa__nome'
    ).annotate(
        total_conversoes=Count('id')
    ).order_by('-total_conversoes')[:5]
    
    # === TOP 5 MOTIVOS DE RECUSA GERAIS ===
    motivos_gerais = RepescagemLead.objects.values(
        'motivo_recusa__nome'
    ).annotate(
        total=Count('id')
    ).order_by('-total')[:5]
    
    # === PERFORMANCE POR CONSULTOR ===
    performance_consultores = RepescagemLead.objects.filter(
        consultor_repescagem__isnull=False
    ).values(
        'consultor_repescagem__username',
        'consultor_repescagem__first_name',
        'consultor_repescagem__last_name'
    ).annotate(
        total_atendimentos=Count('id'),
        total_convertidos=Count('id', filter=Q(status='CONVERTIDO')),
    ).order_by('-total_convertidos')
    
    # Calcular taxa de conversão por consultor
    for perf in performance_consultores:
        if perf['total_atendimentos'] > 0:
            perf['taxa_conversao'] = round(
                (perf['total_convertidos'] / perf['total_atendimentos']) * 100, 1
            )
        else:
            perf['taxa_conversao'] = 0
    
    context = {
        'stats': stats,
        'distribuicao_status': json.dumps(list(distribuicao_status)),
        'motivos_conversao': json.dumps(list(motivos_conversao)),
        'motivos_gerais': list(motivos_gerais),
        'performance_consultores': list(performance_consultores),
        'periodo_dias': dias,
    }
    
    return render(request, 'relatorios/dashboard_kpis_comercial2.html', context)

