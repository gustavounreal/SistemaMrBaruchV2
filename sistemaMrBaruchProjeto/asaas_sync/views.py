"""
Views para visualização de dados sincronizados do Asaas
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Sum, Count, Case, When, DecimalField
from django.utils import timezone
from .models import AsaasClienteSyncronizado, AsaasCobrancaSyncronizada, AsaasSyncronizacaoLog
from .services import AsaasSyncService
import logging

logger = logging.getLogger(__name__)


@login_required
def dashboard_asaas_sync(request):
    """Dashboard principal com dados do Asaas"""
    
    # Estatísticas gerais
    total_clientes = AsaasClienteSyncronizado.objects.count()
    total_cobrancas = AsaasCobrancaSyncronizada.objects.count()
    
    # Valores
    total_recebido = AsaasCobrancaSyncronizada.objects.filter(
        status__in=['RECEIVED', 'CONFIRMED']
    ).aggregate(total=Sum('valor'))['total'] or 0
    
    total_pendente = AsaasCobrancaSyncronizada.objects.filter(
        status='PENDING'
    ).aggregate(total=Sum('valor'))['total'] or 0
    
    total_vencido = AsaasCobrancaSyncronizada.objects.filter(
        status='OVERDUE'
    ).aggregate(total=Sum('valor'))['total'] or 0
    
    # Últimas sincronizações
    ultimas_syncs = AsaasSyncronizacaoLog.objects.all()[:5]
    ultima_sync = ultimas_syncs.first()
    
    # Cobranças recentes
    cobrancas_recentes = AsaasCobrancaSyncronizada.objects.select_related('cliente').order_by('-sincronizado_em')[:10]
    
    # Cobranças por status
    cobrancas_por_status = AsaasCobrancaSyncronizada.objects.values('status').annotate(
        total=Count('id'),
        valor_total=Sum('valor')
    ).order_by('-total')
    
    context = {
        'total_clientes': total_clientes,
        'total_cobrancas': total_cobrancas,
        'total_recebido': total_recebido,
        'total_pendente': total_pendente,
        'total_vencido': total_vencido,
        'ultimas_syncs': ultimas_syncs,
        'ultima_sync': ultima_sync,
        'cobrancas_recentes': cobrancas_recentes,
        'cobrancas_por_status': cobrancas_por_status,
    }
    
    return render(request, 'asaas_sync/dashboard.html', context)


@login_required
def lista_clientes(request):
    """Lista todos os clientes sincronizados"""
    
    # Filtros
    busca = request.GET.get('busca', '')
    estado = request.GET.get('estado', '')
    
    clientes = AsaasClienteSyncronizado.objects.all()
    
    if busca:
        clientes = clientes.filter(
            Q(nome__icontains=busca) |
            Q(cpf_cnpj__icontains=busca) |
            Q(email__icontains=busca)
        )
    
    if estado:
        clientes = clientes.filter(estado=estado)
    
    # Paginação simples (primeiros 100)
    clientes = clientes[:100]
    
    # Estados únicos para filtro
    estados = AsaasClienteSyncronizado.objects.values_list('estado', flat=True).distinct().order_by('estado')
    
    context = {
        'clientes': clientes,
        'busca': busca,
        'estado': estado,
        'estados': estados,
    }
    
    return render(request, 'asaas_sync/lista_clientes.html', context)


@login_required
def detalhes_cliente(request, cliente_id):
    """Detalhes de um cliente e suas cobranças"""
    
    cliente = get_object_or_404(AsaasClienteSyncronizado, id=cliente_id)
    
    # Cobranças do cliente
    cobrancas = cliente.cobrancas.all().order_by('-data_vencimento')
    
    # Estatísticas do cliente
    stats = {
        'total_cobrancas': cobrancas.count(),
        'total_recebido': cobrancas.filter(status__in=['RECEIVED', 'CONFIRMED']).aggregate(Sum('valor'))['valor__sum'] or 0,
        'total_pendente': cobrancas.filter(status='PENDING').aggregate(Sum('valor'))['valor__sum'] or 0,
        'total_vencido': cobrancas.filter(status='OVERDUE').aggregate(Sum('valor'))['valor__sum'] or 0,
    }
    
    # Separar cobranças por status
    cobrancas_pagas = cobrancas.filter(status__in=['RECEIVED', 'CONFIRMED'])
    cobrancas_pendentes = cobrancas.filter(status='PENDING')
    cobrancas_vencidas = cobrancas.filter(status='OVERDUE')
    cobrancas_outras = cobrancas.exclude(status__in=['RECEIVED', 'CONFIRMED', 'PENDING', 'OVERDUE'])
    
    context = {
        'cliente': cliente,
        'cobrancas': cobrancas,
        'stats': stats,
        'cobrancas_pagas': cobrancas_pagas,
        'cobrancas_pendentes': cobrancas_pendentes,
        'cobrancas_vencidas': cobrancas_vencidas,
        'cobrancas_outras': cobrancas_outras,
    }
    
    return render(request, 'asaas_sync/detalhes_cliente.html', context)


@login_required
def lista_cobrancas(request):
    """Lista todas as cobranças com filtros"""
    
    # Filtros
    status = request.GET.get('status', '')
    tipo = request.GET.get('tipo', '')
    cliente_busca = request.GET.get('cliente', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    
    cobrancas = AsaasCobrancaSyncronizada.objects.select_related('cliente').all()
    
    if status:
        cobrancas = cobrancas.filter(status=status)
    
    if tipo:
        cobrancas = cobrancas.filter(tipo_cobranca=tipo)
    
    if cliente_busca:
        cobrancas = cobrancas.filter(
            Q(cliente__nome__icontains=cliente_busca) |
            Q(cliente__cpf_cnpj__icontains=cliente_busca)
        )
    
    if data_inicio:
        cobrancas = cobrancas.filter(data_vencimento__gte=data_inicio)
    
    if data_fim:
        cobrancas = cobrancas.filter(data_vencimento__lte=data_fim)
    
    # Ordenação
    cobrancas = cobrancas.order_by('-data_vencimento')[:200]
    
    # Totais
    totais = {
        'quantidade': cobrancas.count(),
        'valor_total': cobrancas.aggregate(Sum('valor'))['valor__sum'] or 0
    }
    
    # Status filtrados para o dropdown
    status_filtrados = [
        ('PENDING', 'Pendente'),
        ('RECEIVED', 'Recebida'),
        ('CONFIRMED', 'Confirmada'),
        ('OVERDUE', 'Vencida'),
    ]
    
    context = {
        'cobrancas': cobrancas,
        'status': status,
        'tipo': tipo,
        'cliente_busca': cliente_busca,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'totais': totais,
        'status_choices': status_filtrados,
        'tipo_choices': AsaasCobrancaSyncronizada.TIPO_COBRANCA_CHOICES,
    }
    
    return render(request, 'asaas_sync/lista_cobrancas.html', context)


@login_required
def sincronizar_agora(request):
    """Inicia sincronização manual"""
    
    if request.method == 'POST':
        try:
            logger.info(f"Sincronização iniciada por {request.user.username}")
            
            sync_service = AsaasSyncService()
            log = sync_service.sincronizar_tudo(usuario=request.user)
            
            return JsonResponse({
                'success': True,
                'message': 'Sincronização concluída com sucesso!',
                'log': {
                    'id': log.id,
                    'status': log.status,
                    'total_clientes': log.total_clientes,
                    'clientes_novos': log.clientes_novos,
                    'total_cobrancas': log.total_cobrancas,
                    'cobrancas_novas': log.cobrancas_novas,
                    'duracao': log.duracao_segundos,
                    'mensagem': log.mensagem,
                }
            })
            
        except Exception as e:
            logger.error(f"Erro na sincronização: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': f'Erro na sincronização: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Método não permitido'
    }, status=405)


@login_required
def relatorio_completo(request):
    """Relatório completo com todas as informações"""
    
    clientes = AsaasClienteSyncronizado.objects.all()
    
    dados = []
    
    for cliente in clientes:
        cobrancas = cliente.cobrancas.all()
        
        dados.append({
            'cliente': cliente,
            'total_cobrancas': cobrancas.count(),
            'cobrancas_pagas': cobrancas.filter(status__in=['RECEIVED', 'CONFIRMED']).count(),
            'cobrancas_pendentes': cobrancas.filter(status='PENDING').count(),
            'cobrancas_vencidas': cobrancas.filter(status='OVERDUE').count(),
            'valor_recebido': cobrancas.filter(status__in=['RECEIVED', 'CONFIRMED']).aggregate(Sum('valor'))['valor__sum'] or 0,
            'valor_pendente': cobrancas.filter(status='PENDING').aggregate(Sum('valor'))['valor__sum'] or 0,
            'valor_vencido': cobrancas.filter(status='OVERDUE').aggregate(Sum('valor'))['valor__sum'] or 0,
            'cobrancas': cobrancas.order_by('-data_vencimento')
        })
    
    context = {
        'dados': dados,
        'data_geracao': timezone.now(),
    }
    
    return render(request, 'asaas_sync/relatorio_completo.html', context)
