"""
Views para Gestão de Comissões
Painel completo com filtros, autorização e pagamento
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Sum, Count
from django.utils import timezone
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from datetime import datetime, timedelta
from decimal import Decimal

from .models import ComissaoLead, ComissaoConsultor, ComissaoCaptador
from financeiro.models import Comissao  # Modelo correto de comissões
from .services import (
    autorizar_comissao, 
    processar_pagamento_comissao, 
    cancelar_comissao,
    obter_estatisticas_comissoes
)


def is_admin_or_financeiro(user):
    """Verifica se usuário é admin ou do financeiro"""
    return user.is_superuser or user.groups.filter(name__in=['Administradores', 'Financeiro']).exists()


@login_required
@user_passes_test(is_admin_or_financeiro)
def painel_gestao_comissoes(request):
    """
    Painel principal de gestão de comissões
    Lista todas as comissões com filtros
    """
    # Filtros
    tipo_filtro = request.GET.get('tipo', 'todos')  # todos, lead, consultor, captador
    status_filtro = request.GET.get('status', 'todos')  # todos, DISPONIVEL, AUTORIZADO, PAGO, CANCELADO
    competencia_filtro = request.GET.get('competencia', '')  # YYYY-MM
    busca = request.GET.get('busca', '')
    
    # Busca comissões de cada tipo
    comissoes_lead = ComissaoLead.objects.select_related('atendente', 'lead', 'autorizado_por', 'pago_por')
    comissoes_consultor = ComissaoConsultor.objects.select_related('consultor', 'venda', 'parcela', 'autorizado_por', 'pago_por')
    # Comissões de captador estão no modelo financeiro.Comissao
    comissoes_captador = Comissao.objects.filter(
        tipo_comissao__in=['CAPTADOR_ENTRADA', 'CAPTADOR_PARCELA']
    ).select_related('usuario', 'venda')
    
    # Aplica filtro de tipo
    if tipo_filtro == 'lead':
        comissoes_consultor = comissoes_consultor.none()
        comissoes_captador = comissoes_captador.none()
    elif tipo_filtro == 'consultor':
        comissoes_lead = comissoes_lead.none()
        comissoes_captador = comissoes_captador.none()
    elif tipo_filtro == 'captador':
        comissoes_lead = comissoes_lead.none()
        comissoes_consultor = comissoes_consultor.none()
    
    # Aplica filtro de status
    if status_filtro != 'todos':
        comissoes_lead = comissoes_lead.filter(status=status_filtro)
        comissoes_consultor = comissoes_consultor.filter(status=status_filtro)
        
        # Para captador, mapear status do template para status do modelo financeiro.Comissao
        status_captador_map = {
            'DISPONIVEL': 'pendente',
            'PAGO': 'paga',
            'CANCELADO': 'cancelada'
        }
        status_captador = status_captador_map.get(status_filtro, status_filtro.lower())
        comissoes_captador = comissoes_captador.filter(status=status_captador)
    
    # Aplica filtro de competência
    if competencia_filtro:
        try:
            comp_date = datetime.strptime(competencia_filtro, '%Y-%m').date()
            comissoes_lead = comissoes_lead.filter(competencia=comp_date)
            comissoes_consultor = comissoes_consultor.filter(competencia=comp_date)
            comissoes_captador = comissoes_captador.filter(competencia=comp_date)
        except ValueError:
            pass
    
    # Aplica busca por nome de usuário
    if busca:
        comissoes_lead = comissoes_lead.filter(
            Q(atendente__first_name__icontains=busca) |
            Q(atendente__last_name__icontains=busca) |
            Q(atendente__email__icontains=busca)
        )
        comissoes_consultor = comissoes_consultor.filter(
            Q(consultor__first_name__icontains=busca) |
            Q(consultor__last_name__icontains=busca) |
            Q(consultor__email__icontains=busca)
        )
        comissoes_captador = comissoes_captador.filter(
            Q(captador__first_name__icontains=busca) |
            Q(captador__last_name__icontains=busca) |
            Q(captador__email__icontains=busca)
        )
    
    # Monta lista unificada com tipo
    comissoes_lista = []
    
    for c in comissoes_lead:
        comissoes_lista.append({
            'id': c.id,
            'tipo': 'atendente',
            'tipo_display': 'Atendente',
            'usuario': c.atendente,
            'valor': c.valor,
            'status': c.status,
            'status_display': c.get_status_display(),
            'competencia': c.competencia,
            'data_criacao': c.data_criacao,
            'data_autorizacao': c.data_autorizacao,
            'autorizado_por': c.autorizado_por,
            'data_pagamento': c.data_pagamento,
            'pago_por': c.pago_por,
            'referencia': f"Lead #{c.lead.id}",
            'observacoes': c.observacoes,
        })
    
    for c in comissoes_consultor:
        comissoes_lista.append({
            'id': c.id,
            'tipo': 'consultor',
            'tipo_display': 'Consultor',
            'usuario': c.consultor,
            'valor': c.valor,
            'valor_venda': c.valor_venda,
            'percentual': c.percentual,
            'status': c.status,
            'status_display': c.get_status_display(),
            'competencia': c.competencia,
            'data_criacao': c.data_criacao,
            'data_autorizacao': c.data_autorizacao,
            'autorizado_por': c.autorizado_por,
            'data_pagamento': c.data_pagamento,
            'pago_por': c.pago_por,
            'referencia': f"Venda #{c.venda.id}" + (f" - Parcela #{c.parcela.numero_parcela}" if c.parcela else ""),
            'observacoes': c.observacoes,
        })
    
    for c in comissoes_captador:
        # Modelo financeiro.Comissao tem campos diferentes
        parcela_texto = "Entrada" if c.tipo_comissao == 'CAPTADOR_ENTRADA' else f"Parcela #{c.parcela.numero_parcela if c.parcela else '?'}"
        
        # Mapear status do modelo financeiro para os status esperados pelo template
        status_map = {
            'pendente': 'DISPONIVEL',
            'paga': 'PAGO',
            'cancelada': 'CANCELADO'
        }
        status_mapeado = status_map.get(c.status, 'DISPONIVEL')
        
        comissoes_lista.append({
            'id': c.id,
            'tipo': 'captador',
            'tipo_display': 'Captador',
            'usuario': c.usuario,  # Campo 'usuario' no modelo Comissao
            'valor': c.valor_comissao,  # Campo 'valor_comissao' no modelo Comissao
            'valor_venda': Decimal('0'),  # Modelo Comissao não tem este campo
            'percentual': c.percentual_comissao,  # Campo 'percentual_comissao' no modelo Comissao
            'status': status_mapeado,  # Status mapeado para formato do template
            'status_display': c.get_status_display(),
            'competencia': None,  # Modelo Comissao não tem este campo
            'data_criacao': c.data_calculada,  # Campo 'data_calculada' no modelo Comissao
            'data_autorizacao': None,  # Modelo Comissao não tem este campo
            'autorizado_por': None,  # Modelo Comissao não tem este campo
            'data_pagamento': c.data_pagamento,
            'pago_por': None,  # Modelo Comissao não tem este campo
            'referencia': f"Venda #{c.venda.id} - {parcela_texto}",
            'observacoes': c.observacoes,
        })
    
    # Ordena por data de criação (mais recente primeiro)
    comissoes_lista.sort(key=lambda x: x['data_criacao'], reverse=True)
    
    # Paginação - 25 itens por página
    paginator = Paginator(comissoes_lista, 25)
    page_number = request.GET.get('page', 1)
    
    try:
        comissoes_paginadas = paginator.page(page_number)
    except PageNotAnInteger:
        # Se page não é um inteiro, entrega primeira página
        comissoes_paginadas = paginator.page(1)
    except EmptyPage:
        # Se page está fora do range, entrega última página
        comissoes_paginadas = paginator.page(paginator.num_pages)
    
    # Estatísticas
    stats = obter_estatisticas_comissoes(
        tipo_comissao=tipo_filtro if tipo_filtro != 'todos' else None,
        competencia=comp_date if competencia_filtro else None
    )
    
    # Lista de competências disponíveis (últimos 12 meses)
    competencias = []
    data_atual = timezone.now().date().replace(day=1)
    for i in range(12):
        comp = data_atual - timedelta(days=30 * i)
        competencias.append({
            'valor': comp.strftime('%Y-%m'),
            'texto': comp.strftime('%m/%Y')
        })
    
    context = {
        'comissoes': comissoes_paginadas,
        'page_obj': comissoes_paginadas,  # Para compatibilidade com template
        'total_comissoes': len(comissoes_lista),
        'stats': stats,
        'tipo_filtro': tipo_filtro,
        'status_filtro': status_filtro,
        'competencia_filtro': competencia_filtro,
        'busca': busca,
        'competencias': competencias,
    }
    
    return render(request, 'comissoes/painel_gestao.html', context)


@login_required
@user_passes_test(is_admin_or_financeiro)
def autorizar_comissao_view(request, tipo, comissao_id):
    """Autoriza uma comissão"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)
    
    comissao = autorizar_comissao(comissao_id, tipo, request.user)
    
    if comissao:
        messages.success(request, f'Comissão #{comissao_id} autorizada com sucesso!')
        return JsonResponse({'success': True, 'message': 'Comissão autorizada!'})
    else:
        messages.error(request, 'Erro ao autorizar comissão. Verifique se ela está disponível.')
        return JsonResponse({'success': False, 'message': 'Erro ao autorizar'}, status=400)


@login_required
@user_passes_test(is_admin_or_financeiro)
def processar_pagamento_view(request, tipo, comissao_id):
    """Processa pagamento de uma comissão"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)
    
    comissao = processar_pagamento_comissao(comissao_id, tipo, request.user)
    
    if comissao:
        messages.success(request, f'Pagamento da comissão #{comissao_id} processado com sucesso!')
        return JsonResponse({'success': True, 'message': 'Pagamento processado!'})
    else:
        messages.error(request, 'Erro ao processar pagamento. Verifique se a comissão está autorizada.')
        return JsonResponse({'success': False, 'message': 'Erro ao processar'}, status=400)


@login_required
@user_passes_test(is_admin_or_financeiro)
def cancelar_comissao_view(request, tipo, comissao_id):
    """Cancela uma comissão"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)
    
    motivo = request.POST.get('motivo', '')
    comissao = cancelar_comissao(comissao_id, tipo, request.user, motivo)
    
    if comissao:
        messages.success(request, f'Comissão #{comissao_id} cancelada com sucesso!')
        return JsonResponse({'success': True, 'message': 'Comissão cancelada!'})
    else:
        messages.error(request, 'Erro ao cancelar comissão. Comissões pagas não podem ser canceladas.')
        return JsonResponse({'success': False, 'message': 'Erro ao cancelar'}, status=400)


@login_required
@user_passes_test(is_admin_or_financeiro)
def dashboard_comissoes(request):
    """
    Dashboard com estatísticas gerais de comissões
    """
    # Estatísticas gerais
    stats_gerais = obter_estatisticas_comissoes()
    
    # Estatísticas por tipo
    stats_lead = obter_estatisticas_comissoes(tipo_comissao='lead')
    stats_consultor = obter_estatisticas_comissoes(tipo_comissao='consultor')
    stats_captador = obter_estatisticas_comissoes(tipo_comissao='captador')
    
    # Comissões recentes
    comissoes_recentes = []
    
    for c in ComissaoLead.objects.select_related('atendente', 'lead').order_by('-data_criacao')[:10]:
        comissoes_recentes.append({
            'tipo': 'Atendente',
            'usuario': c.atendente.get_full_name() or c.atendente.username,
            'valor': c.valor,
            'status': c.get_status_display(),
            'data': c.data_criacao,
        })
    
    for c in ComissaoConsultor.objects.select_related('consultor', 'venda').order_by('-data_criacao')[:10]:
        comissoes_recentes.append({
            'tipo': 'Consultor',
            'usuario': c.consultor.get_full_name() or c.consultor.username,
            'valor': c.valor,
            'status': c.get_status_display(),
            'data': c.data_criacao,
        })
    
    for c in ComissaoCaptador.objects.select_related('captador', 'venda').order_by('-data_criacao')[:10]:
        comissoes_recentes.append({
            'tipo': 'Captador',
            'usuario': c.captador.get_full_name() or c.captador.username,
            'valor': c.valor,
            'status': c.get_status_display(),
            'data': c.data_criacao,
        })
    
    comissoes_recentes.sort(key=lambda x: x['data'], reverse=True)
    comissoes_recentes = comissoes_recentes[:20]
    
    context = {
        'stats_gerais': stats_gerais,
        'stats_lead': stats_lead,
        'stats_consultor': stats_consultor,
        'stats_captador': stats_captador,
        'comissoes_recentes': comissoes_recentes,
    }
    
    return render(request, 'comissoes/dashboard.html', context)


@login_required
@user_passes_test(is_admin_or_financeiro)
def relatorio_usuario(request, user_id, tipo):
    """
    Relatório detalhado de comissões de um usuário específico
    
    Args:
        user_id: ID do usuário
        tipo: 'atendente', 'consultor' ou 'captador'
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    usuario = get_object_or_404(User, id=user_id)
    
    # Filtros
    mes_filtro = request.GET.get('mes', '')
    ano_filtro = request.GET.get('ano', str(timezone.now().year))
    status_filtro = request.GET.get('status', 'todos')
    
    # Preparar filtros de data (usa data_criacao ao invés de competencia)
    filtro_data = Q()
    if mes_filtro and ano_filtro:
        try:
            # Remover pontos e vírgulas do ano (2.025 -> 2025)
            ano_limpo = ano_filtro.replace('.', '').replace(',', '')
            # Filtrar por mês/ano de criação da comissão
            filtro_data = Q(
                data_criacao__year=int(ano_limpo),
                data_criacao__month=int(mes_filtro)
            )
        except (ValueError, TypeError):
            pass
    
    # Buscar comissões do usuário
    comissoes = []
    total_comissoes = Decimal('0.00')
    total_vendas = Decimal('0.00')
    
    if tipo == 'atendente':
        queryset = ComissaoLead.objects.filter(atendente=usuario)
        if filtro_data:
            queryset = queryset.filter(filtro_data)
        if status_filtro != 'todos':
            queryset = queryset.filter(status=status_filtro)
        
        queryset = queryset.select_related('lead').order_by('-data_criacao')
        
        for c in queryset:
            comissoes.append({
                'id': c.id,
                'data': c.data_criacao,
                'referencia': f"Lead #{c.lead.id}",
                'valor': c.valor,
                'percentual': None,
                'valor_base': Decimal('0.50'),  # Valor fixo por levantamento
                'status': c.status,
                'status_display': c.get_status_display(),
                'competencia': c.competencia,
                'observacoes': c.observacoes,
            })
            if c.status == 'PAGO':
                total_comissoes += c.valor
        
        # Para atendentes, calcular quantidade de levantamentos
        total_vendas = queryset.filter(status='PAGO').count()
        regra_comissao = """
        <strong>R$ 0,50 por levantamento PIX confirmado:</strong><br>
        • A comissão é gerada automaticamente quando o cliente paga o PIX de levantamento<br>
        • Valor fixo de R$ 0,50 por levantamento<br>
        <small class="text-muted">* Pagamento: 5º dia útil do mês vigente, referente ao mês anterior</small>
        """
        
    elif tipo == 'consultor':
        queryset = ComissaoConsultor.objects.filter(consultor=usuario)
        if filtro_data:
            queryset = queryset.filter(filtro_data)
        if status_filtro != 'todos':
            queryset = queryset.filter(status=status_filtro)
        
        queryset = queryset.select_related('venda').order_by('-data_criacao')
        
        for c in queryset:
            comissoes.append({
                'id': c.id,
                'data': c.data_criacao,
                'referencia': f"Venda #{c.venda.id} - Entrada",
                'valor': c.valor,
                'percentual': c.percentual,
                'valor_base': c.valor_venda,  # Valor da entrada
                'status': c.status,
                'status_display': c.get_status_display(),
                'competencia': c.competencia,
                'observacoes': c.observacoes,
            })
            if c.status == 'PAGO':
                total_comissoes += c.valor
                total_vendas += c.valor_venda
        
        regra_comissao = """
        <strong>Comissão progressiva por faturamento mensal (SOMENTE SOBRE ENTRADAS):</strong><br>
        • Faturamento ≥ R$ 20.000 = 2% de comissão<br>
        • Faturamento ≥ R$ 30.000 = 3% de comissão<br>
        • Faturamento ≥ R$ 40.000 = 4% de comissão<br>
        • Faturamento ≥ R$ 50.000 = 5% de comissão<br>
        • Faturamento ≥ R$ 60.000 = 6% de comissão<br>
        • Faturamento ≥ R$ 80.000 = 10% de comissão<br>
        <small class="text-muted">* Percentual aplicado retroativamente sobre todo o faturamento do mês</small><br>
        <small class="text-muted">* Pagamento: 5º dia útil do mês vigente, referente ao mês anterior</small>
        """
        
    elif tipo == 'captador':
        queryset = ComissaoCaptador.objects.filter(captador=usuario)
        if filtro_data:
            queryset = queryset.filter(filtro_data)
        if status_filtro != 'todos':
            queryset = queryset.filter(status=status_filtro)
        
        queryset = queryset.select_related('venda', 'parcela').order_by('-data_criacao')
        
        for c in queryset:
            parcela_texto = "Entrada" if not c.parcela else f"Parcela {c.parcela.numero_parcela}"
            comissoes.append({
                'id': c.id,
                'data': c.data_criacao,
                'referencia': f"Venda #{c.venda.id} - {parcela_texto}",
                'valor': c.valor,
                'percentual': c.percentual,
                'valor_base': c.valor_venda,
                'status': c.status,
                'status_display': c.get_status_display(),
                'competencia': c.competencia,
                'observacoes': c.observacoes,
            })
            if c.status == 'PAGO':
                total_comissoes += c.valor
                total_vendas += c.valor_venda
        
        regra_comissao = """
        <strong>3% sobre valores pagos (Entrada + Parcelas):</strong><br>
        • Cada pagamento recebido gera uma comissão de 3%<br>
        • Incide sobre entrada e todas as parcelas pagas<br>
        <small class="text-muted">* Pagamento: Todo dia 10 do mês vigente, referente aos valores recebidos no mês anterior</small>
        """
    
    else:
        return redirect('comissoes:painel_gestao')
    
    # Calcular valor a receber (disponíveis + autorizadas)
    valor_a_receber = queryset.filter(
        status__in=['DISPONIVEL', 'AUTORIZADO']
    ).aggregate(total=Sum('valor'))['total'] or Decimal('0')
    
    # Estatísticas do usuário
    stats_usuario = {
        'total_comissoes': queryset.count(),
        'disponiveis': queryset.filter(status='DISPONIVEL').count(),
        'autorizadas': queryset.filter(status='AUTORIZADO').count(),
        'pagas': queryset.filter(status='PAGO').count(),
        'canceladas': queryset.filter(status='CANCELADO').count(),
        'valor_total': total_comissoes,
        'valor_vendas': total_vendas,
        'valor_a_receber': valor_a_receber,
    }
    
    # Lista de meses/anos disponíveis
    anos_disponiveis = list(range(timezone.now().year, timezone.now().year - 3, -1))
    meses_disponiveis = [
        {'valor': '1', 'nome': 'Janeiro'},
        {'valor': '2', 'nome': 'Fevereiro'},
        {'valor': '3', 'nome': 'Março'},
        {'valor': '4', 'nome': 'Abril'},
        {'valor': '5', 'nome': 'Maio'},
        {'valor': '6', 'nome': 'Junho'},
        {'valor': '7', 'nome': 'Julho'},
        {'valor': '8', 'nome': 'Agosto'},
        {'valor': '9', 'nome': 'Setembro'},
        {'valor': '10', 'nome': 'Outubro'},
        {'valor': '11', 'nome': 'Novembro'},
        {'valor': '12', 'nome': 'Dezembro'},
    ]
    
    context = {
        'usuario': usuario,
        'tipo': tipo,
        'tipo_display': {'atendente': 'Atendente', 'consultor': 'Consultor', 'captador': 'Captador'}[tipo],
        'comissoes': comissoes,
        'stats': stats_usuario,
        'regra_comissao': regra_comissao,
        'mes_filtro': mes_filtro,
        'ano_filtro': ano_filtro,
        'status_filtro': status_filtro,
        'anos_disponiveis': anos_disponiveis,
        'meses_disponiveis': meses_disponiveis,
    }
    
    return render(request, 'comissoes/relatorio_usuario.html', context)
