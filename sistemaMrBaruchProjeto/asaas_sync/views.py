"""
Views para visualização de dados sincronizados do Asaas
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Q, Sum, Count, Case, When, DecimalField
from django.utils import timezone
from django.conf import settings
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
    """Lista todos os clientes sincronizados com paginação"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    # Filtros
    busca = request.GET.get('busca', '')
    inadimplente = request.GET.get('inadimplente', '')
    servico_concluido = request.GET.get('servico_concluido', '')
    page = request.GET.get('page', 1)
    
    clientes = AsaasClienteSyncronizado.objects.prefetch_related('cobrancas').all()
    
    # Filtro por nome, CPF ou CNPJ
    if busca:
        clientes = clientes.filter(
            Q(nome__icontains=busca) |
            Q(cpf_cnpj__icontains=busca)
        )
    
    # Filtro por inadimplência
    if inadimplente:
        if inadimplente == 'sim':
            # Clientes com cobranças vencidas
            clientes_ids = []
            for cliente in clientes:
                if cliente.esta_inadimplente():
                    clientes_ids.append(cliente.id)
            clientes = clientes.filter(id__in=clientes_ids)
        elif inadimplente == 'nao':
            # Clientes sem cobranças vencidas
            clientes_ids = []
            for cliente in clientes:
                if not cliente.esta_inadimplente():
                    clientes_ids.append(cliente.id)
            clientes = clientes.filter(id__in=clientes_ids)
    
    # Filtro por serviço concluído
    if servico_concluido:
        if servico_concluido == 'sim':
            clientes = clientes.filter(servico_concluido=True)
        elif servico_concluido == 'nao':
            clientes = clientes.filter(servico_concluido=False)
    
    # Ordenação
    clientes = clientes.order_by('nome')
    
    # Contagem total antes da paginação
    total_clientes = clientes.count()
    
    # Paginação - 50 clientes por página
    paginator = Paginator(clientes, 50)
    
    try:
        clientes_paginados = paginator.page(page)
    except PageNotAnInteger:
        clientes_paginados = paginator.page(1)
    except EmptyPage:
        clientes_paginados = paginator.page(paginator.num_pages)
    
    # Preparar dados enriquecidos
    clientes_dados = []
    for cliente in clientes_paginados:
        clientes_dados.append({
            'cliente': cliente,
            'valor_total': cliente.get_valor_total_servico(),
            'esta_inadimplente': cliente.esta_inadimplente(),
            'periodo_inadimplencia': cliente.get_periodo_inadimplencia(),
            'valor_inadimplente': cliente.get_valor_inadimplente(),
        })
    
    context = {
        'clientes_dados': clientes_dados,
        'clientes_paginados': clientes_paginados,
        'total_clientes': total_clientes,
        'busca': busca,
        'inadimplente': inadimplente,
        'servico_concluido': servico_concluido,
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
    """Lista todas as cobranças com filtros e paginação"""
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    # Filtros
    status = request.GET.get('status', '')
    tipo = request.GET.get('tipo', '')
    cliente_busca = request.GET.get('cliente', '')
    data_inicio = request.GET.get('data_inicio', '')
    data_fim = request.GET.get('data_fim', '')
    page = request.GET.get('page', 1)
    
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
    cobrancas = cobrancas.order_by('-data_vencimento')
    
    # Totais antes da paginação
    total_cobrancas = cobrancas.count()
    valor_total = cobrancas.aggregate(Sum('valor'))['valor__sum'] or 0
    
    # Paginação - 100 cobranças por página
    paginator = Paginator(cobrancas, 100)
    
    try:
        cobrancas_paginadas = paginator.page(page)
    except PageNotAnInteger:
        cobrancas_paginadas = paginator.page(1)
    except EmptyPage:
        cobrancas_paginadas = paginator.page(paginator.num_pages)
    
    # Totais
    totais = {
        'quantidade': total_cobrancas,
        'valor_total': valor_total
    }
    
    # Status filtrados para o dropdown
    status_filtrados = [
        ('PENDING', 'Pendente'),
        ('RECEIVED', 'Recebida'),
        ('CONFIRMED', 'Confirmada'),
        ('OVERDUE', 'Vencida'),
    ]
    
    context = {
        'cobrancas': cobrancas_paginadas,
        'cobrancas_paginadas': cobrancas_paginadas,
        'total_cobrancas': total_cobrancas,
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


@login_required
def atualizar_cliente(request, cliente_id):
    """Atualiza dados do cliente (consultor e status do serviço)"""
    
    if request.method == 'POST':
        try:
            cliente = get_object_or_404(AsaasClienteSyncronizado, id=cliente_id)
            
            # Atualizar consultor
            if 'consultor_responsavel' in request.POST:
                consultor = request.POST.get('consultor_responsavel', '').strip()
                cliente.consultor_responsavel = consultor if consultor else None
            
            # Atualizar status do serviço
            if 'servico_concluido' in request.POST:
                servico = request.POST.get('servico_concluido', 'false')
                cliente.servico_concluido = servico.lower() == 'true'
            
            cliente.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Cliente atualizado com sucesso!',
                'data': {
                    'consultor_responsavel': cliente.consultor_responsavel or '',
                    'servico_concluido': cliente.servico_concluido,
                }
            })
            
        except Exception as e:
            logger.error(f"Erro ao atualizar cliente: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': f'Erro ao atualizar: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Método não permitido'
    }, status=405)


@login_required
def sincronizar_alternativo(request):
    """Sincroniza dados de uma conta Asaas alternativa usando token configurado no backend"""
    
    if request.method == 'POST':
        try:
            # Buscar token alternativo das configurações (mais seguro que no frontend)
            token_alternativo = getattr(settings, 'ASAAS_ALTERNATIVO_TOKEN', None)
            
            if not token_alternativo:
                return JsonResponse({
                    'success': False,
                    'message': '❌ Token alternativo não configurado.\n\nConfigure ASAAS_ALTERNATIVO_TOKEN nas variáveis de ambiente ou settings.py'
                }, status=500)
            
            logger.info(f"Sincronização alternativa iniciada por {request.user.username}")
            logger.info(f"Token alternativo: {token_alternativo[:20]}...")
            
            # Criar instância do serviço com token alternativo
            sync_service = AsaasSyncService()
            
            # GARANTIR que está usando PRODUÇÃO do Asaas
            url_producao = 'https://api.asaas.com/v3'
            sync_service.base_url = url_producao
            logger.info(f"URL forçada para produção: {url_producao}")
            
            # Substituir temporariamente o token
            token_original = sync_service.api_token
            url_original = sync_service.base_url
            sync_service.api_token = token_alternativo
            sync_service.headers['access_token'] = token_alternativo
            
            try:
                # Executar sincronização
                log = sync_service.sincronizar_tudo(usuario=request.user)
                
                # Verificar se houve erro de autenticação
                if log.status == 'ERRO' and '401' in str(log.mensagem or ''):
                    return JsonResponse({
                        'success': False,
                        'message': '❌ Credenciais inválidas ou expiradas.\n\nVerifique se as credenciais da conta Asaas alternativa estão corretas e têm permissões adequadas.'
                    })
                
                # Verificar se houve erro de endpoint não encontrado
                if log.status == 'ERRO' and '404' in str(log.mensagem or ''):
                    return JsonResponse({
                        'success': False,
                        'message': '❌ Erro de comunicação com API Asaas.\n\nEndpoint não encontrado (404). Verifique se a URL da API está correta e se o endpoint existe.'
                    })
                
                # Verificar se houve outros erros
                if log.status == 'ERRO':
                    mensagem_erro = log.mensagem or 'Erro desconhecido durante sincronização'
                    return JsonResponse({
                        'success': False,
                        'message': f'❌ Erro durante sincronização:\n\n{mensagem_erro}'
                    })
                
                return JsonResponse({
                    'success': True,
                    'message': 'Sincronização alternativa concluída com sucesso!',
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
            finally:
                # Restaurar token e URL originais
                sync_service.api_token = token_original
                sync_service.base_url = url_original
                sync_service.headers['access_token'] = token_original
            
        except Exception as e:
            logger.error(f"Erro na sincronização alternativa: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'message': f'❌ Erro na sincronização: {str(e)}'
            }, status=500)
    
    return JsonResponse({
        'success': False,
        'message': 'Método não permitido'
    }, status=405)

