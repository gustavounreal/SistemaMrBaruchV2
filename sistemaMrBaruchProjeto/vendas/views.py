from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.db import models as django_models
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from decimal import Decimal
from .forms import UserForm, ConsultorForm
from accounts.models import DadosUsuario


# Funções auxiliares de permissão
def is_consultor_or_admin(user):
    """Verifica se usuário é consultor (comercial1) ou admin"""
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name__in=['comercial1', 'admin', 'Admin']).exists()


def is_atendente_or_admin(user):
    """Verifica se usuário é atendente ou admin"""
    if user.is_superuser or user.is_staff:
        return True
    return user.groups.filter(name__in=['atendente', 'admin', 'Atendentes', 'Admin']).exists()


# Outras funções...

@login_required
def perfil_consultor(request):
    """
    View para gerenciar o perfil do consultor (comercial1).
    Permite atualizar dados pessoais e profissionais.
    """
    # Verifica se o usuário é consultor
    if not request.user.groups.filter(name='comercial1').exists():
        messages.error(request, 'Acesso negado. Você não tem permissão para acessar esta página.')
        return redirect('vendas:painel_leads_pagos')
    
    # Obtém ou cria o perfil de consultor (DadosUsuario)
    consultor, created = DadosUsuario.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        consultor_form = ConsultorForm(request.POST, instance=consultor)
        
        if user_form.is_valid() and consultor_form.is_valid():
            user_form.save()
            consultor_form.save()
            
            # Verifica se houve alteração de senha
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            
            if new_password and confirm_password:
                if new_password == confirm_password:
                    request.user.set_password(new_password)
                    request.user.save()
                    messages.success(request, 'Senha alterada com sucesso. Por favor, faça login novamente.')
                    return redirect('accounts:login')
                else:
                    messages.error(request, 'As senhas não conferem.')
            else:
                messages.success(request, 'Perfil atualizado com sucesso!')
                return redirect('vendas:perfil_consultor')
    else:
        user_form = UserForm(instance=request.user)
        consultor_form = ConsultorForm(instance=consultor)
    
    context = {
        'user_form': user_form,
        'consultor_form': consultor_form,
    }
    
    return render(request, 'vendas/perfil_consultor.html', context)


@login_required
@user_passes_test(is_consultor_or_admin)
def painel_metricas_consultor(request):
    """
    Painel completo de métricas e performance do consultor.
    Exibe todas as informações sobre vendas, comissões e status de pagamentos.
    """
    from datetime import date
    from calendar import monthrange
    
    # Usuário atual (consultor)
    usuario = request.user
    is_admin = request.user.is_superuser or request.user.groups.filter(name='admin').exists()
    
    # Mês e ano vigente
    hoje = timezone.now().date()
    mes_atual = hoje.month
    ano_atual = hoje.year
    primeiro_dia_mes = date(ano_atual, mes_atual, 1)
    ultimo_dia_mes = date(ano_atual, mes_atual, monthrange(ano_atual, mes_atual)[1])
    
    # ====== VENDAS ======
    # Todas as vendas do consultor
    if is_admin:
        vendas = Venda.objects.all()
    else:
        vendas = Venda.objects.filter(consultor=usuario)
    
    vendas = vendas.select_related('cliente', 'servico', 'captador', 'consultor').prefetch_related(
        'parcela_set', 'comissoes'
    )
    
    # Vendas do mês vigente
    vendas_mes = vendas.filter(data_criacao__gte=primeiro_dia_mes, data_criacao__lte=ultimo_dia_mes)
    
    # Métricas de vendas
    total_vendas = vendas.count()
    total_vendas_mes = vendas_mes.count()
    valor_total_vendas = vendas.aggregate(total=django_models.Sum('valor_total'))['total'] or Decimal('0')
    valor_vendas_mes = vendas_mes.aggregate(total=django_models.Sum('valor_total'))['total'] or Decimal('0')
    
    # ====== PARCELAS ======
    if is_admin:
        parcelas = FinanceiroParcela.objects.all()
    else:
        parcelas = FinanceiroParcela.objects.filter(venda__consultor=usuario)
    
    # Boletos pagos (clientes)
    boletos_pagos = parcelas.filter(status='paga').count()
    valor_boletos_pagos = parcelas.filter(status='paga').aggregate(
        total=django_models.Sum('valor')
    )['total'] or Decimal('0')
    
    # Boletos vencidos (clientes)
    boletos_vencidos = parcelas.filter(
        status='vencida',
        data_vencimento__lt=hoje
    ).count()
    valor_boletos_vencidos = parcelas.filter(
        status='vencida',
        data_vencimento__lt=hoje
    ).aggregate(total=django_models.Sum('valor'))['total'] or Decimal('0')
    
    # Boletos a vencer
    boletos_a_vencer = parcelas.filter(
        status='aberta',
        data_vencimento__gte=hoje
    ).count()
    valor_boletos_a_vencer = parcelas.filter(
        status='aberta',
        data_vencimento__gte=hoje
    ).aggregate(total=django_models.Sum('valor'))['total'] or Decimal('0')
    
    # Próximo vencimento
    proxima_parcela = parcelas.filter(
        status__in=['aberta', 'vencida'],
        data_vencimento__gte=hoje
    ).order_by('data_vencimento').first()
    
    # ====== COMISSÕES ======
    if is_admin:
        comissoes = Comissao.objects.all()
    else:
        comissoes = Comissao.objects.filter(usuario=usuario)
    
    comissoes = comissoes.filter(tipo_comissao__in=['CONSULTOR_ENTRADA', 'CONSULTOR_PARCELA'])
    
    # Comissões pagas
    comissoes_pagas = comissoes.filter(status='paga')
    total_comissao_recebida = comissoes_pagas.aggregate(
        total=django_models.Sum('valor_comissao')
    )['total'] or Decimal('0')
    
    # Comissões pendentes (a receber)
    comissoes_pendentes = comissoes.filter(status='pendente')
    comissao_a_receber = comissoes_pendentes.aggregate(
        total=django_models.Sum('valor_comissao')
    )['total'] or Decimal('0')
    
    # Comissões do mês vigente (a receber neste mês)
    comissoes_mes = comissoes_pendentes.filter(
        data_calculada__gte=primeiro_dia_mes,
        data_calculada__lte=ultimo_dia_mes
    )
    comissao_mes_vigente = comissoes_mes.aggregate(
        total=django_models.Sum('valor_comissao')
    )['total'] or Decimal('0')
    
    # Valor previsto total a receber (todas as comissões pendentes)
    valor_previsto_total = comissao_a_receber
    
    # ====== FAIXA DE COMISSÃO ATUAL ======
    # Calcular faturamento do mês (entradas + boletos pagos)
    from core.commission_service import CommissionCalculator
    
    # Somar valor de entradas e parcelas pagas do mês
    faturamento_mes_atual = Decimal('0')
    
    # Entradas pagas no mês
    if is_admin:
        entradas_mes = Venda.objects.filter(
            data_criacao__gte=primeiro_dia_mes,
            data_criacao__lte=ultimo_dia_mes,
            status_pagamento_entrada='PAGO'
        ).aggregate(total=django_models.Sum('valor_entrada'))['total'] or Decimal('0')
    else:
        entradas_mes = Venda.objects.filter(
            consultor=usuario,
            data_criacao__gte=primeiro_dia_mes,
            data_criacao__lte=ultimo_dia_mes,
            status_pagamento_entrada='PAGO'
        ).aggregate(total=django_models.Sum('valor_entrada'))['total'] or Decimal('0')
    
    # Parcelas pagas no mês
    parcelas_pagas_mes = parcelas.filter(
        status='paga',
        data_pagamento__gte=primeiro_dia_mes,
        data_pagamento__lte=ultimo_dia_mes
    ).aggregate(total=django_models.Sum('valor'))['total'] or Decimal('0')
    
    faturamento_mes_atual = entradas_mes + parcelas_pagas_mes
    percentual_atual = CommissionCalculator.calcular_percentual_consultor(faturamento_mes_atual)
    
    # Calcular próxima faixa
    faixas = [
        (Decimal('80000.00'), Decimal('10.00'), 'R$ 80.000'),
        (Decimal('60000.00'), Decimal('6.00'), 'R$ 60.000'),
        (Decimal('50000.00'), Decimal('5.00'), 'R$ 50.000'),
        (Decimal('40000.00'), Decimal('4.00'), 'R$ 40.000'),
        (Decimal('30000.00'), Decimal('3.00'), 'R$ 30.000'),
        (Decimal('20000.00'), Decimal('2.00'), 'R$ 20.000'),
    ]
    
    proxima_faixa_valor = None
    proxima_faixa_percentual = None
    falta_para_proxima_faixa = None
    
    for limite, percentual, label in faixas:
        if faturamento_mes_atual < limite:
            proxima_faixa_valor = label
            proxima_faixa_percentual = percentual
            falta_para_proxima_faixa = limite - faturamento_mes_atual
    
    # ====== VENDAS DETALHADAS (últimas 10) ======
    vendas_detalhadas = vendas.order_by('-data_criacao')[:10]
    
    # Preparar dados para cada venda
    vendas_lista = []
    for venda in vendas_detalhadas:
        # Nome do cliente
        nome_cliente = venda.cliente.lead.nome_completo if venda.cliente and hasattr(venda.cliente, 'lead') else "Cliente sem nome"
        
        # Parcelas da venda
        parcelas_venda = venda.parcela_set.all()
        parcelas_pagas = parcelas_venda.filter(status='paga').count()
        parcelas_vencidas = parcelas_venda.filter(status='vencida').count()
        parcelas_abertas = parcelas_venda.filter(status='aberta').count()
        
        vendas_lista.append({
            'venda': venda,
            'nome_cliente': nome_cliente,
            'parcelas_pagas': parcelas_pagas,
            'parcelas_vencidas': parcelas_vencidas,
            'parcelas_abertas': parcelas_abertas,
        })
    
    context = {
        'usuario': usuario,
        'is_admin': is_admin,
        'mes_atual': primeiro_dia_mes.strftime('%B/%Y'),
        
        # Vendas
        'total_vendas': total_vendas,
        'total_vendas_mes': total_vendas_mes,
        'valor_total_vendas': valor_total_vendas,
        'valor_vendas_mes': valor_vendas_mes,
        
        # Parcelas/Boletos
        'boletos_pagos': boletos_pagos,
        'valor_boletos_pagos': valor_boletos_pagos,
        'boletos_vencidos': boletos_vencidos,
        'valor_boletos_vencidos': valor_boletos_vencidos,
        'boletos_a_vencer': boletos_a_vencer,
        'valor_boletos_a_vencer': valor_boletos_a_vencer,
        'proxima_parcela': proxima_parcela,
        
        # Comissões
        'total_comissao_recebida': total_comissao_recebida,
        'comissao_a_receber': comissao_a_receber,
        'comissao_mes_vigente': comissao_mes_vigente,
        'valor_previsto_total': valor_previsto_total,
        
        # Faixa de Comissão
        'faturamento_mes_atual': faturamento_mes_atual,
        'percentual_comissao_atual': percentual_atual,
        'proxima_faixa_valor': proxima_faixa_valor,
        'proxima_faixa_percentual': proxima_faixa_percentual,
        'falta_para_proxima_faixa': falta_para_proxima_faixa,
        
        # Detalhes
        'vendas_lista': vendas_lista,
    }
    
    return render(request, 'vendas/painel_metricas_consultor.html', context)

from datetime import timedelta
from dateutil.relativedelta import relativedelta
import json

from .models import PreVenda, Venda, DocumentoVenda, Servico, Parcela, MotivoRecusa
from marketing.models import Lead, MotivoContato
from clientes.models import Cliente
from financeiro.models import PixLevantamento, Parcela as FinanceiroParcela, Comissao
from core.asaas_service import AsaasService
from core.commission_service import CommissionService
from core.services import LogService


@login_required
@user_passes_test(is_consultor_or_admin)
def painel_leads_pagos(request):
    """
    Painel para consultores: Lista leads com PIX de levantamento pago
    Estes leads estão prontos para iniciar a pré-venda
    ATUALIZADO: Filtra apenas leads atribuídos ao consultor logado
    """
    from compliance.models import AnaliseCompliance
    
    # Determinar se é admin ou consultor individual
    is_admin = request.user.is_superuser or request.user.groups.filter(name='admin').exists()
    
    # ATUALIZADO: Buscar apenas leads aprovados pelo Compliance e atribuídos ao consultor logado
    leads_com_pix_pago = Lead.objects.filter(
        pix_levantamentos__status_pagamento='pago',
        passou_compliance=True,  # Apenas leads aprovados pelo Compliance
        status__in=['APROVADO_COMPLIANCE', 'EM_NEGOCIACAO', 'QUALIFICADO']
    )
    
    # Se não for admin, filtrar apenas leads atribuídos ao usuário logado via AnaliseCompliance
    if not is_admin:
        # Buscar IDs dos leads atribuídos ao consultor logado
        leads_atribuidos_ids = AnaliseCompliance.objects.filter(
            consultor_atribuido=request.user
        ).values_list('lead_id', flat=True)
        leads_com_pix_pago = leads_com_pix_pago.filter(id__in=leads_atribuidos_ids)
    
    leads_com_pix_pago = leads_com_pix_pago.select_related(
        'captador', 'atendente'
    ).prefetch_related('pix_levantamentos').distinct().order_by('-data_cadastro')
    
    # Buscar pré-vendas aceitas aguardando finalização
    # Primeiro, buscar IDs de leads que já têm vendas finalizadas
    leads_com_venda_ids = Venda.objects.values_list('cliente__lead_id', flat=True)
    
    pre_vendas_aceitas = PreVenda.objects.filter(
        status='ACEITO'
    ).exclude(
        lead_id__in=leads_com_venda_ids  # Exclui se já tem venda associada
    )
    
    # Se não for admin, filtrar apenas pré-vendas do usuário logado
    if not is_admin:
        pre_vendas_aceitas = pre_vendas_aceitas.filter(lead_id__in=leads_atribuidos_ids)
    
    pre_vendas_aceitas = pre_vendas_aceitas.select_related(
        'lead', 'lead__captador', 'lead__atendente', 'motivo_principal'
    ).order_by('-data_criacao')
    
    # Filtros opcionais
    filtro_captador = request.GET.get('captador')
    filtro_atendente = request.GET.get('atendente')
    filtro_status_venda = request.GET.get('status_venda', 'todos')  # todos, sem_pre_venda, em_pre_venda, vendido, aceito
    
    if filtro_captador:
        leads_com_pix_pago = leads_com_pix_pago.filter(captador_id=filtro_captador)
        pre_vendas_aceitas = pre_vendas_aceitas.filter(lead__captador_id=filtro_captador)
    
    if filtro_atendente:
        leads_com_pix_pago = leads_com_pix_pago.filter(atendente_id=filtro_atendente)
        pre_vendas_aceitas = pre_vendas_aceitas.filter(lead__atendente_id=filtro_atendente)
    
    # Filtrar por status de venda
    if filtro_status_venda == 'sem_pre_venda':
        # Leads que ainda não têm pré-venda
        leads_com_prevenda_ids = PreVenda.objects.values_list('lead_id', flat=True)
        leads_com_pix_pago = leads_com_pix_pago.exclude(id__in=leads_com_prevenda_ids)
    elif filtro_status_venda == 'em_pre_venda':
        # Leads que têm pré-venda mas ainda não viraram venda
        leads_com_prevenda_ids = PreVenda.objects.filter(
            status__in=['AGUARDANDO_ACEITE', 'PENDENTE']
        ).values_list('lead_id', flat=True)
        leads_com_pix_pago = leads_com_pix_pago.filter(id__in=leads_com_prevenda_ids)
    elif filtro_status_venda == 'aceito':
        # Apenas pré-vendas aceitas aguardando finalização
        leads_com_pix_pago = Lead.objects.none()  # Não mostrar na lista principal
    elif filtro_status_venda == 'vendido':
        # Leads que já viraram venda (através do cliente)
        leads_com_venda_ids = Venda.objects.select_related('cliente').values_list('cliente__lead_id', flat=True)
        leads_com_pix_pago = leads_com_pix_pago.filter(id__in=leads_com_venda_ids)
    
    # Adicionar informações de pré-venda e venda para cada lead
    for lead in leads_com_pix_pago:
        # Buscar PIX mais recente
        lead.pix_levantamento = lead.pix_levantamentos.filter(status_pagamento='pago').order_by('-data_criacao').first()
        
        # Buscar pré-venda
        lead.pre_venda = PreVenda.objects.filter(lead=lead).first()
        
        # Buscar venda (através do cliente) com PIX de entrada
        try:
            from datetime import timedelta
            
            cliente = getattr(lead, 'cliente', None)  # Lead tem OneToOneField com related_name='cliente'
            if cliente:
                lead.venda = Venda.objects.filter(cliente=cliente).prefetch_related(
                    'pix_entradas'
                ).first()
                
                # Verificar se deve mostrar PIX (vendas das últimas 72 horas / 3 dias)
                if lead.venda:
                    agora = timezone.now()
                    setenta_duas_horas_atras = agora - timedelta(hours=72)
                    
                    # Garantir que ambos estão timezone-aware
                    data_criacao_aware = lead.venda.data_criacao
                    if timezone.is_naive(data_criacao_aware):
                        data_criacao_aware = timezone.make_aware(data_criacao_aware)
                    
                    lead.venda.mostrar_pix = data_criacao_aware >= setenta_duas_horas_atras
                    pix_count = lead.venda.pix_entradas.count()
            else:
                lead.venda = None
        except Exception as e:
            lead.venda = None
        
        # Definir status para exibição
        if lead.venda:
            lead.status_venda = 'vendido'
            lead.status_venda_label = 'Venda Concluída'
            lead.status_venda_class = 'success'
        elif lead.pre_venda:
            if lead.pre_venda.status == 'ACEITO':
                lead.status_venda = 'aceito'
                lead.status_venda_label = 'Aceite Registrado'
                lead.status_venda_class = 'info'
            else:
                lead.status_venda = 'em_pre_venda'
                lead.status_venda_label = 'Em Pré-Venda'
                lead.status_venda_class = 'warning'
        else:
            lead.status_venda = 'pronto'
            lead.status_venda_label = 'Pronto para Pré-Venda'
            lead.status_venda_class = 'primary'
    
    # Paginação
    page = request.GET.get('page', 1)
    paginator = Paginator(leads_com_pix_pago, 15)  # 15 leads por página
    
    try:
        leads_paginated = paginator.page(page)
    except PageNotAnInteger:
        leads_paginated = paginator.page(1)
    except EmptyPage:
        leads_paginated = paginator.page(paginator.num_pages)
    
    # Buscar usuários para filtros
    from django.contrib.auth import get_user_model
    User = get_user_model()
    captadores = User.objects.filter(groups__name__in=['atendente', 'Atendentes']).distinct()
    atendentes = User.objects.filter(groups__name__in=['atendente', 'Atendentes']).distinct()
    consultores = User.objects.filter(groups__name__in=['comercial1', 'admin', 'Admin']).distinct()
    
    # Métricas adicionais (apenas do consultor logado)
    total_pre_vendas_aceitas = pre_vendas_aceitas.count()
    
    # Leads prontos para abordar (sem pré-venda iniciada)
    leads_com_prevenda_ids = PreVenda.objects.values_list('lead_id', flat=True)
    if not is_admin:
        leads_prontos = leads_com_pix_pago.exclude(id__in=leads_com_prevenda_ids).exclude(id__in=leads_com_venda_ids).count()
    else:
        leads_prontos = Lead.objects.filter(
            pix_levantamentos__status_pagamento='pago',
            passou_compliance=True
        ).exclude(id__in=leads_com_prevenda_ids).exclude(id__in=leads_com_venda_ids).distinct().count()
    
    # Pré-vendas em negociação (aguardando aceite do cliente)
    pre_vendas_pendentes = PreVenda.objects.filter(
        status__in=['AGUARDANDO_ACEITE', 'PENDENTE']
    )
    if not is_admin:
        pre_vendas_pendentes = pre_vendas_pendentes.filter(lead_id__in=leads_atribuidos_ids)
    total_pre_vendas_pendentes = pre_vendas_pendentes.count()
    
    # Vendas finalizadas do mês - filtrar por consultor se não for admin
    vendas_mes_query = Venda.objects.filter(
        data_criacao__month=timezone.now().month,
        data_criacao__year=timezone.now().year
    )
    
    if not is_admin:
        vendas_mes_query = vendas_mes_query.filter(consultor=request.user)
    
    total_vendas_mes = vendas_mes_query.count()
    valor_vendas_mes = vendas_mes_query.aggregate(total=django_models.Sum('valor_total'))['total'] or 0
    
    context = {
        'leads': leads_paginated,
        'total_leads': leads_com_pix_pago.count(),
        'leads_prontos': leads_prontos,
        'total_pre_vendas_pendentes': total_pre_vendas_pendentes,
        'pre_vendas_aceitas': pre_vendas_aceitas,
        'total_pre_vendas_aceitas': total_pre_vendas_aceitas,
        'total_vendas_mes': total_vendas_mes,
        'valor_vendas_mes': valor_vendas_mes,
        'captadores': captadores,
        'atendentes': atendentes,
        'consultores': consultores,
        'filtro_captador': filtro_captador,
        'filtro_atendente': filtro_atendente,
        'filtro_status_venda': filtro_status_venda,
        'is_admin': is_admin,  # Para mostrar informações diferentes na interface
    }
    
    return render(request, 'vendas/painel_leads_pagos.html', context)


@login_required
@user_passes_test(is_consultor_or_admin)
def iniciar_pre_venda(request, lead_id):
    """
    Primeira etapa: Coleta dos desejos do cliente após levantamento pago
    Apenas consultores podem acessar
    """
    lead = get_object_or_404(Lead, id=lead_id)
    
    # NOVO: Verifica se o lead passou pelo Compliance
    if not lead.passou_compliance:
        messages.error(request, 'Este lead ainda não foi aprovado pelo Compliance. Aguarde a análise.')
        return redirect('vendas:painel_leads_pagos')
    
    # Verifica se o levantamento foi pago
    if lead.status not in ['LEVANTAMENTO_PAGO', 'APROVADO_COMPLIANCE', 'EM_NEGOCIACAO']:
        messages.error(request, 'O levantamento ainda não foi pago pelo cliente.')
        return redirect('vendas:painel_leads_pagos')
    
    # Verifica se já existe uma pré-venda para este lead
    pre_venda = PreVenda.objects.filter(lead=lead).first()
    
    if request.method == 'POST':
        try:
            with transaction.atomic():
                if pre_venda is None:
                    pre_venda = PreVenda(lead=lead, atendente=request.user)
                
                # Coleta dados do formulário
                pre_venda.prazo_risco = request.POST.get('prazo_risco')
                pre_venda.servico_interesse = request.POST.get('servico_interesse')
                pre_venda.perfil_emocional_id = request.POST.get('perfil_emocional')
                pre_venda.motivo_principal_id = request.POST.get('motivo_principal')
                pre_venda.valor_proposto = Decimal(request.POST.get('valor_proposto', '0'))
                pre_venda.observacoes_levantamento = request.POST.get('observacoes_levantamento', '')
                # Novos campos financeiros
                pre_venda.valor_total = Decimal(request.POST.get('valor_total', '0'))
                pre_venda.valor_entrada = Decimal(request.POST.get('valor_entrada', '0'))
                pre_venda.quantidade_parcelas = int(request.POST.get('quantidade_parcelas', 1))
                pre_venda.valor_parcela = Decimal(request.POST.get('valor_parcela', '0'))
                pre_venda.frequencia_pagamento = request.POST.get('frequencia_pagamento', 'MENSAL')
                pre_venda.status = 'AGUARDANDO_ACEITE'
                pre_venda.save()
                
                # Atualiza status do lead
                lead.status = 'EM_NEGOCIACAO'
                lead.save()
                
                messages.success(request, 'Pré-venda registrada! Aguardando aceite do cliente.')
                return redirect('vendas:registrar_aceite', pre_venda_id=pre_venda.id)
                
        except Exception as e:
            messages.error(request, f'Erro ao registrar pré-venda: {str(e)}')
    
    # Busca dados para o formulário
    motivos = MotivoContato.objects.filter(tipo='MOTIVO', ativo=True)
    perfis_emocionais = MotivoContato.objects.filter(tipo='PERFIL', ativo=True)
    
    context = {
        'lead': lead,
        'pre_venda': pre_venda,
        'motivos': motivos,
        'perfis_emocionais': perfis_emocionais,
        'servicos_choices': PreVenda.SERVICO_INTERESSE_CHOICES,
        'prazo_risco_choices': PreVenda.PRAZO_RISCO_CHOICES,
    }
    
    return render(request, 'vendas/pre_venda_form.html', context)


@login_required
@user_passes_test(is_consultor_or_admin)  # Alterado de is_atendente_or_admin para is_consultor_or_admin
def registrar_aceite(request, pre_venda_id):
    """
    Segunda etapa: Registra se o cliente aceitou ou recusou a proposta
    """
    pre_venda = get_object_or_404(PreVenda, id=pre_venda_id)
    
    if pre_venda.status != 'AGUARDANDO_ACEITE':
        messages.warning(request, 'Esta pré-venda já teve seu aceite processado.')
        return redirect('vendas:detalhes_pre_venda', pre_venda_id=pre_venda_id)
    
    # Busca motivos de recusa ativos
    motivos_recusa = MotivoRecusa.objects.filter(ativo=True).order_by('ordem', 'nome')
    
    if request.method == 'POST':
        aceite = request.POST.get('aceite') == 'sim'
        
        with transaction.atomic():
            pre_venda.aceite_cliente = aceite
            pre_venda.data_resposta_cliente = timezone.now()
            
            if aceite:
                pre_venda.status = 'ACEITO'
                pre_venda.lead.status = 'CLIENTE'
                messages.success(request, 'Cliente aceitou a proposta! Prossiga com o cadastro completo.')
                pre_venda.save()
                pre_venda.lead.save()
                return redirect('vendas:cadastro_venda', pre_venda_id=pre_venda_id)
            else:
                pre_venda.status = 'RECUSADO'
                pre_venda.lead.status = 'PERDIDO'
                
                # Captura o ID do motivo de recusa selecionado
                motivo_recusa_id = request.POST.get('motivo_recusa_categoria', '')
                motivo_detalhes = request.POST.get('motivo_recusa', '')
                
                if motivo_recusa_id:
                    try:
                        motivo = MotivoRecusa.objects.get(id=motivo_recusa_id)
                        pre_venda.motivo_recusa_principal = motivo
                        motivo_texto = motivo.nome
                    except MotivoRecusa.DoesNotExist:
                        motivo_texto = "Motivo não especificado"
                else:
                    motivo_texto = "Motivo não especificado"
                
                # Salva detalhes adicionais se fornecidos
                if motivo_detalhes:
                    pre_venda.motivo_recusa = motivo_detalhes
                
                messages.info(request, f'Cliente recusou a proposta. Motivo: {motivo_texto}')
                pre_venda.save()
                pre_venda.lead.save()
                return redirect('vendas:painel_leads_pagos')
    
    context = {
        'pre_venda': pre_venda,
        'motivos_recusa': motivos_recusa,
    }
    return render(request, 'vendas/registrar_aceite.html', context)


@login_required
@user_passes_test(is_consultor_or_admin)
def cadastro_venda_direta(request):
    """
    Cadastro direto de venda com fluxo completo:
    1. Criar venda
    2. Gerar cobrança entrada (ASAAS)
    3. Gerar parcelas + cobranças (ASAAS)
    4. Calcular comissões (atendente + captador + consultor)
    """
    if request.method == 'POST':
        try:
            with transaction.atomic():
                # ==========================================
                # ETAPA 1: VALIDAR E PREPARAR DADOS
                # ==========================================
                
                # Cliente
                cpf = request.POST.get('cpf')
                cliente, created = Cliente.objects.get_or_create(
                    cpf=cpf,
                    defaults={
                        'nome': request.POST.get('nome'),
                        'email': request.POST.get('email'),
                        'telefone': request.POST.get('telefone'),
                        'data_nascimento': request.POST.get('data_nascimento') or None,
                        'endereco': request.POST.get('endereco'),
                        'cidade': request.POST.get('cidade'),
                        'estado': request.POST.get('estado'),
                        'cep': request.POST.get('cep'),
                    }
                )
                
                if not created:
                    cliente.nome = request.POST.get('nome')
                    cliente.email = request.POST.get('email')
                    cliente.telefone = request.POST.get('telefone')
                    if request.POST.get('data_nascimento'):
                        cliente.data_nascimento = request.POST.get('data_nascimento')
                    cliente.endereco = request.POST.get('endereco')
                    cliente.cidade = request.POST.get('cidade')
                    cliente.estado = request.POST.get('estado')
                    cliente.cep = request.POST.get('cep')
                    cliente.save()
                
                # Serviço
                servico_id = request.POST.get('servico')
                servico = get_object_or_404(Servico, id=servico_id)
                
                # Valores
                valor_total = Decimal(request.POST.get('valor_total', '0'))
                valor_entrada = Decimal(request.POST.get('valor_entrada', '0'))
                quantidade_parcelas = int(request.POST.get('quantidade_parcelas', 0))
                valor_parcela = Decimal(request.POST.get('valor_parcela', '0')) if quantidade_parcelas > 0 else Decimal('0')
                
                # ===== Validações/ajustes server-side =====
                # Garante que entrada não seja maior que o total
                if valor_entrada > valor_total:
                    messages.warning(request, 'Valor de entrada maior que o valor total. Ajustando entrada para o valor total.')
                    valor_entrada = valor_total
                    quantidade_parcelas = 0
                    valor_parcela = Decimal('0')

                # Garante que o valor da parcela individual não seja maior que o total
                if quantidade_parcelas > 0 and valor_parcela > valor_total:
                    messages.warning(request, 'Valor da parcela informado é maior que o valor total. Ajustando para dividir o restante em 1 parcela.')
                    quantidade_parcelas = 1
                    valor_parcela = max(Decimal('0'), valor_total - valor_entrada)

                # Ajusta distribuição das parcelas caso a soma difira do restante
                valor_restante = valor_total - valor_entrada
                valor_total_parcelas = quantidade_parcelas * valor_parcela if quantidade_parcelas > 0 else Decimal('0')

                if quantidade_parcelas > 0 and abs(valor_total_parcelas - valor_restante) > Decimal('0.01'):
                    # Recalcula o valor da parcela para dividir o restante de forma uniforme
                    try:
                        novo_valor_parcela = (valor_restante / quantidade_parcelas).quantize(Decimal('0.01'))
                        valor_parcela = novo_valor_parcela
                        messages.info(request, 'Valores de parcela ajustados automaticamente para distribuir o saldo restante.')
                        valor_total_parcelas = quantidade_parcelas * valor_parcela
                    except Exception:
                        # Em caso de erro, zera parcelas
                        quantidade_parcelas = 0
                        valor_parcela = Decimal('0')
                        valor_total_parcelas = Decimal('0')

                # Por fim, se ainda houver diferença relevante, rejeitar
                if abs(valor_total - (valor_entrada + valor_total_parcelas)) > Decimal('0.01'):
                    raise ValueError(f"Soma incorreta após ajustes: Entrada R$ {valor_entrada:.2f} + Parcelas R$ {valor_total_parcelas:.2f} ≠ Total R$ {valor_total:.2f}")
                
                # Pagamento
                forma_entrada = request.POST.get('forma_pagamento_entrada', 'PIX')
                forma_parcelas = request.POST.get('forma_pagamento_parcelas', 'BOLETO')
                frequencia = request.POST.get('frequencia_pagamento', 'MENSAL')
                
                data_vencimento_primeira_str = request.POST.get('data_vencimento_primeira')
                if data_vencimento_primeira_str:
                    from datetime import datetime
                    data_vencimento_primeira = datetime.strptime(data_vencimento_primeira_str, '%Y-%m-%d').date()
                else:
                    data_vencimento_primeira = (timezone.now() + timedelta(days=30)).date()
                
                # Lead (se existir)
                lead_id = request.POST.get('lead_id')
                lead = None
                captador_user = request.user  # Default: quem cadastra é o captador
                
                if lead_id:
                    try:
                        lead = Lead.objects.get(id=lead_id)
                        captador_user = lead.captador if lead.captador else request.user
                    except Lead.DoesNotExist:
                        pass
                
                # ==========================================
                # ETAPA 2: CRIAR VENDA
                # ==========================================
                
                venda = Venda.objects.create(
                    cliente=cliente,
                    servico=servico,
                    captador=captador_user,
                    consultor=request.user,
                    valor_total=valor_total,
                    valor_entrada=valor_entrada,
                    sem_entrada=(valor_entrada == 0),
                    quantidade_parcelas=quantidade_parcelas,
                    valor_parcela=valor_parcela,
                    forma_entrada=forma_entrada,
                    forma_pagamento=forma_parcelas,
                    frequencia_pagamento=frequencia,
                    data_vencimento_primeira=data_vencimento_primeira,
                    status='ORCAMENTO',  # Status inicial: Orçamento (aguardando pagamento entrada)
                    observacoes=request.POST.get('observacoes', ''),
                )
                
                # Log
                try:
                    LogService.log_info(
                        'VENDA_CRIADA',
                        f'Venda #{venda.id} criada - Cliente: {cliente.nome} - Valor: R$ {valor_total:.2f}',
                        usuario=request.user
                    )
                except:
                    pass  # Não bloquear se LogService falhar
                
                # ==========================================
                # ETAPA 3: UPLOAD DE DOCUMENTOS
                # ==========================================
                
                documentos = request.FILES.getlist('documentos')
                tipos_doc = request.POST.getlist('tipo_documento')
                
                for i, documento in enumerate(documentos):
                    tipo = tipos_doc[i] if i < len(tipos_doc) else 'OUTROS'
                    DocumentoVenda.objects.create(
                        venda=venda,
                        tipo_documento=tipo,
                        arquivo=documento,
                        usuario_upload=request.user,
                    )
                
                # ==========================================
                # ETAPA 4: INTEGRAÇÃO ASAAS
                # ==========================================
                
                asaas = AsaasService()
                asaas_customer = None
                entrada_paga = False
                
                try:
                    # 4.1. Criar/atualizar cliente no ASAAS
                    asaas_customer = asaas.criar_cliente({
                        'nome': cliente.nome,
                        'cpf_cnpj': cliente.cpf,
                        'email': cliente.email,
                        'telefone': cliente.telefone,
                        'cep': cliente.cep,
                        'endereco': cliente.endereco,
                        'numero': '',
                        'bairro': '',
                        'id_cliente': str(cliente.id),
                    })
                    
                    # 4.2. Gerar cobrança da ENTRADA
                    if valor_entrada > 0:
                        cobranca_entrada = asaas.criar_cobranca({
                            'customer': asaas_customer['id'],
                            'billingType': forma_entrada,
                            'value': float(valor_entrada),
                            'dueDate': timezone.now().date().isoformat(),
                            'description': f'Entrada - Venda #{venda.id} - {servico.nome}',
                            'externalReference': f'venda_{venda.id}_entrada',
                        })
                        
                        # Verificar se já foi pago
                        if cobranca_entrada.get('status') == 'RECEIVED':
                            entrada_paga = True
                    
                    # 4.3. Gerar PARCELAS no sistema (NÃO enviar ao ASAAS ainda)
                    # As parcelas serão enviadas ao ASAAS apenas quando o contrato for assinado
                    if quantidade_parcelas > 0 and valor_parcela > 0:
                        data_vencimento_atual = data_vencimento_primeira
                        
                        for i in range(1, quantidade_parcelas + 1):
                            # Criar parcela no sistema (financeiro) - SEM enviar ao ASAAS
                            parcela = FinanceiroParcela.objects.create(
                                venda=venda,
                                numero_parcela=i,
                                valor=valor_parcela,
                                data_vencimento=data_vencimento_atual,
                                status='aberta',
                                enviado_asaas=False  # ⚠️ Não enviado - aguarda assinatura do contrato
                            )
                            
                            # ⚠️ NÃO criar cobrança no ASAAS agora
                            # O envio será feito automaticamente quando o contrato for marcado como ASSINADO
                            # no módulo jurídico (juridico/views.py -> atualizar_status_contrato)
                            
                            # Calcular próxima data de vencimento
                            if i < quantidade_parcelas:
                                if frequencia == 'SEMANAL':
                                    data_vencimento_atual += timedelta(weeks=1)
                                elif frequencia == 'QUINZENAL':
                                    data_vencimento_atual += timedelta(weeks=2)
                                elif frequencia == 'MENSAL':
                                    data_vencimento_atual += relativedelta(months=1)
                
                except Exception as e:
                    try:
                        LogService.log_error(
                            'ASAAS_ERRO_GERAL',
                            f'Erro na integração ASAAS: {str(e)}',
                            usuario=request.user
                        )
                    except:
                        pass
                    messages.warning(request, f'Venda cadastrada, mas houve erro na integração ASAAS: {str(e)}')
                
                # ==========================================
                # ETAPA 5: GERAR COMISSÕES
                # ==========================================
                
                comissoes_criadas = []
                
                # 5.1. Comissão do ATENDENTE (se houver lead com PIX pago)
                if lead:
                    try:
                        pix_pago = lead.pix_levantamentos.filter(status_pagamento='pago').exists()
                        if pix_pago:
                            comissao_atendente = CommissionService.criar_comissao_atendente(lead)
                            comissoes_criadas.append(f"Atendente: R$ {comissao_atendente.valor:.2f}")
                            
                            try:
                                LogService.log_info(
                                    'COMISSAO_CRIADA',
                                    f'Comissão atendente criada: R$ {comissao_atendente.valor:.2f}',
                                    usuario=request.user
                                )
                            except:
                                pass
                    except Exception as e:
                        try:
                            LogService.log_error(
                                'COMISSAO_ERRO',
                                f'Erro ao criar comissão atendente: {str(e)}',
                                usuario=request.user
                            )
                        except:
                            pass
                
                # 5.2. Comissões da ENTRADA (Captador + Consultor)
                if valor_entrada > 0:
                    try:
                        comissoes_entrada = CommissionService.criar_comissao_entrada_venda(venda)
                        
                        # Se entrada já paga, marcar comissões como pagas
                        if entrada_paga:
                            for key in ['captador', 'consultor']:
                                if key in comissoes_entrada and comissoes_entrada[key]:
                                    comissoes_entrada[key].status = 'paga'
                                    comissoes_entrada[key].data_pagamento = timezone.now().date()
                                    comissoes_entrada[key].save()
                        
                        if 'captador' in comissoes_entrada and comissoes_entrada['captador']:
                            comissoes_criadas.append(
                                f"Captador (entrada): R$ {comissoes_entrada['captador'].valor_comissao:.2f} ({comissoes_entrada['captador'].percentual_comissao}%)"
                            )
                        
                        if 'consultor' in comissoes_entrada and comissoes_entrada['consultor']:
                            comissoes_criadas.append(
                                f"Consultor (entrada): R$ {comissoes_entrada['consultor'].valor_comissao:.2f} ({comissoes_entrada['consultor'].percentual_comissao}%)"
                            )
                        
                        try:
                            LogService.log_info(
                                'COMISSOES_CRIADAS',
                                f'Comissões da entrada criadas',
                                usuario=request.user
                            )
                        except:
                            pass
                        
                    except Exception as e:
                        try:
                            LogService.log_error(
                                'COMISSAO_ERRO',
                                f'Erro ao criar comissões da entrada: {str(e)}',
                                usuario=request.user
                            )
                        except:
                            pass
                        messages.warning(request, f'Comissões da entrada não foram criadas: {str(e)}')
                
                # 5.3. Comissões das PARCELAS
                # ❌ NÃO CRIAR AGORA - Webhook ASAAS criará automaticamente quando cada parcela for paga
                
                # ==========================================
                # ETAPA 6: MENSAGEM DE SUCESSO
                # ==========================================
                
                msg_sucesso = f'✅ Venda #{venda.id} cadastrada com sucesso!'
                
                if valor_entrada > 0:
                    msg_sucesso += f' | 💰 Entrada: R$ {valor_entrada:.2f}'
                
                if quantidade_parcelas > 0:
                    msg_sucesso += f' | 📅 {quantidade_parcelas}x de R$ {valor_parcela:.2f}'
                
                if comissoes_criadas:
                    msg_sucesso += ' | 💸 Comissões: ' + ', '.join(comissoes_criadas)
                
                messages.success(request, msg_sucesso)
                
                return redirect('vendas:detalhes_venda', venda_id=venda.id)
                
        except Exception as e:
            try:
                LogService.log_error(
                    'VENDA_ERRO',
                    f'Erro ao cadastrar venda: {str(e)}',
                    usuario=request.user
                )
            except:
                pass
            messages.error(request, f'❌ Erro ao cadastrar venda: {str(e)}')
    
    # GET: Renderizar formulário
    servicos = Servico.objects.filter(ativo=True)
    
    # Buscar leads disponíveis (com PIX pago, sem venda)
    try:
        leads_com_venda = Venda.objects.values_list('id', flat=True)
        leads_disponiveis = Lead.objects.filter(
            status='LEVANTAMENTO_PAGO'
        ).exclude(
            id__in=leads_com_venda
        ).select_related('captador', 'atendente')
    except:
        leads_disponiveis = []
    
    context = {
        'servicos': servicos,
        'leads_disponiveis': leads_disponiveis,
        'formas_pagamento': Venda.FORMA_PAGAMENTO_CHOICES,
        'frequencias': Venda.FREQUENCIA_CHOICES,
        'tipos_documento': DocumentoVenda.TIPO_DOCUMENTO_CHOICES,
    }
    
    return render(request, 'vendas/cadastro_venda_direta.html', context)


@login_required
@user_passes_test(is_consultor_or_admin)  # Alterado de is_atendente_or_admin para is_consultor_or_admin
def cadastro_venda(request, pre_venda_id):
    """
    Terceira etapa: Cadastro completo da venda e coleta de documentos
    """
    pre_venda = get_object_or_404(PreVenda, id=pre_venda_id)
    
    if pre_venda.status != 'ACEITO':
        messages.error(request, 'Esta pré-venda não foi aceita pelo cliente.')
        return redirect('vendas:detalhes_pre_venda', pre_venda_id=pre_venda_id)
    
    # Pré-carrega dados do Lead para o formulário
    lead = pre_venda.lead
    dados_iniciais = {
        'nome': lead.nome_completo,
        'cpf_cnpj': lead.cpf_cnpj or '',
        'email': lead.email or '',
        'telefone': lead.telefone or '',
        'valor_total': pre_venda.valor_total or pre_venda.valor_proposto,
        'valor_entrada': pre_venda.valor_entrada,
        'quantidade_parcelas': pre_venda.quantidade_parcelas,
        'valor_parcela': pre_venda.valor_parcela,
        'frequencia_pagamento': pre_venda.frequencia_pagamento,
    }
    
    if request.method == 'POST':
        print("="*80)
        print("INICIANDO CADASTRO DE VENDA")
        print(f"POST data recebido: {request.POST.keys()}")
        print("="*80)
        try:
            with transaction.atomic():
                # Usa o Lead da pré-venda (já existe e está correto)
                lead = pre_venda.lead
                print(f"Lead da pré-venda: {lead} (ID: {lead.id})")
                
                # Atualiza dados do lead com informações do formulário
                lead.nome_completo = request.POST.get('nome')
                lead.email = request.POST.get('email', lead.email)
                lead.telefone = request.POST.get('telefone', lead.telefone)
                cpf_cnpj = request.POST.get('cpf')
                if cpf_cnpj:
                    lead.cpf_cnpj = cpf_cnpj
                lead.status = 'CLIENTE'
                lead.save()
                print(f"Lead atualizado com sucesso")
                
                # Cria ou atualiza o Cliente (vinculado ao Lead)
                cliente, cliente_created = Cliente.objects.get_or_create(
                    lead=lead,
                    defaults={
                        'data_nascimento': request.POST.get('data_nascimento'),
                        'rg': request.POST.get('rg', ''),
                        'profissao': request.POST.get('profissao', ''),
                        'nacionalidade': request.POST.get('nacionalidade', 'Brasileiro(a)'),
                        'estado_civil': request.POST.get('estado_civil', ''),
                        'cep': request.POST.get('cep', ''),
                        'rua': request.POST.get('rua', ''),
                        'numero': request.POST.get('numero', ''),
                        'bairro': request.POST.get('bairro', ''),
                        'cidade': request.POST.get('cidade', ''),
                        'estado': request.POST.get('estado', ''),
                        'cadastro_completo': True,
                    }
                )
                
                if not cliente_created:
                    # Atualiza dados existentes do cliente
                    cliente.data_nascimento = request.POST.get('data_nascimento')
                    cliente.rg = request.POST.get('rg', '')
                    cliente.profissao = request.POST.get('profissao', '')
                    cliente.nacionalidade = request.POST.get('nacionalidade', 'Brasileira')
                    cliente.estado_civil = request.POST.get('estado_civil', '')
                    cliente.cep = request.POST.get('cep', '')
                    cliente.rua = request.POST.get('rua', '')
                    cliente.numero = request.POST.get('numero', '')
                    cliente.bairro = request.POST.get('bairro', '')
                    cliente.cidade = request.POST.get('cidade', '')
                    cliente.estado = request.POST.get('estado', '')
                    cliente.cadastro_completo = True
                    cliente.save()
                    print(f"Cliente atualizado: {cliente}")
                else:
                    print(f"Cliente criado: {cliente}")
                
                # Obtém captador e consultor (consultor sempre = usuário logado)
                # Prioridade: 1) Captador da pré-venda/lead, 2) ID informado, 3) Usuário logado
                from accounts.models import User
                
                if pre_venda.lead.captador:
                    captador = pre_venda.lead.captador
                    print(f"Captador do Lead: {captador}")
                else:
                    captador_id = request.POST.get('captador_id')
                    captador = User.objects.get(id=captador_id) if captador_id else request.user
                    print(f"Captador informado/padrão: {captador}")
                
                consultor = request.user  # Sempre o usuário logado
                print(f"Consultor (logado): {consultor}")
                
                # ==== Extrai valores do POST ANTES de usar em qualquer lugar ====
                quantidade_parcelas = int(request.POST.get('quantidade_parcelas', 1))
                valor_entrada = Decimal(request.POST.get('valor_entrada', '0'))
                valor_total = Decimal(request.POST.get('valor_total'))
                valor_parcela = Decimal(request.POST.get('valor_parcela', '0'))
                
                # Determina os serviços contratados baseado nos checkboxes
                servicos_contratados = []
                if request.POST.get('limpa_nome') == 'on':
                    servicos_contratados.append('Limpa Nome')
                if request.POST.get('retirada_travas') == 'on':
                    servicos_contratados.append('Retirada de Travas')
                if request.POST.get('recuperacao_score') == 'on':
                    servicos_contratados.append('Recuperação de Score')
                
                # Cria nome do serviço baseado nos contratados
                if servicos_contratados:
                    nome_servico = ' + '.join(servicos_contratados)
                else:
                    nome_servico = 'Consultoria Financeira'
                
                print(f"Serviços contratados: {servicos_contratados}")
                print(f"Nome do serviço: {nome_servico}")
                
                # Mapeamento de combinações de serviços para tipo e prazo
                # Chave: tupla ordenada de serviços | Valor: dict com tipo e prazo
                COMBINACOES_SERVICOS = {
                    ('Limpa Nome',): {
                        'tipo': 'LIMPA_NOME',
                        'prazo': 60,
                        'descricao': 'Serviço de limpeza de nome - remoção de restrições cadastrais'
                    },
                    ('Retirada de Travas',): {
                        'tipo': 'RETIRADA_TRAVAS',
                        'prazo': 45,
                        'descricao': 'Serviço de retirada de travas bancárias e financeiras'
                    },
                    ('Recuperação de Score',): {
                        'tipo': 'RECUPERACAO_SCORE',
                        'prazo': 90,
                        'descricao': 'Serviço de recuperação e melhoria de score de crédito'
                    },
                    ('Limpa Nome', 'Recuperação de Score'): {
                        'tipo': 'COMBINADO',
                        'prazo': 90,
                        'descricao': 'Pacote combinado: Limpeza de Nome + Recuperação de Score'
                    },
                    ('Limpa Nome', 'Retirada de Travas'): {
                        'tipo': 'COMBINADO',
                        'prazo': 75,
                        'descricao': 'Pacote combinado: Limpeza de Nome + Retirada de Travas'
                    },
                    ('Recuperação de Score', 'Retirada de Travas'): {
                        'tipo': 'COMBINADO',
                        'prazo': 90,
                        'descricao': 'Pacote combinado: Recuperação de Score + Retirada de Travas'
                    },
                    ('Limpa Nome', 'Recuperação de Score', 'Retirada de Travas'): {
                        'tipo': 'COMBINADO',
                        'prazo': 120,
                        'descricao': 'Pacote completo: Limpeza de Nome + Recuperação de Score + Retirada de Travas'
                    },
                }
                
                # Normaliza a ordem dos serviços para buscar no mapeamento
                servicos_tuple = tuple(sorted(servicos_contratados))
                config_servico = COMBINACOES_SERVICOS.get(servicos_tuple, {
                    'tipo': 'COMBINADO',
                    'prazo': 90,
                    'descricao': f'Pacote personalizado: {nome_servico}'
                })
                
                # ===== Validações/ajustes server-side (valores já extraídos acima) =====
                # Garante que entrada não seja maior que o total
                if valor_entrada > valor_total:
                    messages.warning(request, 'Valor de entrada maior que o valor total. Ajustando automaticamente para o valor total.')
                    valor_entrada = valor_total
                    quantidade_parcelas = 0
                    valor_parcela = Decimal('0')

                # Se parcela individual for maior que total, ajustar para 1 parcela com o restante
                if quantidade_parcelas > 0 and valor_parcela > valor_total:
                    messages.warning(request, 'Valor da parcela maior que o valor total. Ajustando para 1 parcela com o restante do serviço.')
                    quantidade_parcelas = 1
                    valor_parcela = max(Decimal('0'), valor_total - valor_entrada)

                # Recalcula restante e ajusta parcelas para dividir o saldo corretamente
                valor_restante = valor_total - valor_entrada
                if quantidade_parcelas > 0:
                    total_parcelas = valor_parcela * quantidade_parcelas
                    if abs(total_parcelas - valor_restante) > Decimal('0.01'):
                        try:
                            valor_parcela = (valor_restante / quantidade_parcelas).quantize(Decimal('0.01'))
                            messages.info(request, 'Valores de parcela ajustados para distribuir o saldo restante.')
                        except Exception:
                            quantidade_parcelas = 0
                            valor_parcela = Decimal('0')
                
                # ===== Busca ou cria o serviço (dentro da transação, após validações) =====
                # Usar update_or_create para evitar duplicatas e atualizar preço se já existe
                servico, servico_criado = Servico.objects.update_or_create(
                    nome=nome_servico,
                    defaults={
                        'tipo': config_servico['tipo'],
                        'descricao': config_servico['descricao'],
                        'prazo_medio': config_servico['prazo'],
                        'preco_base': valor_total,
                        'ativo': True
                    }
                )
                
                if servico_criado:
                    print(f"✅ Novo serviço criado: {servico}")
                else:
                    print(f"📝 Serviço existente atualizado: {servico}")
                
                # Cria a venda
                print(f"Criando venda com:")
                print(f"  - Cliente: {cliente}")
                print(f"  - Serviço: {servico}")
                print(f"  - Captador: {captador}")
                print(f"  - Consultor: {consultor}")
                print(f"  - Valor Total: {valor_total}")
                print(f"  - Valor Entrada: {valor_entrada}")
                print(f"  - Parcelas: {quantidade_parcelas}x {valor_parcela}")
                
                # Processa campos de prazo
                data_inicio_servico = request.POST.get('data_inicio_servico')
                dias_conclusao = int(request.POST.get('dias_conclusao', 90))
                data_conclusao_prevista = request.POST.get('data_conclusao_prevista')
                
                # Converter data_vencimento_primeira para date
                data_vencimento_primeira_str = request.POST.get('data_vencimento_primeira')
                if data_vencimento_primeira_str:
                    from datetime import datetime
                    data_vencimento_primeira = datetime.strptime(data_vencimento_primeira_str, '%Y-%m-%d').date()
                else:
                    data_vencimento_primeira = (timezone.now() + timedelta(days=30)).date()
                
                # Calcula prazo de pagamento total arredondado
                frequencia = request.POST.get('frequencia_pagamento', 'MENSAL')
                dias_entre_parcelas = {'SEMANAL': 7, 'QUINZENAL': 15, 'MENSAL': 30}.get(frequencia, 30)
                prazo_total_calculado = quantidade_parcelas * dias_entre_parcelas
                valores_permitidos = [30, 60, 90, 120, 150, 180, 210, 240, 270]
                prazo_pagamento_total = min(valores_permitidos, key=lambda x: abs(x - prazo_total_calculado))
                
                venda = Venda.objects.create(
                    cliente=cliente,
                    servico=servico,
                    captador=captador,
                    consultor=consultor,
                    valor_total=valor_total,
                    valor_entrada=valor_entrada,
                    sem_entrada=(valor_entrada == 0),
                    quantidade_parcelas=quantidade_parcelas,
                    valor_parcela=valor_parcela,
                    frequencia_pagamento=frequencia,
                    forma_entrada=request.POST.get('forma_entrada', 'PIX'),
                    forma_pagamento=request.POST.get('forma_pagamento', 'BOLETO'),
                    data_vencimento_primeira=data_vencimento_primeira,
                    data_inicio_servico=data_inicio_servico if data_inicio_servico else None,
                    dias_para_conclusao=dias_conclusao,
                    data_conclusao_prevista=data_conclusao_prevista if data_conclusao_prevista else None,
                    prazo_pagamento_total=prazo_pagamento_total,
                    status='ORCAMENTO',  # Status inicial: Orçamento (aguardando pagamento entrada)
                    observacoes=request.POST.get('observacoes', ''),
                    limpa_nome=request.POST.get('limpa_nome') == 'on',
                    retirada_travas=request.POST.get('retirada_travas') == 'on',
                    recuperacao_score=request.POST.get('recuperacao_score') == 'on',
                )
                
                # Upload de documentos
                documentos = request.FILES.getlist('documentos')
                tipos_doc = request.POST.getlist('tipo_documento')
                
                for i, documento in enumerate(documentos):
                    tipo = tipos_doc[i] if i < len(tipos_doc) else 'OUTROS'
                    DocumentoVenda.objects.create(
                        venda=venda,
                        tipo_documento=tipo,
                        arquivo=documento,
                        usuario_upload=request.user,
                    )
                
                # Gera cobrança PIX no ASAAS se entrada > 0
                pix_entrada = None
                if venda.valor_entrada > 0:
                    try:
                        asaas = AsaasService()
                        
                        # Cria ou busca cliente no ASAAS
                        from financeiro.models import ClienteAsaas, PixEntrada
                        cliente_asaas, created = ClienteAsaas.objects.get_or_create(
                            lead=pre_venda.lead,
                            defaults={'asaas_customer_id': ''}
                        )
                        
                        if not cliente_asaas.asaas_customer_id:
                            # Cliente acessa dados via lead
                            cpf_limpo = (lead.cpf_cnpj or '').replace('.', '').replace('-', '').replace('/', '')
                            telefone_limpo = (lead.telefone or '').replace('(', '').replace(')', '').replace(' ', '').replace('-', '')
                            cep_limpo = (cliente.cep or '').replace('-', '')
                            
                            print(f"🔄 Criando cliente ASAAS: {lead.nome_completo}")
                            # Método criar_cliente espera chaves específicas
                            customer_data = asaas.criar_cliente({
                                'nome': lead.nome_completo,
                                'cpf_cnpj': cpf_limpo,
                                'email': lead.email or f'cliente{cliente.id}@mrbaruch.com.br',
                                'telefone': telefone_limpo,
                                'cep': cep_limpo,
                                'endereco': cliente.rua or '',
                                'numero': cliente.numero or 'S/N',
                                'bairro': cliente.bairro or '',
                                'id_cliente': str(cliente.id),
                            })
                            
                            # Verifica se customer foi criado com sucesso
                            if customer_data and 'id' in customer_data:
                                cliente_asaas.asaas_customer_id = customer_data['id']
                                cliente_asaas.save()
                                print(f"✅ Cliente ASAAS criado: {customer_data['id']}")
                            else:
                                raise ValueError(f"Falha ao criar cliente no ASAAS: {customer_data}")
                        
                        # Verifica se temos customer_id válido antes de criar cobrança
                        if cliente_asaas.asaas_customer_id:
                            print(f"🔄 Gerando PIX de entrada: R$ {venda.valor_entrada}")
                            # Gera cobrança PIX para entrada (criar_cobranca espera chaves específicas)
                            payment_data = {
                                'customer_id': cliente_asaas.asaas_customer_id,
                                'billing_type': 'PIX',
                                'value': float(venda.valor_entrada),
                                'due_date': timezone.now().date().isoformat(),
                                'description': f'Entrada - Venda #{venda.id} - {lead.nome_completo}',
                                'external_reference': f'venda_{venda.id}_entrada',
                            }
                            cobranca = asaas.criar_cobranca(payment_data)
                            
                            print(f"📋 Resposta ASAAS: {cobranca}")
                            
                            # Verifica se cobrança foi criada com sucesso
                            if cobranca and 'id' in cobranca:
                                # Obtém os dados do PIX
                                pix_code = cobranca.get('pixCopiaECola', '')
                                pix_qr_url = cobranca.get('encodedImage', '')
                                
                                print(f"🔍 Verificando dados do PIX na resposta inicial...")
                                print(f"   pixCopiaECola presente: {'pixCopiaECola' in cobranca}")
                                print(f"   encodedImage presente: {'encodedImage' in cobranca}")
                                
                                # Se não vier no response inicial, busca explicitamente o QR Code
                                if not pix_code:
                                    print("🔄 PIX Code não veio na resposta inicial. Buscando QR Code PIX...")
                                    qr_data = asaas.obter_qr_code_pix(cobranca['id'])
                                    print(f"📋 Resposta QR Code: {qr_data}")
                                    
                                    if qr_data:
                                        pix_code = qr_data.get('payload', '')
                                        pix_qr_url = qr_data.get('encodedImage', '')
                                        print(f"   ✅ Payload obtido: {len(pix_code)} caracteres")
                                        print(f"   ✅ EncodedImage obtido: {len(pix_qr_url)} caracteres")
                                    else:
                                        print("   ⚠️ Falha ao obter QR Code do ASAAS")
                                
                                # Fallback para invoiceUrl se ainda não tiver PIX Code
                                if not pix_code:
                                    pix_code = cobranca.get('invoiceUrl', f'PIX não disponível - Payment ID: {cobranca["id"]}')
                                    print(f"   ⚠️ Usando fallback: invoiceUrl")
                                
                                if not pix_qr_url:
                                    pix_qr_url = cobranca.get('invoiceUrl', '')
                                    print(f"   ⚠️ QR Code URL não disponível, usando invoiceUrl")
                                
                                # Salva PIX na tabela PixEntrada
                                pix_entrada = PixEntrada.objects.create(
                                    venda=venda,
                                    asaas_payment_id=cobranca['id'],
                                    valor=venda.valor_entrada,
                                    pix_code=pix_code or f'PIX não disponível - ID: {cobranca["id"]}',
                                    pix_qr_code_url=pix_qr_url or cobranca.get('invoiceUrl', ''),
                                    status_pagamento='pendente'
                                )
                                print(f"✅ PIX Entrada criado: ID={pix_entrada.id}, ASAAS={pix_entrada.asaas_payment_id}")
                                print(f"   PIX Code: {pix_code[:50]}..." if len(pix_code) > 50 else f"   PIX Code: {pix_code}")
                                messages.success(request, f'PIX de entrada gerado com sucesso! Valor: R$ {venda.valor_entrada}')
                            else:
                                print(f"⚠️ Cobrança ASAAS não criada corretamente: {cobranca}")
                                messages.warning(request, 'Venda cadastrada, mas não foi possível gerar o PIX de entrada no ASAAS.')
                        else:
                            print("⚠️ Cliente ASAAS sem ID válido - pulando criação de cobrança")
                            messages.warning(request, 'Venda cadastrada, mas não foi possível criar cliente no ASAAS para gerar PIX.')
                            
                    except Exception as e:
                        print(f"⚠️ Erro na integração ASAAS (entrada): {str(e)}")
                        import traceback
                        traceback.print_exc()
                        messages.warning(request, f'Venda cadastrada, mas houve erro ao gerar PIX de entrada: {str(e)}')
                else:
                    print("ℹ️ Sem valor de entrada - PIX não será gerado")
                
                # ============================================================
                # CRIAR COMISSÕES FUTURAS (ENTRADA + TODAS AS PARCELAS)
                # ============================================================
                print("\n" + "="*80)
                print("🔄 CRIANDO COMISSÕES FUTURAS DA VENDA")
                print("="*80)
                
                from core.commission_service import CommissionService
                from financeiro.models import Parcela, Comissao
                
                comissoes_criadas_total = {
                    'entrada_captador': None,
                    'entrada_consultor': None,
                    'parcelas_captador': [],
                    'parcelas_consultor': [],
                }
                
                # 1️⃣ COMISSÕES DA ENTRADA (se houver entrada)
                if venda.valor_entrada > 0 and not venda.sem_entrada:
                    print(f"\n1️⃣ Criando comissões da ENTRADA (R$ {venda.valor_entrada:.2f})...")
                    try:
                        comissoes_entrada = CommissionService.criar_comissao_entrada_venda(venda)
                        comissoes_criadas_total['entrada_captador'] = comissoes_entrada.get('captador')
                        comissoes_criadas_total['entrada_consultor'] = comissoes_entrada.get('consultor')
                        
                        if comissoes_entrada.get('captador'):
                            print(f"   ✅ Captador entrada: R$ {comissoes_entrada['captador'].valor_comissao:.2f} ({comissoes_entrada['captador'].percentual_comissao}%)")
                        if comissoes_entrada.get('consultor'):
                            print(f"   ✅ Consultor entrada: R$ {comissoes_entrada['consultor'].valor_comissao:.2f} ({comissoes_entrada['consultor'].percentual_comissao}%)")
                        elif comissoes_entrada.get('captador'):
                            print(f"   ⚠️ Consultor entrada: Não atingiu faturamento mínimo (< R$ 20.000)")
                    except Exception as e:
                        print(f"   ❌ Erro ao criar comissões de entrada: {str(e)}")
                        import traceback
                        traceback.print_exc()
                else:
                    print(f"\n1️⃣ Sem entrada - comissões da entrada não criadas")
                
                # 2️⃣ GERAR PARCELAS E CRIAR COMISSÕES FUTURAS
                if venda.quantidade_parcelas > 0:
                    print(f"\n2️⃣ Gerando {venda.quantidade_parcelas} parcelas e suas comissões futuras...")
                    
                    # Mapear frequência para dias
                    frequencia_dias = {
                        'SEMANAL': 7,
                        'QUINZENAL': 15,
                        'MENSAL': 30,
                    }
                    dias_intervalo = frequencia_dias.get(venda.frequencia_pagamento, 30)
                    
                    # Data inicial de vencimento
                    from datetime import timedelta
                    data_vencimento_base = venda.data_vencimento_primeira
                    
                    # Obter percentuais (captador sempre 3%)
                    percentual_captador = Decimal('3.00')
                    
                    # Faturamento mensal do consultor (para escala)
                    from datetime import date
                    mes_atual = venda.data_venda or timezone.now().date()
                    faturamento_mensal_consultor = CommissionService._calcular_faturamento_mensal_consultor(
                        consultor=venda.consultor,
                        mes=mes_atual.replace(day=1),
                        incluir_venda_atual=venda
                    )
                    from core.commission_service import CommissionCalculator
                    percentual_consultor = CommissionCalculator.calcular_percentual_consultor(faturamento_mensal_consultor)
                    
                    print(f"   Percentual Captador: {percentual_captador}% (fixo)")
                    print(f"   Percentual Consultor: {percentual_consultor}% (faturamento mensal: R$ {faturamento_mensal_consultor:.2f})")
                    
                    for i in range(1, venda.quantidade_parcelas + 1):
                        # Calcular data de vencimento
                        data_venc = data_vencimento_base + timedelta(days=(i - 1) * dias_intervalo)
                        
                        # Criar parcela (status inicial: aberta)
                        parcela = Parcela.objects.create(
                            venda=venda,
                            numero_parcela=i,
                            valor=venda.valor_parcela,
                            data_vencimento=data_venc,
                            status='aberta',
                            enviado_asaas=False,
                        )
                        
                        # Criar comissão FUTURA do CAPTADOR (status: pendente)
                        valor_comissao_captador = (venda.valor_parcela * percentual_captador / Decimal('100')).quantize(Decimal('0.01'))
                        comissao_captador = Comissao.objects.create(
                            usuario=venda.captador,
                            venda=venda,
                            parcela=parcela,
                            tipo_comissao='CAPTADOR_PARCELA',
                            valor_comissao=valor_comissao_captador,
                            percentual_comissao=percentual_captador,
                            status='pendente',
                            observacoes=f'Parcela {i}/{venda.quantidade_parcelas} - Aguardando pagamento'
                        )
                        comissoes_criadas_total['parcelas_captador'].append(comissao_captador)
                        
                        # Criar comissão FUTURA do CONSULTOR (se percentual > 0)
                        valor_comissao_consultor = Decimal('0.00')
                        if percentual_consultor > 0:
                            valor_comissao_consultor = (venda.valor_parcela * percentual_consultor / Decimal('100')).quantize(Decimal('0.01'))
                            comissao_consultor = Comissao.objects.create(
                                usuario=venda.consultor,
                                venda=venda,
                                parcela=parcela,
                                tipo_comissao='CONSULTOR_PARCELA',
                                valor_comissao=valor_comissao_consultor,
                                percentual_comissao=percentual_consultor,
                                status='pendente',
                                observacoes=f'Parcela {i}/{venda.quantidade_parcelas} - Escala: R$ {faturamento_mensal_consultor:.2f} faturado → {percentual_consultor}% - Aguardando pagamento'
                            )
                            comissoes_criadas_total['parcelas_consultor'].append(comissao_consultor)
                        
                        if i <= 3:  # Log apenas das 3 primeiras
                            print(f"   ✅ Parcela {i}: R$ {venda.valor_parcela:.2f} - Vencimento: {data_venc.strftime('%d/%m/%Y')}")
                            print(f"      → Captador: R$ {valor_comissao_captador:.2f} | Consultor: R$ {valor_comissao_consultor:.2f}")
                        elif i == venda.quantidade_parcelas:
                            print(f"   ... (parcelas intermediárias omitidas)")
                            print(f"   ✅ Parcela {i}: R$ {venda.valor_parcela:.2f} - Vencimento: {data_venc.strftime('%d/%m/%Y')}")
                    
                    print(f"\n   📊 RESUMO DAS COMISSÕES FUTURAS:")
                    print(f"   - Parcelas Captador: {len(comissoes_criadas_total['parcelas_captador'])} comissões criadas")
                    print(f"   - Parcelas Consultor: {len(comissoes_criadas_total['parcelas_consultor'])} comissões criadas")
                    
                    # Total de comissões a receber (se todas parcelas forem pagas)
                    total_captador_futuro = sum(c.valor_comissao for c in comissoes_criadas_total['parcelas_captador'])
                    total_consultor_futuro = sum(c.valor_comissao for c in comissoes_criadas_total['parcelas_consultor'])
                    print(f"   - Total Futuro Captador: R$ {total_captador_futuro:.2f}")
                    print(f"   - Total Futuro Consultor: R$ {total_consultor_futuro:.2f}")
                
                print("\n" + "="*80)
                print("✅ COMISSÕES CRIADAS COM SUCESSO!")
                print("="*80)
                
                # Atualiza pré-venda
                pre_venda.converter_em_venda()
                
                print(f"\n✅ VENDA CRIADA COM SUCESSO! ID: {venda.id}")
                print("="*80)
                
                # Redireciona para página de confirmação
                return redirect('vendas:confirmacao_venda', venda_id=venda.id)
                
        except Exception as e:
            print(f"❌ ERRO AO CADASTRAR VENDA: {str(e)}")
            messages.error(request, f'Erro ao cadastrar venda: {str(e)}')
            import traceback
            traceback.print_exc()  # Log do erro completo
            print("="*80)
    
    # Busca serviços disponíveis
    servicos = Servico.objects.filter(ativo=True)
    
    # Busca consultores (usuários do grupo comercial1 ou Admin)
    from django.contrib.auth.models import Group
    from accounts.models import User
    
    grupo_consultores = Group.objects.filter(name__in=['comercial1', 'admin', 'Admin']).first()
    if grupo_consultores:
        consultores = grupo_consultores.user_set.filter(is_active=True)
    else:
        consultores = User.objects.filter(is_staff=True, is_active=True)
    
    context = {
        'pre_venda': pre_venda,
        'servicos': servicos,
        'consultores': consultores,
        'formas_pagamento': Venda.FORMA_PAGAMENTO_CHOICES,
        'tipos_documento': DocumentoVenda.TIPO_DOCUMENTO_CHOICES,
        'dados_iniciais': dados_iniciais,
    }
    
    return render(request, 'vendas/cadastro_venda_form_new.html', context)


@login_required
@user_passes_test(is_consultor_or_admin)
def exibir_pix_entrada(request, venda_id):
    """Exibe QR Code e Copia e Cola do PIX da entrada"""
    venda = get_object_or_404(Venda, id=venda_id)
    from financeiro.models import PixEntrada
    
    pix_entrada = PixEntrada.objects.filter(venda=venda).order_by('-data_criacao').first()
    
    if not pix_entrada:
        messages.warning(request, 'Nenhum PIX de entrada encontrado para esta venda.')
        return redirect('vendas:detalhes_venda', venda_id=venda_id)
    
    context = {
        'venda': venda,
        'pix_entrada': pix_entrada,
    }
    
    return render(request, 'vendas/exibir_pix_entrada.html', context)


@login_required
@user_passes_test(is_consultor_or_admin)
def confirmacao_venda(request, venda_id):
    """Página de confirmação após cadastro completo da venda"""
    venda = get_object_or_404(
        Venda.objects.select_related('cliente', 'servico', 'consultor', 'captador'),
        id=venda_id
    )
    
    print("="*80)
    print(f"📋 CONFIRMAÇÃO DE VENDA #{venda_id}")
    print(f"Valor da Entrada: R$ {venda.valor_entrada}")
    
    # Busca PIX de entrada se existir
    from financeiro.models import PixEntrada
    pix_entrada = PixEntrada.objects.filter(venda=venda).order_by('-data_criacao').first()
    
    if pix_entrada:
        print(f"✅ PIX Encontrado: ID={pix_entrada.id}")
        print(f"   ASAAS Payment ID: {pix_entrada.asaas_payment_id}")
        print(f"   Valor: R$ {pix_entrada.valor}")
        print(f"   PIX Code: {pix_entrada.pix_code[:50]}..." if len(pix_entrada.pix_code) > 50 else f"   PIX Code: {pix_entrada.pix_code}")
        print(f"   QR Code URL: {pix_entrada.pix_qr_code_url[:50]}..." if len(pix_entrada.pix_qr_code_url) > 50 else f"   QR Code URL: {pix_entrada.pix_qr_code_url}")
        print(f"   Status: {pix_entrada.status_pagamento}")
        print(f"   Data Criação: {pix_entrada.data_criacao}")
    else:
        print("⚠️ NENHUM PIX ENCONTRADO NO BANCO DE DADOS")
        # Busca todos os PIX para debug
        todos_pix = PixEntrada.objects.filter(venda=venda)
        print(f"   Total de PIX para esta venda: {todos_pix.count()}")
        for pix in todos_pix:
            print(f"   - PIX ID={pix.id}, ASAAS={pix.asaas_payment_id}, Criado em={pix.data_criacao}")
    
    # Busca pré-venda relacionada (Cliente tem OneToOne com Lead, usar .lead)
    pre_venda = None
    if hasattr(venda.cliente, 'lead') and venda.cliente.lead:
        pre_venda = PreVenda.objects.filter(lead=venda.cliente.lead).first()
    
    print("="*80)
    
    context = {
        'venda': venda,
        'pix_entrada': pix_entrada,
        'pre_venda': pre_venda,
    }
    
    print(f"📤 Contexto sendo enviado para o template:")
    print(f"   venda: {venda}")
    print(f"   pix_entrada: {pix_entrada}")
    print(f"   pix_entrada.pix_code presente: {bool(pix_entrada.pix_code) if pix_entrada else False}")
    print("="*80)
    
    return render(request, 'vendas/confirmacao_venda.html', context)


@login_required
@user_passes_test(is_consultor_or_admin)
def listar_vendas(request):
    """Lista todas as vendas com filtros"""
    vendas = Venda.objects.select_related('cliente', 'servico', 'consultor', 'captador').order_by('-data_venda')
    
    # Filtros
    status = request.GET.get('status')
    if status:
        vendas = vendas.filter(status=status)
    
    data_inicio = request.GET.get('data_inicio')
    if data_inicio:
        vendas = vendas.filter(data_venda__gte=data_inicio)
    
    data_fim = request.GET.get('data_fim')
    if data_fim:
        vendas = vendas.filter(data_venda__lte=data_fim)
    
    context = {
        'vendas': vendas,
        'status_choices': Venda.STATUS_CHOICES,
    }
    
    return render(request, 'vendas/lista_vendas.html', context)


@login_required
@user_passes_test(is_consultor_or_admin)
def detalhes_venda(request, venda_id):
    """Exibe detalhes completos de uma venda"""
    venda = get_object_or_404(
        Venda.objects.select_related('cliente', 'servico', 'consultor', 'captador'),
        id=venda_id
    )
    
    documentos = DocumentoVenda.objects.filter(venda=venda).order_by('-data_upload')
    parcelas = Parcela.objects.filter(venda=venda).order_by('numero_parcela')
    
    context = {
        'venda': venda,
        'documentos': documentos,
        'parcelas': parcelas,
    }
    
    return render(request, 'vendas/detalhes_venda.html', context)


@login_required
@user_passes_test(lambda u: u.is_staff or u.groups.filter(name='Administradores').exists())
def gerar_comissoes_entradas_pagas(request):
    """
    View administrativa para gerar comissões retroativas de entradas pagas.
    
    Busca vendas com:
    - status_pagamento_entrada='PAGO'
    - valor_entrada > 0
    - Sem comissões do tipo CONSULTOR_ENTRADA ou CAPTADOR_ENTRADA
    
    E cria as comissões usando o CommissionService.
    """
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.db.models import Q
    
    # Buscar vendas com entrada paga
    vendas_entrada_paga = Venda.objects.filter(
        status_pagamento_entrada='PAGO',
        valor_entrada__gt=0
    ).select_related('captador', 'consultor', 'cliente')
    
    # Para cada venda, verificar se já tem comissões de entrada
    vendas_sem_comissao = []
    
    for venda in vendas_entrada_paga:
        # Verificar se já existe comissão de entrada (captador ou consultor)
        tem_comissao = Comissao.objects.filter(
            venda=venda,
            tipo_comissao__in=['CAPTADOR_ENTRADA', 'CONSULTOR_ENTRADA']
        ).exists()
        
        if not tem_comissao:
            vendas_sem_comissao.append(venda)
    
    if not vendas_sem_comissao:
        messages.success(request, '✅ Todas as entradas pagas já possuem comissões!')
        return redirect('vendas:painel_metricas_consultor')
    
    # Criar comissões
    total_criadas = 0
    total_erros = 0
    detalhes = []
    
    for venda in vendas_sem_comissao:
        try:
            # Criar comissões usando o serviço
            comissoes = CommissionService.criar_comissao_entrada_venda(venda)
            
            venda_info = f'Venda #{venda.id} - R$ {venda.valor_entrada:.2f}'
            
            if comissoes.get('captador'):
                detalhes.append(f'✅ {venda_info} - Captador: R$ {comissoes["captador"].valor_comissao:.2f}')
                total_criadas += 1
            
            if comissoes.get('consultor'):
                detalhes.append(f'✅ {venda_info} - Consultor: R$ {comissoes["consultor"].valor_comissao:.2f}')
                total_criadas += 1
            
        except Exception as e:
            total_erros += 1
            detalhes.append(f'❌ Venda #{venda.id}: Erro - {str(e)}')
    
    # Mensagens de sucesso
    if total_criadas > 0:
        messages.success(request, f'✅ {total_criadas} comissões criadas com sucesso!')
        for detalhe in detalhes[:10]:  # Mostrar primeiras 10
            messages.info(request, detalhe)
    
    if total_erros > 0:
        messages.error(request, f'❌ {total_erros} erros ao criar comissões')
    
    return redirect('vendas:painel_metricas_consultor')


@login_required
@user_passes_test(is_consultor_or_admin) 
def detalhes_pre_venda(request, pre_venda_id):
    """Exibe detalhes de uma pré-venda"""
    pre_venda = get_object_or_404(
        PreVenda.objects.select_related('lead', 'atendente', 'motivo_principal', 'perfil_emocional'),
        id=pre_venda_id
    )
    
    context = {
        'pre_venda': pre_venda,
    }
    
    return render(request, 'vendas/detalhes_pre_venda.html', context)
