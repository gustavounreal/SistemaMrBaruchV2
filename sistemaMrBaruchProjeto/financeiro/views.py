from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from financeiro.models import (
    Parcela, ClienteAsaas, Renegociacao, 
    HistoricoContatoRetencao, PixEntrada, PixLevantamento
)
from vendas.models import Venda
from core.asaas_service import asaas_service
import logging

logger = logging.getLogger(__name__)


@login_required
def dashboard_financeiro(request):
    """Dashboard principal do módulo Financeiro/Retenção"""
    hoje = timezone.now().date()
    
    # Estatísticas Gerais
    total_inadimplentes = Parcela.objects.filter(
        status='vencida',
        data_vencimento__lt=hoje - timedelta(days=3)
    ).count()
    
    total_valor_inadimplencia = Parcela.objects.filter(
        status='vencida',
        data_vencimento__lt=hoje - timedelta(days=3)
    ).aggregate(total=Sum('valor'))['total'] or 0
    
    # Entradas do Mês
    primeiro_dia_mes = hoje.replace(day=1)
    entradas_mes = Parcela.objects.filter(
        status='paga',
        data_pagamento__gte=primeiro_dia_mes,
        data_pagamento__lte=hoje
    ).aggregate(total=Sum('valor'))['total'] or 0
    
    # Renegociações Ativas
    renegociacoes_ativas = Renegociacao.objects.filter(
        status__in=['em_negociacao', 'aceita']
    ).count()
    
    context = {
        'total_inadimplentes': total_inadimplentes,
        'total_valor_inadimplencia': total_valor_inadimplencia,
        'entradas_mes': entradas_mes,
        'renegociacoes_ativas': renegociacoes_ativas,
    }
    
    return render(request, 'financeiro/dashboard.html', context)


@login_required
def painel_retencao(request):
    """Painel de Retenção - visão geral de inadimplentes"""
    hoje = timezone.now().date()
    data_corte = hoje - timedelta(days=3)
    
    # Parcelas vencidas há mais de 3 dias
    parcelas_vencidas = Parcela.objects.filter(
        status='vencida',
        data_vencimento__lt=data_corte
    ).select_related('venda', 'venda__cliente', 'venda__cliente__lead').order_by('data_vencimento')
    
    # Agrupar por venda
    vendas_inadimplentes = {}
    for parcela in parcelas_vencidas:
        venda_id = parcela.venda.id
        if venda_id not in vendas_inadimplentes:
            vendas_inadimplentes[venda_id] = {
                'venda': parcela.venda,
                'parcelas': [],
                'valor_total': Decimal('0'),
                'dias_atraso': 0,
                'ultimo_contato': None,
            }
        vendas_inadimplentes[venda_id]['parcelas'].append(parcela)
        vendas_inadimplentes[venda_id]['valor_total'] += parcela.valor
        dias_atraso = (hoje - parcela.data_vencimento).days
        if dias_atraso > vendas_inadimplentes[venda_id]['dias_atraso']:
            vendas_inadimplentes[venda_id]['dias_atraso'] = dias_atraso
    
    # Buscar último contato para cada venda
    for venda_id, dados in vendas_inadimplentes.items():
        ultimo_contato = HistoricoContatoRetencao.objects.filter(
            venda_id=venda_id
        ).order_by('-data_contato').first()
        dados['ultimo_contato'] = ultimo_contato
    
    context = {
        'vendas_inadimplentes': vendas_inadimplentes.values(),
        'total_inadimplentes': len(vendas_inadimplentes),
        'data_corte': data_corte,
    }
    
    return render(request, 'financeiro/retencao/painel.html', context)


@login_required
def lista_inadimplentes(request):
    """Lista detalhada de inadimplentes com filtros"""
    hoje = timezone.now().date()
    data_corte = hoje - timedelta(days=3)
    
    # Filtros
    filtro_dias = request.GET.get('dias', 'todos')
    filtro_valor_min = request.GET.get('valor_min', '')
    filtro_valor_max = request.GET.get('valor_max', '')
    
    parcelas = Parcela.objects.filter(
        status='vencida',
        data_vencimento__lt=data_corte
    ).select_related('venda', 'venda__cliente', 'venda__cliente__lead')
    
    # Aplicar filtros
    if filtro_dias == '3-7':
        parcelas = parcelas.filter(data_vencimento__gte=hoje - timedelta(days=7))
    elif filtro_dias == '8-15':
        parcelas = parcelas.filter(
            data_vencimento__lt=hoje - timedelta(days=7),
            data_vencimento__gte=hoje - timedelta(days=15)
        )
    elif filtro_dias == '16-30':
        parcelas = parcelas.filter(
            data_vencimento__lt=hoje - timedelta(days=15),
            data_vencimento__gte=hoje - timedelta(days=30)
        )
    elif filtro_dias == 'mais_30':
        parcelas = parcelas.filter(data_vencimento__lt=hoje - timedelta(days=30))
    
    if filtro_valor_min:
        parcelas = parcelas.filter(valor__gte=Decimal(filtro_valor_min))
    
    if filtro_valor_max:
        parcelas = parcelas.filter(valor__lte=Decimal(filtro_valor_max))
    
    # Agrupar parcelas por venda
    vendas_dict = {}
    for parcela in parcelas.order_by('data_vencimento'):
        venda_id = parcela.venda.id
        if venda_id not in vendas_dict:
            vendas_dict[venda_id] = {
                'venda': parcela.venda,
                'parcelas': [],
                'valor_total': Decimal('0.00'),
                'dias_atraso': 0
            }
        
        vendas_dict[venda_id]['parcelas'].append(parcela)
        vendas_dict[venda_id]['valor_total'] += parcela.valor
        
        # Calcular dias de atraso (usando a parcela mais antiga)
        dias = (hoje - parcela.data_vencimento).days
        if dias > vendas_dict[venda_id]['dias_atraso']:
            vendas_dict[venda_id]['dias_atraso'] = dias
    
    vendas_inadimplentes = list(vendas_dict.values())
    
    context = {
        'vendas_inadimplentes': vendas_inadimplentes,
        'total_inadimplentes': len(vendas_inadimplentes),
        'filtro_dias': filtro_dias,
        'filtro_valor_min': filtro_valor_min,
        'filtro_valor_max': filtro_valor_max,
    }
    
    return render(request, 'financeiro/retencao/lista_inadimplentes.html', context)


@login_required
def renegociar_divida(request, venda_id):
    """Formulário para renegociar dívida"""
    venda = get_object_or_404(Venda, id=venda_id)
    
    # Buscar parcelas vencidas ou em aberto da venda
    parcelas_pendentes = Parcela.objects.filter(
        venda=venda,
        status__in=['aberta', 'vencida']
    ).order_by('numero_parcela')
    
    if request.method == 'POST':
        # Processar renegociação
        tipo_renegociacao = request.POST.get('tipo_renegociacao')
        percentual_desconto = Decimal(request.POST.get('percentual_desconto', '0'))
        numero_novas_parcelas = int(request.POST.get('numero_novas_parcelas', '1'))
        data_primeira_parcela = request.POST.get('data_primeira_parcela')
        observacoes = request.POST.get('observacoes', '')
        
        # IDs das parcelas selecionadas para renegociação
        parcelas_ids = request.POST.getlist('parcelas_selecionadas')
        parcelas_selecionadas = parcelas_pendentes.filter(id__in=parcelas_ids)
        
        # Calcular valores
        valor_total_divida = sum(p.valor for p in parcelas_selecionadas)
        valor_desconto = (valor_total_divida * percentual_desconto) / 100
        valor_novo_total = valor_total_divida - valor_desconto
        
        # Criar renegociação
        renegociacao = Renegociacao.objects.create(
            venda=venda,
            tipo_renegociacao=tipo_renegociacao,
            valor_total_divida=valor_total_divida,
            valor_desconto=valor_desconto,
            percentual_desconto=percentual_desconto,
            valor_novo_total=valor_novo_total,
            numero_novas_parcelas=numero_novas_parcelas,
            data_primeira_parcela=datetime.strptime(data_primeira_parcela, '%Y-%m-%d').date(),
            responsavel=request.user,
            observacoes=observacoes,
            status='em_negociacao'
        )
        
        # Associar parcelas
        renegociacao.parcelas_original.set(parcelas_selecionadas)
        
        messages.success(request, 'Renegociação criada com sucesso! Aguardando aprovação do cliente.')
        return redirect('financeiro:historico_negociacoes', venda_id=venda.id)
    
    context = {
        'venda': venda,
        'parcelas_pendentes': parcelas_pendentes,
        'valor_total_pendente': sum(p.valor for p in parcelas_pendentes),
    }
    
    return render(request, 'financeiro/retencao/renegociar.html', context)


@login_required
def historico_negociacoes(request, venda_id):
    """Histórico de renegociações de uma venda"""
    venda = get_object_or_404(Venda, id=venda_id)
    
    renegociacoes = Renegociacao.objects.filter(
        venda=venda
    ).prefetch_related('parcelas_original').order_by('-data_criacao')
    
    contatos = HistoricoContatoRetencao.objects.filter(
        venda=venda
    ).select_related('responsavel').order_by('-data_contato')
    
    context = {
        'venda': venda,
        'renegociacoes': renegociacoes,
        'contatos': contatos,
    }
    
    return render(request, 'financeiro/retencao/historico.html', context)


@login_required
def painel_entradas(request):
    """Painel de entradas PIX (pagamento inicial de vendas)"""
    hoje = timezone.now().date()
    
    # Estatísticas do mês atual
    primeiro_dia_mes = hoje.replace(day=1)
    
    # USAR PixEntrada (entrada inicial), NÃO Parcela
    entradas_mes = PixEntrada.objects.filter(
        status_pagamento='pago',
        data_pagamento__gte=primeiro_dia_mes,
        data_pagamento__lte=timezone.now()
    ).aggregate(
        total=Sum('valor'),
        quantidade=Count('id')
    )
    
    # Entradas PIX pagas hoje
    entradas_hoje = PixEntrada.objects.filter(
        status_pagamento='pago',
        data_pagamento__date=hoje
    ).aggregate(
        total=Sum('valor'),
        quantidade=Count('id')
    )
    
    # Entradas PIX pendentes
    entradas_pendentes = PixEntrada.objects.filter(
        status_pagamento='pendente'
    ).aggregate(
        total=Sum('valor'),
        quantidade=Count('id')
    )
    
    context = {
        'entradas_mes_valor': entradas_mes['total'] or 0,
        'entradas_mes_qtd': entradas_mes['quantidade'] or 0,
        'entradas_hoje_valor': entradas_hoje['total'] or 0,
        'entradas_hoje_qtd': entradas_hoje['quantidade'] or 0,
        'entradas_pendentes_valor': entradas_pendentes['total'] or 0,
        'entradas_pendentes_qtd': entradas_pendentes['quantidade'] or 0,
    }
    
    return render(request, 'financeiro/entradas/painel.html', context)


@login_required
def entradas_diario(request):
    """Relatório de entradas PIX do dia"""
    data_str = request.GET.get('data', timezone.now().date().strftime('%Y-%m-%d'))
    data_filtro = datetime.strptime(data_str, '%Y-%m-%d').date()
    
    # USAR PixEntrada (entrada inicial), NÃO Parcela
    entradas = PixEntrada.objects.filter(
        status_pagamento='pago',
        data_pagamento__date=data_filtro
    ).select_related('venda', 'venda__cliente', 'venda__cliente__lead').order_by('-data_pagamento')
    
    total = entradas.aggregate(Sum('valor'))['valor__sum'] or 0
    
    context = {
        'entradas': entradas,
        'data': data_filtro,
        'total': total,
        'quantidade': entradas.count(),
    }
    
    return render(request, 'financeiro/entradas/diario.html', context)


@login_required
def entradas_semanal(request):
    """Relatório de entradas PIX da semana"""
    hoje = timezone.now().date()
    inicio_semana = hoje - timedelta(days=hoje.weekday())
    fim_semana = inicio_semana + timedelta(days=6)
    
    # USAR PixEntrada (entrada inicial), NÃO Parcela
    entradas = PixEntrada.objects.filter(
        status_pagamento='pago',
        data_pagamento__date__gte=inicio_semana,
        data_pagamento__date__lte=fim_semana
    ).select_related('venda', 'venda__cliente', 'venda__cliente__lead').order_by('-data_pagamento')
    
    total = entradas.aggregate(Sum('valor'))['valor__sum'] or 0
    
    context = {
        'entradas': entradas,
        'data_inicio': inicio_semana,
        'data_fim': fim_semana,
        'total': total,
        'quantidade': entradas.count(),
    }
    
    return render(request, 'financeiro/entradas/semanal.html', context)


@login_required
def entradas_mensal(request):
    """Relatório de entradas PIX do mês"""
    hoje = timezone.now().date()
    mes = int(request.GET.get('mes', hoje.month))
    ano = int(request.GET.get('ano', hoje.year))
    
    primeiro_dia = datetime(ano, mes, 1).date()
    if mes == 12:
        ultimo_dia = datetime(ano + 1, 1, 1).date() - timedelta(days=1)
    else:
        ultimo_dia = datetime(ano, mes + 1, 1).date() - timedelta(days=1)
    
    # USAR PixEntrada (entrada inicial), NÃO Parcela
    entradas = PixEntrada.objects.filter(
        status_pagamento='pago',
        data_pagamento__date__gte=primeiro_dia,
        data_pagamento__date__lte=ultimo_dia
    ).select_related('venda', 'venda__cliente', 'venda__cliente__lead').order_by('-data_pagamento')
    
    total = entradas.aggregate(Sum('valor'))['valor__sum'] or 0
    
    context = {
        'entradas': entradas,
        'mes': mes,
        'ano': ano,
        'data_inicio': primeiro_dia,
        'data_fim': ultimo_dia,
        'total': total,
        'quantidade': entradas.count(),
    }
    
    return render(request, 'financeiro/entradas/mensal.html', context)


@login_required
def lista_parcelas(request):
    """Lista todas as parcelas com filtros"""
    from django.db.models import Sum, Count, Q
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    from datetime import datetime
    
    status_filtro = request.GET.get('status', 'todas')
    asaas_filtro = request.GET.get('asaas', 'todos')
    busca = request.GET.get('busca', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    
    parcelas = Parcela.objects.all().select_related('venda', 'venda__cliente', 'venda__cliente__lead')
    
    # Filtro de status
    if status_filtro != 'todas':
        parcelas = parcelas.filter(status=status_filtro)
    
    # Filtro de ASAAS
    if asaas_filtro == 'criado':
        parcelas = parcelas.exclude(id_asaas__isnull=True).exclude(id_asaas='')
    elif asaas_filtro == 'pendente':
        parcelas = parcelas.filter(Q(id_asaas__isnull=True) | Q(id_asaas=''))
    
    # Filtro de busca por cliente
    if busca:
        parcelas = parcelas.filter(
            Q(venda__cliente__lead__nome_completo__icontains=busca) |
            Q(venda__cliente__lead__telefone__icontains=busca)
        )
    
    # Filtro de data
    if data_inicio:
        parcelas = parcelas.filter(data_vencimento__gte=data_inicio)
    if data_fim:
        parcelas = parcelas.filter(data_vencimento__lte=data_fim)
    
    parcelas = parcelas.order_by('-data_vencimento')
    
    # Paginação
    paginator = Paginator(parcelas, 20)  # 20 parcelas por página
    page = request.GET.get('page', 1)
    
    try:
        parcelas_paginadas = paginator.page(page)
    except PageNotAnInteger:
        parcelas_paginadas = paginator.page(1)
    except EmptyPage:
        parcelas_paginadas = paginator.page(paginator.num_pages)
    
    # Calcular estatísticas
    todas_parcelas = Parcela.objects.all()
    
    pagas = todas_parcelas.filter(status='paga').aggregate(
        total=Count('id'),
        valor=Sum('valor')
    )
    
    abertas = todas_parcelas.filter(status='aberta').aggregate(
        total=Count('id'),
        valor=Sum('valor')
    )
    
    vencidas = todas_parcelas.filter(status='vencida').aggregate(
        total=Count('id'),
        valor=Sum('valor')
    )
    
    context = {
        'parcelas': parcelas_paginadas,
        'status_filtro': status_filtro,
        'asaas_filtro': asaas_filtro,
        'busca': busca,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'total_pagas': pagas['total'] or 0,
        'valor_pagas': pagas['valor'] or 0,
        'total_abertas': abertas['total'] or 0,
        'valor_abertas': abertas['valor'] or 0,
        'total_vencidas': vencidas['total'] or 0,
        'valor_vencidas': vencidas['valor'] or 0,
    }
    
    return render(request, 'financeiro/parcelas/lista.html', context)


@login_required
def detalhes_parcela(request, parcela_id):
    """Detalhes de uma parcela específica"""
    from datetime import date
    
    parcela = get_object_or_404(
        Parcela.objects.select_related('venda', 'venda__cliente', 'venda__cliente__lead', 'venda__servico', 'venda__consultor'), 
        id=parcela_id
    )
    
    # Calcular informações adicionais da venda
    venda = parcela.venda
    todas_parcelas = venda.parcelas.all()
    parcelas_pagas = todas_parcelas.filter(status='paga').count()
    valor_pago = sum(p.valor for p in todas_parcelas.filter(status='paga'))
    valor_pendente = venda.valor_total - valor_pago
    percentual_pago = (valor_pago / venda.valor_total * 100) if venda.valor_total > 0 else 0
    
    # Adicionar informações à venda
    venda.parcelas_pagas = parcelas_pagas
    venda.valor_pago = valor_pago
    venda.valor_pendente = valor_pendente
    venda.percentual_pago = percentual_pago
    
    # Calcular dias de atraso se vencida
    if parcela.status == 'vencida' and not parcela.data_pagamento:
        dias_atraso = (date.today() - parcela.data_vencimento).days
        parcela.dias_atraso = dias_atraso
    
    context = {
        'parcela': parcela,
        'hoje': date.today(),
    }
    
    return render(request, 'financeiro/parcelas/detalhes.html', context)


@login_required
def marcar_parcela_paga(request, parcela_id):
    """Marca uma parcela como paga manualmente"""
    if request.method == 'POST':
        parcela = get_object_or_404(Parcela, id=parcela_id)
        data_pagamento = request.POST.get('data_pagamento', timezone.now().date())
        
        parcela.status = 'paga'
        parcela.data_pagamento = data_pagamento
        parcela.save()
        
        messages.success(request, f'Parcela {parcela.numero_parcela} marcada como paga.')
        return redirect('financeiro:detalhes_parcela', parcela_id=parcela.id)
    
    return redirect('financeiro:lista_parcelas')


@login_required
def editar_data_parcela(request, parcela_id):
    """Edita a data de vencimento de uma parcela e sincroniza com ASAAS"""
    if request.method == 'POST':
        parcela = get_object_or_404(Parcela, id=parcela_id)
        nova_data = request.POST.get('nova_data_vencimento')
        
        if nova_data:
            try:
                # Converte a string para date
                nova_data_obj = datetime.strptime(nova_data, '%Y-%m-%d').date()
                data_antiga = parcela.data_vencimento
                
                # Se a parcela tem id_asaas, atualiza também no ASAAS
                if parcela.id_asaas:
                    try:
                        # Prepara dados para atualização no ASAAS
                        dados_atualizacao = {
                            'dueDate': nova_data_obj.strftime('%Y-%m-%d')
                        }
                        
                        # Atualiza no ASAAS
                        resultado_asaas = asaas_service.atualizar_cobranca(
                            parcela.id_asaas, 
                            dados_atualizacao
                        )
                        
                        if resultado_asaas and 'errors' not in resultado_asaas:
                            logger.info(f"Data da cobrança {parcela.id_asaas} atualizada no ASAAS")
                            messages.success(request, 'Data atualizada no ASAAS com sucesso!')
                        else:
                            erro_msg = resultado_asaas.get('errors', [{}])[0].get('description', 'Erro desconhecido') if resultado_asaas else 'Sem resposta do ASAAS'
                            logger.error(f"Erro ao atualizar data no ASAAS: {erro_msg}")
                            messages.warning(request, f'Data será atualizada apenas no sistema. Erro ASAAS: {erro_msg}')
                            
                    except Exception as e:
                        logger.error(f"Exceção ao atualizar data no ASAAS: {str(e)}")
                        messages.warning(request, f'Data será atualizada apenas no sistema. Erro na comunicação com ASAAS.')
                
                # Atualiza a data no sistema local
                parcela.data_vencimento = nova_data_obj
                
                # Atualiza o status baseado na nova data
                hoje = timezone.now().date()
                if parcela.status != 'paga':
                    if nova_data_obj < hoje:
                        parcela.status = 'vencida'
                    else:
                        parcela.status = 'aberta'
                
                parcela.save()
                
                messages.success(
                    request, 
                    f'Data de vencimento atualizada de {data_antiga.strftime("%d/%m/%Y")} para {nova_data_obj.strftime("%d/%m/%Y")}'
                )
            except ValueError:
                messages.error(request, 'Data inválida!')
        else:
            messages.error(request, 'Data não informada!')
        
        return redirect('financeiro:detalhes_parcela', parcela_id=parcela.id)
    
    return redirect('financeiro:lista_parcelas')


@login_required
def imprimir_boleto_parcela(request, parcela_id):
    """Redireciona para o boleto real do ASAAS ou busca a URL se não estiver salva"""
    parcela = get_object_or_404(Parcela, id=parcela_id)
    
    # Se já temos a URL do boleto salva, redireciona direto
    if parcela.url_boleto:
        return redirect(parcela.url_boleto)
    
    # Se não temos a URL mas temos o ID do ASAAS, busca na API
    if parcela.id_asaas:
        try:
            dados_asaas = asaas_service.obter_cobranca(parcela.id_asaas)
            
            if dados_asaas and 'bankSlipUrl' in dados_asaas:
                # Salva a URL para uso futuro
                parcela.url_boleto = dados_asaas['bankSlipUrl']
                
                # Salva também o código de barras se disponível
                if 'identificationField' in dados_asaas:
                    parcela.codigo_barras = dados_asaas['identificationField']
                
                parcela.save()
                
                logger.info(f"URL do boleto obtida e salva para parcela {parcela_id}")
                return redirect(parcela.url_boleto)
            else:
                logger.error(f"Boleto não encontrado no ASAAS para parcela {parcela_id}")
                messages.error(request, "Boleto não encontrado no ASAAS.")
        except Exception as e:
            logger.error(f"Erro ao buscar boleto no ASAAS para parcela {parcela_id}: {str(e)}")
            messages.error(request, f"Erro ao buscar boleto no ASAAS: {str(e)}")
    else:
        messages.error(request, "Esta parcela ainda não foi sincronizada com o ASAAS.")
    
    return redirect('financeiro:detalhes_parcela', parcela_id=parcela.id)


@login_required
def relatorio_inadimplencia(request):
    """Relatório consolidado de inadimplência"""
    hoje = timezone.now().date()
    
    # Inadimplência por período
    inadimplencia_3_7 = Parcela.objects.filter(
        status='vencida',
        data_vencimento__gte=hoje - timedelta(days=7),
        data_vencimento__lt=hoje - timedelta(days=3)
    ).aggregate(total=Sum('valor'), qtd=Count('id'))
    
    inadimplencia_8_15 = Parcela.objects.filter(
        status='vencida',
        data_vencimento__gte=hoje - timedelta(days=15),
        data_vencimento__lt=hoje - timedelta(days=7)
    ).aggregate(total=Sum('valor'), qtd=Count('id'))
    
    inadimplencia_16_30 = Parcela.objects.filter(
        status='vencida',
        data_vencimento__gte=hoje - timedelta(days=30),
        data_vencimento__lt=hoje - timedelta(days=15)
    ).aggregate(total=Sum('valor'), qtd=Count('id'))
    
    inadimplencia_mais_30 = Parcela.objects.filter(
        status='vencida',
        data_vencimento__lt=hoje - timedelta(days=30)
    ).aggregate(total=Sum('valor'), qtd=Count('id'))
    
    context = {
        'inadimplencia_3_7': inadimplencia_3_7,
        'inadimplencia_8_15': inadimplencia_8_15,
        'inadimplencia_16_30': inadimplencia_16_30,
        'inadimplencia_mais_30': inadimplencia_mais_30,
    }
    
    return render(request, 'financeiro/relatorios/inadimplencia.html', context)


# ============= Funções auxiliares (mantidas da versão original) =============

from financeiro.models import ClienteAsaas
from core.asaas_service import asaas_service
import logging

logger = logging.getLogger(__name__)

def criar_cliente_asaas(lead):
    """Cria um cliente no Asaas e salva na tabela ClienteAsaas"""
    logger.info(f"Iniciando criação de cliente ASAAS para lead {lead.id}")
    
    # Verificar se já existe um cliente ASAAS para este lead
    cliente_existente = ClienteAsaas.objects.filter(lead=lead).first()
    if cliente_existente:
        logger.info(f"Cliente ASAAS já existe para lead {lead.id}: {cliente_existente.asaas_customer_id}")
        return cliente_existente
    
    # Validar CPF/CNPJ obrigatório
    if not lead.cpf_cnpj:
        logger.error(f"Lead {lead.id} sem CPF/CNPJ")
        raise ValueError("CPF ou CNPJ é obrigatório para criar um cliente no Asaas.")
    
    # Preparar dados do cliente
    cliente_data = {
        'nome': lead.nome_completo,
        'email': lead.email if lead.email else 'naotem@email.com',  # Email obrigatório no ASAAS
        'telefone': lead.telefone if lead.telefone else '',
        'cpf_cnpj': lead.cpf_cnpj, 
    }
    
    logger.info(f"Enviando dados para ASAAS - Lead {lead.id}: Nome={cliente_data['nome']}, CPF={cliente_data['cpf_cnpj']}")
    
    # Criar cliente no ASAAS
    response = asaas_service.criar_cliente(cliente_data)
    
    if response and 'id' in response:
        # Criar registro na tabela ClienteAsaas
        cliente_asaas = ClienteAsaas.objects.create(
            lead=lead,
            asaas_customer_id=response['id']
        )
        logger.info(f"Cliente ASAAS criado com sucesso: {response['id']} para lead {lead.id}")
        return cliente_asaas
    else:
        error_msg = "Erro ao criar cliente no ASAAS"
        if response and 'errors' in response:
            error_msg = response['errors'][0].get('description', error_msg)
        logger.error(f"Falha ao criar cliente ASAAS para lead {lead.id}: {error_msg}")
        logger.error(f"Response completa do ASAAS: {response}")
        raise ValueError(error_msg)


@login_required
def lista_clientes_aptos_liminar(request):
    """
    Lista clientes aptos para envio de liminar baseado nos critérios:
    - 10 dias de contrato assinado
    - Mínimo R$500,00 de pagamento (soma entrada + parcelas pagas)
    - Liminar ainda não iniciada ou concluída
    """
    from django.http import HttpResponse
    import csv
    from django.db.models import Sum, F
    
    hoje = timezone.now().date()
    
    # Obter filtros de data
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    
    # Se não houver filtros, usar data padrão (10 dias atrás)
    if not data_inicio and not data_fim:
        data_limite_assinatura = hoje - timedelta(days=10)
        vendas_elegiveis = Venda.objects.filter(
            contrato_assinado=True,
            data_assinatura__isnull=False,
            data_assinatura__date__lte=data_limite_assinatura,
            liminar_entregue=False
        )
    else:
        # Aplicar filtros de data
        vendas_elegiveis = Venda.objects.filter(
            contrato_assinado=True,
            data_assinatura__isnull=False,
            liminar_entregue=False
        )
        
        if data_inicio:
            try:
                data_inicio_obj = datetime.strptime(data_inicio, '%Y-%m-%d').date()
                vendas_elegiveis = vendas_elegiveis.filter(data_assinatura__date__gte=data_inicio_obj)
            except ValueError:
                pass
        
        if data_fim:
            try:
                data_fim_obj = datetime.strptime(data_fim, '%Y-%m-%d').date()
                vendas_elegiveis = vendas_elegiveis.filter(data_assinatura__date__lte=data_fim_obj)
            except ValueError:
                pass
    
    vendas_elegiveis = vendas_elegiveis.select_related('cliente', 'cliente__lead').prefetch_related('parcelas')
    
    # Filtrar por pagamento mínimo de R$500
    clientes_aptos = []
    for venda in vendas_elegiveis:
        # Somar valor de entrada
        valor_entrada = venda.valor_entrada if not venda.sem_entrada else Decimal('0.00')
        
        # Somar parcelas pagas
        valor_parcelas_pagas = venda.parcelas.filter(
            status='paga'
        ).aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        
        total_pago = valor_entrada + valor_parcelas_pagas
        
        # Verificar se tem pelo menos 10 dias desde assinatura E pagamento >= 500
        dias_desde_assinatura = (hoje - venda.data_assinatura.date()).days
        
        if total_pago >= Decimal('500.00') and dias_desde_assinatura >= 10:
            clientes_aptos.append({
                'venda': venda,
                'total_pago': total_pago,
                'dias_desde_assinatura': dias_desde_assinatura
            })
    
    # Verificar se é requisição de exportação
    exportar = request.GET.get('exportar', False)
    
    if exportar:
        # Criar arquivo CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="clientes_aptos_liminar_{hoje}.csv"'
        response.write('\ufeff')  # BOM para UTF-8
        
        writer = csv.writer(response, delimiter=';')
        writer.writerow(['Nome', 'CPF/CNPJ', 'Data Contratação', 'Valor Total Serviço', 'Total Pago', 'Dias desde Assinatura'])
        
        for item in clientes_aptos:
            venda = item['venda']
            writer.writerow([
                venda.cliente.lead.nome_completo,
                venda.cliente.lead.cpf_cnpj or '',
                venda.data_assinatura.strftime('%d/%m/%Y') if venda.data_assinatura else '',
                f"R$ {venda.valor_total:.2f}".replace('.', ','),
                f"R$ {item['total_pago']:.2f}".replace('.', ','),
                item['dias_desde_assinatura']
            ])
        
        return response
    
    context = {
        'clientes_aptos': clientes_aptos,
        'total_clientes': len(clientes_aptos),
        'data_consulta': hoje,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    }
    
    return render(request, 'financeiro/lista_aptos_liminar.html', context)