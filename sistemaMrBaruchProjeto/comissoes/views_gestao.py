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
from datetime import datetime, timedelta
from decimal import Decimal

from .models import ComissaoLead, ComissaoConsultor, ComissaoCaptador
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
    comissoes_captador = ComissaoCaptador.objects.select_related('captador', 'venda', 'parcela', 'autorizado_por', 'pago_por')
    
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
        comissoes_captador = comissoes_captador.filter(status=status_filtro)
    
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
            'tipo': 'lead',
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
            'referencia': f"Venda #{c.venda.id}" + (f" - Parcela #{c.parcela.numero}" if c.parcela else ""),
            'observacoes': c.observacoes,
        })
    
    for c in comissoes_captador:
        comissoes_lista.append({
            'id': c.id,
            'tipo': 'captador',
            'tipo_display': 'Captador',
            'usuario': c.captador,
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
            'referencia': f"Venda #{c.venda.id}" + (f" - Parcela #{c.parcela.numero}" if c.parcela else ""),
            'observacoes': c.observacoes,
        })
    
    # Ordena por data de criação (mais recente primeiro)
    comissoes_lista.sort(key=lambda x: x['data_criacao'], reverse=True)
    
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
        'comissoes': comissoes_lista,
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
