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
    leads_pagos = leads.filter(status='LEVANTAMENTO_PAGO').count()
    leads_pendentes = leads.filter(status='LEVANTAMENTO_PENDENTE').count()
    leads_perdidos = leads.filter(status='PERDIDO').count()
    leads_em_compliance = leads.filter(status='EM_COMPLIANCE').count()
    leads_aprovado_compliance = leads.filter(status='APROVADO_COMPLIANCE').count()
    
    # Valor total baseado em comissões reais
    from comissoes.models import ComissaoLead
    comissoes_periodo = ComissaoLead.objects.filter(
        lead__in=leads.filter(status='LEVANTAMENTO_PAGO')
    )
    valor_total = comissoes_periodo.aggregate(total=Sum('valor'))['total'] or 0
    
    # Se não houver comissões registradas, calcular com valor padrão
    if valor_total == 0 and leads_pagos > 0:
        valor_comissao = ComissaoLead.obter_valor_comissao()
        valor_total = leads_pagos * float(valor_comissao)
    
     # Atendentes para filtro (usar grupos ao invés de leads existentes)
    atendentes = User.objects.filter(groups__name='atendente').distinct().order_by('first_name')
    
    # Distribuição por status
    distribuicao_status = leads.values('status').annotate(
        quantidade=Count('id')
    ).order_by('-quantidade')
    
    context = {
        'leads': leads[:100],  # Limitar a 100 registros para performance
        'total_leads': total_leads,
        'leads_pagos': leads_pagos,
        'leads_pendentes': leads_pendentes,
        'leads_perdidos': leads_perdidos,
        'leads_em_compliance': leads_em_compliance,
        'leads_aprovado_compliance': leads_aprovado_compliance,
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
    Relatório de comissões com análises financeiras para consultores, captadores e atendentes.
    """
    from django.core.paginator import Paginator
    
    # Filtros
    periodo = request.GET.get('periodo', '30')  # dias
    status_filter = request.GET.get('status', 'todos')
    usuario_id = request.GET.get('usuario')
    
    # Data inicial
    if periodo == 'todos':
        data_inicio = None
    else:
        try:
            dias = int(periodo)
            data_inicio = timezone.now() - timedelta(days=dias)
        except ValueError:
            data_inicio = timezone.now() - timedelta(days=30)
    
    # ========== COMISSÕES BASE ==========
    from financeiro.models import Comissao
    
    comissoes_base = Comissao.objects.select_related('usuario', 'venda', 'parcela')
    
    if data_inicio:
        comissoes_base = comissoes_base.filter(data_calculada__gte=data_inicio)
    
    if status_filter != 'todos':
        comissoes_base = comissoes_base.filter(status=status_filter)
    
    if usuario_id:
        comissoes_base = comissoes_base.filter(usuario_id=usuario_id)
    
    # ========== CAPTADORES ==========
    comissoes_captadores = comissoes_base.filter(tipo_comissao__icontains='CAPTADOR').order_by('-data_calculada')
    paginator_captadores = Paginator(comissoes_captadores, 20)
    page_captadores = request.GET.get('page_captadores', 1)
    captadores_paginadas = paginator_captadores.get_page(page_captadores)
    
    # ========== CONSULTORES ==========
    comissoes_consultores = comissoes_base.filter(tipo_comissao__icontains='CONSULTOR').order_by('-data_calculada')
    paginator_consultores = Paginator(comissoes_consultores, 20)
    page_consultores = request.GET.get('page_consultores', 1)
    consultores_paginadas = paginator_consultores.get_page(page_consultores)
    
    # ========== ATENDENTES ==========
    comissoes_atendentes = ComissaoLead.objects.select_related('atendente', 'lead')
    
    if data_inicio:
        comissoes_atendentes = comissoes_atendentes.filter(data_criacao__gte=data_inicio)
    
    if status_filter == 'paga':
        comissoes_atendentes = comissoes_atendentes.filter(pago=True)
    elif status_filter == 'pendente':
        comissoes_atendentes = comissoes_atendentes.filter(pago=False)
    
    if usuario_id:
        comissoes_atendentes = comissoes_atendentes.filter(atendente_id=usuario_id)
    
    comissoes_atendentes = comissoes_atendentes.order_by('-data_criacao')
    
    paginator_atendentes = Paginator(comissoes_atendentes, 20)
    page_atendentes = request.GET.get('page_atendentes', 1)
    atendentes_paginadas = paginator_atendentes.get_page(page_atendentes)
    
    # ========== ESTATÍSTICAS CAPTADORES ==========
    total_captadores = comissoes_captadores.aggregate(total=Sum('valor_comissao'))['total'] or 0
    total_captadores_pagas = comissoes_captadores.filter(status='paga').aggregate(total=Sum('valor_comissao'))['total'] or 0
    total_captadores_pendentes = comissoes_captadores.filter(status='pendente').aggregate(total=Sum('valor_comissao'))['total'] or 0
    qtd_captadores = comissoes_captadores.count()
    qtd_captadores_pagas = comissoes_captadores.filter(status='paga').count()
    qtd_captadores_pendentes = comissoes_captadores.filter(status='pendente').count()
    
    # ========== ESTATÍSTICAS CONSULTORES ==========
    total_consultores = comissoes_consultores.aggregate(total=Sum('valor_comissao'))['total'] or 0
    total_consultores_pagas = comissoes_consultores.filter(status='paga').aggregate(total=Sum('valor_comissao'))['total'] or 0
    total_consultores_pendentes = comissoes_consultores.filter(status='pendente').aggregate(total=Sum('valor_comissao'))['total'] or 0
    qtd_consultores = comissoes_consultores.count()
    qtd_consultores_pagas = comissoes_consultores.filter(status='paga').count()
    qtd_consultores_pendentes = comissoes_consultores.filter(status='pendente').count()
    
    # ========== ESTATÍSTICAS ATENDENTES ==========
    total_atendentes = comissoes_atendentes.aggregate(total=Sum('valor'))['total'] or 0
    total_atendentes_pagas = comissoes_atendentes.filter(pago=True).aggregate(total=Sum('valor'))['total'] or 0
    total_atendentes_pendentes = comissoes_atendentes.filter(pago=False).aggregate(total=Sum('valor'))['total'] or 0
    qtd_atendentes = comissoes_atendentes.count()
    qtd_atendentes_pagas = comissoes_atendentes.filter(pago=True).count()
    qtd_atendentes_pendentes = comissoes_atendentes.filter(pago=False).count()
    
    # ========== TOTAL GERAL ==========
    total_geral = float(total_captadores) + float(total_consultores) + float(total_atendentes)
    total_geral_pagas = float(total_captadores_pagas) + float(total_consultores_pagas) + float(total_atendentes_pagas)
    total_geral_pendentes = float(total_captadores_pendentes) + float(total_consultores_pendentes) + float(total_atendentes_pendentes)
    
    # ========== RANKINGS ==========
    ranking_captadores = comissoes_captadores.values(
        'usuario__first_name', 'usuario__last_name', 'usuario_id'
    ).annotate(
        total_valor=Sum('valor_comissao'),
        quantidade=Count('id'),
        pagas=Count('id', filter=Q(status='paga')),
        pendentes=Count('id', filter=Q(status='pendente'))
    ).order_by('-total_valor')[:10]
    
    ranking_consultores = comissoes_consultores.values(
        'usuario__first_name', 'usuario__last_name', 'usuario_id'
    ).annotate(
        total_valor=Sum('valor_comissao'),
        quantidade=Count('id'),
        pagas=Count('id', filter=Q(status='paga')),
        pendentes=Count('id', filter=Q(status='pendente'))
    ).order_by('-total_valor')[:10]
    
    ranking_atendentes = comissoes_atendentes.values(
        'atendente__first_name', 'atendente__last_name', 'atendente_id'
    ).annotate(
        total_valor=Sum('valor'),
        quantidade=Count('id'),
        pagas=Count('id', filter=Q(pago=True)),
        pendentes=Count('id', filter=Q(pago=False))
    ).order_by('-total_valor')[:10]
    
    # ========== USUÁRIOS PARA FILTRO (USANDO GRUPOS) ==========
    # Buscar TODOS os usuários por grupo, não apenas os que têm comissões
    usuarios_captadores = User.objects.filter(groups__name='captador').distinct()
    usuarios_consultores = User.objects.filter(groups__name='comercial1').distinct()
    usuarios_atendentes = User.objects.filter(groups__name='atendente').distinct()
    
    # Combinar todos os usuários
    usuarios = (usuarios_captadores | usuarios_consultores | usuarios_atendentes).distinct().order_by('first_name')
    
    context = {
        # Comissões paginadas
        'comissoes_captadores': captadores_paginadas,
        'comissoes_consultores': consultores_paginadas,
        'comissoes_atendentes': atendentes_paginadas,
        
        # Estatísticas Captadores
        'total_captadores': total_captadores,
        'total_captadores_pagas': total_captadores_pagas,
        'total_captadores_pendentes': total_captadores_pendentes,
        'qtd_captadores': qtd_captadores,
        'qtd_captadores_pagas': qtd_captadores_pagas,
        'qtd_captadores_pendentes': qtd_captadores_pendentes,
        
        # Estatísticas Consultores
        'total_consultores': total_consultores,
        'total_consultores_pagas': total_consultores_pagas,
        'total_consultores_pendentes': total_consultores_pendentes,
        'qtd_consultores': qtd_consultores,
        'qtd_consultores_pagas': qtd_consultores_pagas,
        'qtd_consultores_pendentes': qtd_consultores_pendentes,
        
        # Estatísticas Atendentes
        'total_atendentes': total_atendentes,
        'total_atendentes_pagas': total_atendentes_pagas,
        'total_atendentes_pendentes': total_atendentes_pendentes,
        'qtd_atendentes': qtd_atendentes,
        'qtd_atendentes_pagas': qtd_atendentes_pagas,
        'qtd_atendentes_pendentes': qtd_atendentes_pendentes,
        
        # Total Geral
        'total_geral': total_geral,
        'total_geral_pagas': total_geral_pagas,
        'total_geral_pendentes': total_geral_pendentes,
        
        # Rankings
        'ranking_captadores': ranking_captadores,
        'ranking_consultores': ranking_consultores,
        'ranking_atendentes': ranking_atendentes,
        
        # Filtros
        'usuarios': usuarios,
        'periodo_selecionado': periodo,
        'status_selecionado': status_filter,
        'usuario_selecionado': usuario_id,
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
        # Django week_day: 1=Sunday, 2=Monday, ..., 7=Saturday
        count = Lead.objects.filter(data_cadastro__week_day=dia+2 if dia < 6 else 1).count()
        leads_por_dia.append(count)
    
    # ========== GRÁFICO 12: VENDAS POR MÊS (Barra) ==========
    vendas_por_mes = []
    
    for i in range(11, -1, -1):
        mes_data = hoje - timedelta(days=30*i)
        inicio_mes = mes_data.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if mes_data.month == 12:
            fim_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1)
        else:
            fim_mes = inicio_mes.replace(month=inicio_mes.month + 1)
        
        count = Venda.objects.filter(
            data_venda__gte=inicio_mes,
            data_venda__lt=fim_mes
        ).count()
        
        vendas_por_mes.append(count)
    
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
        
        # Gráfico 12: Vendas por Mês
        'vendas_por_mes': json.dumps(vendas_por_mes),
        
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


@login_required
def ranking_geral(request):
    """
    Página de Ranking Geral: Atendentes, Consultores e Captadores
    Com estatísticas detalhadas e comparativos
    """
    from decimal import Decimal
    from financeiro.models import Comissao
    
    # Período de análise (padrão: 30 dias)
    periodo = request.GET.get('periodo', '30')
    try:
        dias = int(periodo)
    except ValueError:
        dias = 30
    
    data_inicio = timezone.now() - timedelta(days=dias)
    
    # ========== RANKING DE ATENDENTES (Por Leads Levantados) ==========
    ranking_atendentes = Lead.objects.filter(
        atendente__isnull=False,
        data_cadastro__gte=data_inicio
    ).values(
        'atendente__id',
        'atendente__first_name',
        'atendente__last_name',
        'atendente__username'
    ).annotate(
        total_leads=Count('id'),
        leads_pagos=Count('id', filter=Q(status='LEVANTAMENTO_PAGO')),
        leads_fez_levantamento=Count('id', filter=Q(fez_levantamento=True))
    ).order_by('-total_leads')[:20]
    
    # Calcular comissões dos atendentes
    for atendente in ranking_atendentes:
        atendente_id = atendente['atendente__id']
        comissoes = ComissaoLead.objects.filter(
            atendente_id=atendente_id,
            data_criacao__gte=data_inicio
        ).aggregate(
            total_comissao=Sum('valor'),
            comissoes_pagas=Sum('valor', filter=Q(pago=True)),
            comissoes_pendentes=Sum('valor', filter=Q(pago=False))
        )
        
        atendente['total_comissao'] = comissoes['total_comissao'] or Decimal('0')
        atendente['comissoes_pagas'] = comissoes['comissoes_pagas'] or Decimal('0')
        atendente['comissoes_pendentes'] = comissoes['comissoes_pendentes'] or Decimal('0')
        
        # Taxa de conversão para levantamento
        if atendente['total_leads'] > 0:
            atendente['taxa_conversao'] = round(
                (atendente['leads_fez_levantamento'] / atendente['total_leads']) * 100, 1
            )
        else:
            atendente['taxa_conversao'] = 0
    
    # ========== RANKING DE CONSULTORES (Por Vendas) ==========
    ranking_consultores = Venda.objects.filter(
        consultor__isnull=False,
        data_criacao__gte=data_inicio
    ).values(
        'consultor__id',
        'consultor__first_name',
        'consultor__last_name',
        'consultor__username'
    ).annotate(
        total_vendas=Count('id'),
        valor_total_vendas=Sum('valor_total'),
        valor_total_entradas=Sum('valor_entrada')
    ).order_by('-total_vendas')[:20]
    
    # Calcular comissões dos consultores
    for consultor in ranking_consultores:
        consultor_id = consultor['consultor__id']
        comissoes = Comissao.objects.filter(
            usuario_id=consultor_id,
            tipo_comissao__in=['CONSULTOR_ENTRADA', 'CONSULTOR_PARCELA'],
            data_calculada__gte=data_inicio
        ).aggregate(
            total_comissao=Sum('valor_comissao'),
            comissoes_pagas=Sum('valor_comissao', filter=Q(status='paga')),
            comissoes_pendentes=Sum('valor_comissao', filter=Q(status='pendente'))
        )
        
        consultor['total_comissao'] = comissoes['total_comissao'] or Decimal('0')
        consultor['comissoes_pagas'] = comissoes['comissoes_pagas'] or Decimal('0')
        consultor['comissoes_pendentes'] = comissoes['comissoes_pendentes'] or Decimal('0')
        
        # Ticket médio
        if consultor['total_vendas'] > 0:
            consultor['ticket_medio'] = round(
                consultor['valor_total_vendas'] / consultor['total_vendas'], 2
            )
        else:
            consultor['ticket_medio'] = 0
    
    # ========== RANKING DE CAPTADORES (Por Indicações) ==========
    ranking_captadores = Venda.objects.filter(
        captador__isnull=False,
        data_criacao__gte=data_inicio
    ).values(
        'captador__id',
        'captador__first_name',
        'captador__last_name',
        'captador__username'
    ).annotate(
        total_indicacoes=Count('id'),
        valor_total_indicacoes=Sum('valor_total')
    ).order_by('-total_indicacoes')[:20]
    
    # Calcular comissões dos captadores
    for captador in ranking_captadores:
        captador_id = captador['captador__id']
        comissoes = Comissao.objects.filter(
            usuario_id=captador_id,
            tipo_comissao__in=['CAPTADOR_ENTRADA', 'CAPTADOR_PARCELA'],
            data_calculada__gte=data_inicio
        ).aggregate(
            total_comissao=Sum('valor_comissao'),
            comissoes_pagas=Sum('valor_comissao', filter=Q(status='paga')),
            comissoes_pendentes=Sum('valor_comissao', filter=Q(status='pendente'))
        )
        
        captador['total_comissao'] = comissoes['total_comissao'] or Decimal('0')
        captador['comissoes_pagas'] = comissoes['comissoes_pagas'] or Decimal('0')
        captador['comissoes_pendentes'] = comissoes['comissoes_pendentes'] or Decimal('0')
        
        # Ticket médio por indicação
        if captador['total_indicacoes'] > 0:
            captador['ticket_medio'] = round(
                captador['valor_total_indicacoes'] / captador['total_indicacoes'], 2
            )
        else:
            captador['ticket_medio'] = 0
    
    # KPIs Gerais
    total_atendentes = len(ranking_atendentes)
    total_consultores = len(ranking_consultores)
    total_captadores = len(ranking_captadores)
    
    context = {
        'ranking_atendentes': ranking_atendentes,
        'ranking_consultores': ranking_consultores,
        'ranking_captadores': ranking_captadores,
        'total_atendentes': total_atendentes,
        'total_consultores': total_consultores,
        'total_captadores': total_captadores,
        'periodo': periodo,
        'periodo_dias': dias,
    }
    
    return render(request, 'relatorios/ranking_geral.html', context)


@login_required
def relatorio_consultores(request):
    """
    Relatório detalhado de performance dos consultores (Comercial 1).
    Mostra vendas, pré-vendas, conversões e comissões.
    """
    from decimal import Decimal
    
    # Filtros
    periodo = request.GET.get('periodo', '30')  # dias
    consultor_id = request.GET.get('consultor')
    status_filtro = request.GET.get('status', 'todos')
    
    # Data inicial baseada no período
    if periodo == 'todos':
        data_inicio = None
        dias = 'todos'
    else:
        try:
            dias = int(periodo)
            data_inicio = timezone.now() - timedelta(days=dias)
        except ValueError:
            dias = 30
            data_inicio = timezone.now() - timedelta(days=30)
    
    # Query base para vendas
    vendas = Venda.objects.select_related('cliente', 'servico', 'consultor', 'captador')
    
    if data_inicio:
        vendas = vendas.filter(data_venda__gte=data_inicio)
    
    if consultor_id:
        vendas = vendas.filter(consultor_id=consultor_id)
    
    if status_filtro != 'todos':
        vendas = vendas.filter(status=status_filtro)
    
    # Query base para pré-vendas
    pre_vendas = PreVenda.objects.select_related('lead', 'atendente')
    
    if data_inicio:
        pre_vendas = pre_vendas.filter(data_criacao__gte=data_inicio)
    
    if consultor_id:
        # Pré-vendas onde o atendente é o consultor selecionado
        pre_vendas = pre_vendas.filter(atendente_id=consultor_id)
    
    if status_filtro != 'todos':
        pre_vendas = pre_vendas.filter(status=status_filtro)
    
    # Estatísticas de Vendas
    total_vendas = vendas.count()
    vendas_concluidas = vendas.filter(status='CONCLUIDO').count()
    vendas_em_andamento = vendas.filter(status='EM_ANDAMENTO').count()
    vendas_canceladas = vendas.filter(status='CANCELADO').count()
    vendas_contrato_assinado = vendas.filter(status='CONTRATO_ASSINADO').count()
    
    # Valores totais
    valor_total_vendas = vendas.aggregate(total=Sum('valor_total'))['total'] or Decimal('0')
    valor_total_entradas = vendas.aggregate(total=Sum('valor_entrada'))['total'] or Decimal('0')
    valor_medio_venda = (valor_total_vendas / total_vendas) if total_vendas > 0 else Decimal('0')
    
    # Estatísticas de Pré-Vendas
    total_pre_vendas = pre_vendas.count()
    pre_vendas_pendentes = pre_vendas.filter(status='PENDENTE').count()
    pre_vendas_aceitas = pre_vendas.filter(status='ACEITO').count()
    pre_vendas_recusadas = pre_vendas.filter(status='RECUSADO').count()
    pre_vendas_convertidas = pre_vendas.filter(status='CONVERTIDO').count()
    
    # Taxa de conversão
    taxa_conversao = (pre_vendas_convertidas / total_pre_vendas * 100) if total_pre_vendas > 0 else 0
    
    # Comissões dos consultores
    from financeiro.models import Comissao
    
    comissoes = Comissao.objects.filter(
        tipo_comissao__in=['CONSULTOR_ENTRADA', 'CONSULTOR_PARCELA']
    )
    
    if data_inicio:
        comissoes = comissoes.filter(data_calculada__gte=data_inicio)
    
    if consultor_id:
        comissoes = comissoes.filter(usuario_id=consultor_id)
    
    total_comissoes = comissoes.aggregate(total=Sum('valor_comissao'))['total'] or Decimal('0')
    comissoes_pagas = comissoes.filter(status='paga').aggregate(total=Sum('valor_comissao'))['total'] or Decimal('0')
    comissoes_pendentes = comissoes.filter(status='pendente').aggregate(total=Sum('valor_comissao'))['total'] or Decimal('0')
    
    # Consultores para filtro (grupo comercial1)
    consultores = User.objects.filter(
        groups__name='comercial1'
    ).order_by('first_name')
    
    # Distribuição por status de venda
    distribuicao_status = vendas.values('status').annotate(
        quantidade=Count('id'),
        valor_total=Sum('valor_total')
    ).order_by('-quantidade')
    
    # Ranking de consultores (se nenhum consultor específico for selecionado)
    ranking_consultores = []
    if not consultor_id:
        consultores_query = User.objects.filter(groups__name='comercial1')
        
        for cons in consultores_query:
            vendas_consultor = vendas.filter(consultor=cons)
            pre_vendas_consultor = pre_vendas.filter(atendente=cons)
            comissoes_consultor = comissoes.filter(usuario=cons)
            
            total_vendas_cons = vendas_consultor.count()
            valor_vendas_cons = vendas_consultor.aggregate(total=Sum('valor_total'))['total'] or Decimal('0')
            total_comissoes_cons = comissoes_consultor.aggregate(total=Sum('valor_comissao'))['total'] or Decimal('0')
            
            if total_vendas_cons > 0 or total_comissoes_cons > 0:
                ranking_consultores.append({
                    'id': cons.id,
                    'nome': cons.get_full_name() or cons.email,
                    'total_vendas': total_vendas_cons,
                    'valor_total_vendas': valor_vendas_cons,
                    'total_pre_vendas': pre_vendas_consultor.count(),
                    'pre_vendas_convertidas': pre_vendas_consultor.filter(status='CONVERTIDO').count(),
                    'total_comissoes': total_comissoes_cons,
                    'comissoes_pagas': comissoes_consultor.filter(status='paga').aggregate(total=Sum('valor_comissao'))['total'] or Decimal('0'),
                    'ticket_medio': (valor_vendas_cons / total_vendas_cons) if total_vendas_cons > 0 else Decimal('0'),
                })
        
        # Ordenar por valor total de vendas
        ranking_consultores = sorted(ranking_consultores, key=lambda x: x['valor_total_vendas'], reverse=True)
    
    # Serviços mais vendidos
    servicos_vendidos = vendas.values(
        'servico__nome', 'servico__tipo'
    ).annotate(
        quantidade=Count('id'),
        valor_total=Sum('valor_total')
    ).order_by('-quantidade')[:5]
    
    # Calcular porcentagens para gráficos
    perc_contrato_assinado = (vendas_contrato_assinado / total_vendas * 100) if total_vendas > 0 else 0
    perc_em_andamento = (vendas_em_andamento / total_vendas * 100) if total_vendas > 0 else 0
    perc_concluidas = (vendas_concluidas / total_vendas * 100) if total_vendas > 0 else 0
    perc_canceladas = (vendas_canceladas / total_vendas * 100) if total_vendas > 0 else 0
    
    context = {
        'vendas': vendas.order_by('-data_venda')[:100],  # Limitar a 100 registros
        'total_vendas': total_vendas,
        'vendas_concluidas': vendas_concluidas,
        'vendas_em_andamento': vendas_em_andamento,
        'vendas_canceladas': vendas_canceladas,
        'vendas_contrato_assinado': vendas_contrato_assinado,
        'perc_contrato_assinado': round(perc_contrato_assinado, 1),
        'perc_em_andamento': round(perc_em_andamento, 1),
        'perc_concluidas': round(perc_concluidas, 1),
        'perc_canceladas': round(perc_canceladas, 1),
        'valor_total_vendas': valor_total_vendas,
        'valor_total_entradas': valor_total_entradas,
        'valor_medio_venda': valor_medio_venda,
        'total_pre_vendas': total_pre_vendas,
        'pre_vendas_pendentes': pre_vendas_pendentes,
        'pre_vendas_aceitas': pre_vendas_aceitas,
        'pre_vendas_recusadas': pre_vendas_recusadas,
        'pre_vendas_convertidas': pre_vendas_convertidas,
        'taxa_conversao': round(taxa_conversao, 2),
        'total_comissoes': total_comissoes,
        'comissoes_pagas': comissoes_pagas,
        'comissoes_pendentes': comissoes_pendentes,
        'consultores': consultores,
        'distribuicao_status': distribuicao_status,
        'servicos_vendidos': servicos_vendidos,
        'ranking_consultores': ranking_consultores,
        'periodo_selecionado': periodo,
        'status_selecionado': status_filtro,
        'consultor_selecionado': consultor_id,
    }
    
    return render(request, 'relatorios/relatorio_consultores.html', context)


@login_required
def relatorio_compliance(request):
    """
    Relatório completo do setor de Compliance.
    Análises, aprovações, reprovações, tempo médio, etc.
    """
    from compliance.models import AnaliseCompliance, StatusAnaliseCompliance, ClassificacaoLead
    from decimal import Decimal
    
    # Filtros
    periodo = request.GET.get('periodo', '30')
    status_filtro = request.GET.get('status', 'todos')
    classificacao_filtro = request.GET.get('classificacao', 'todas')
    analista_id = request.GET.get('analista', '')
    
    # Filtra por período
    if periodo != 'todos':
        dias = int(periodo)
        data_limite = timezone.now() - timedelta(days=dias)
        analises = AnaliseCompliance.objects.filter(data_criacao__gte=data_limite)
    else:
        analises = AnaliseCompliance.objects.all()
    
    # Filtra por status
    if status_filtro != 'todos':
        analises = analises.filter(status=status_filtro)
    
    # Filtra por classificação
    if classificacao_filtro != 'todas':
        analises = analises.filter(classificacao=classificacao_filtro)
    
    # Filtra por analista
    if analista_id:
        analises = analises.filter(analista_responsavel_id=analista_id)
    
    # Seleciona campos relacionados para otimização
    analises = analises.select_related('lead', 'analista_responsavel', 'consultor_atribuido')
    
    # Estatísticas gerais
    total_analises = analises.count()
    analises_aguardando = analises.filter(status='AGUARDANDO').count()
    analises_em_andamento = analises.filter(status='EM_ANALISE').count()
    analises_aprovadas = analises.filter(status='APROVADO').count()
    analises_atribuidas = analises.filter(status='ATRIBUIDO').count()
    analises_reprovadas = analises.filter(status='REPROVADO').count()
    analises_em_pre_venda = analises.filter(status='EM_PRE_VENDA').count()
    
    # Percentuais
    perc_aprovadas = (analises_aprovadas / total_analises * 100) if total_analises > 0 else 0
    perc_reprovadas = (analises_reprovadas / total_analises * 100) if total_analises > 0 else 0
    perc_em_andamento = (analises_em_andamento / total_analises * 100) if total_analises > 0 else 0
    perc_aguardando = (analises_aguardando / total_analises * 100) if total_analises > 0 else 0
    perc_atribuidas = (analises_atribuidas / total_analises * 100) if total_analises > 0 else 0
    perc_em_pre_venda = (analises_em_pre_venda / total_analises * 100) if total_analises > 0 else 0
    
    # Distribuição por classificação
    distribuicao_classificacao = analises.values('classificacao').annotate(
        quantidade=Count('id')
    ).order_by('classificacao')
    
    # Distribuição por status
    distribuicao_status = analises.values('status').annotate(
        quantidade=Count('id')
    ).order_by('status')
    
    # Tempo médio de análise (em dias)
    analises_finalizadas = analises.filter(
        Q(status='APROVADO') | Q(status='REPROVADO') | Q(status='ATRIBUIDO')
    ).filter(data_analise__isnull=False)
    
    tempo_medio_analise = 0
    if analises_finalizadas.exists():
        from django.db.models import Avg, ExpressionWrapper, DurationField
        tempo_medio = analises_finalizadas.aggregate(
            media=Avg(ExpressionWrapper(
                F('data_analise') - F('data_criacao'),
                output_field=DurationField()
            ))
        )['media']
        if tempo_medio:
            tempo_medio_analise = tempo_medio.total_seconds() / 86400  # Converte para dias
    
    # Ranking de analistas (buscar do grupo compliance)
    ranking_analistas = []
    analistas = User.objects.filter(groups__name='compliance').distinct()
    
    for analista in analistas:
        analises_analista = analises.filter(analista_responsavel=analista)
        total = analises_analista.count()
        aprovadas = analises_analista.filter(status__in=['APROVADO', 'ATRIBUIDO', 'EM_PRE_VENDA']).count()
        reprovadas = analises_analista.filter(status='REPROVADO').count()
        taxa_aprovacao = (aprovadas / total * 100) if total > 0 else 0
        
        ranking_analistas.append({
            'nome': analista.get_full_name() or analista.email,
            'total_analises': total,
            'aprovadas': aprovadas,
            'reprovadas': reprovadas,
            'taxa_aprovacao': round(taxa_aprovacao, 1),
        })
    
    ranking_analistas = sorted(ranking_analistas, key=lambda x: x['total_analises'], reverse=True)[:10]
    
    # Motivos de reprovação mais comuns
    motivos_reprovacao = analises.filter(
        status='REPROVADO',
        motivo_reprovacao__isnull=False
    ).values('motivo_reprovacao').annotate(
        quantidade=Count('id')
    ).order_by('-quantidade')[:5]
    
    # Leads por consultor atribuído
    leads_por_consultor = analises.filter(
        consultor_atribuido__isnull=False
    ).values(
        'consultor_atribuido__first_name',
        'consultor_atribuido__last_name'
    ).annotate(
        quantidade=Count('id')
    ).order_by('-quantidade')[:10]
    
    # Analistas disponíveis para filtro (usar grupo compliance)
    analistas_filtro = User.objects.filter(
        groups__name='compliance'
    ).distinct().order_by('first_name')
    
    context = {
        'analises': analises.order_by('-data_criacao')[:100],
        'total_analises': total_analises,
        'analises_aguardando': analises_aguardando,
        'analises_em_andamento': analises_em_andamento,
        'analises_aprovadas': analises_aprovadas,
        'analises_atribuidas': analises_atribuidas,
        'analises_reprovadas': analises_reprovadas,
        'analises_em_pre_venda': analises_em_pre_venda,
        'perc_aprovadas': round(perc_aprovadas, 1),
        'perc_reprovadas': round(perc_reprovadas, 1),
        'perc_em_andamento': round(perc_em_andamento, 1),
        'perc_aguardando': round(perc_aguardando, 1),
        'perc_atribuidas': round(perc_atribuidas, 1),
        'perc_em_pre_venda': round(perc_em_pre_venda, 1),
        'distribuicao_classificacao': distribuicao_classificacao,
        'distribuicao_status': distribuicao_status,
        'tempo_medio_analise': round(tempo_medio_analise, 1),
        'ranking_analistas': ranking_analistas,
        'motivos_reprovacao': motivos_reprovacao,
        'leads_por_consultor': leads_por_consultor,
        'analistas_filtro': analistas_filtro,
        'periodo_selecionado': periodo,
        'status_selecionado': status_filtro,
        'classificacao_selecionada': classificacao_filtro,
        'analista_selecionado': analista_id,
    }
    
    return render(request, 'relatorios/relatorio_compliance.html', context)

