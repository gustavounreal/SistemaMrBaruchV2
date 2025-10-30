from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from django.views.decorators.http import require_POST
from .models import ConfiguracaoSistema
from .forms import ConfiguracaoSistemaForm
from .services import GrupoService
from django.http import JsonResponse
from financeiro.models import ClienteAsaas
from marketing.models import Lead

@login_required
@permission_required('core.change_configuracaosistema')
def painel_configuracoes(request):
    """
    Painel de configurações organizado por Jornada (Lead) e por etapas,
    com criação automática de chaves ausentes e validações de tipo.
    """
    # Definições de variáveis por etapa da Jornada Lead
    definicoes_por_categoria = {
        'lead_captura': [
            {
                'chave': 'LEAD_OBRIGAR_EMAIL',
                'descricao': 'Requerer e-mail no cadastro do lead',
                'tipo': 'BOOLEANO',
                'valor_padrao': 'false',
            },
            {
                'chave': 'LEAD_OBRIGAR_CPF_PARA_LEVANTAMENTO',
                'descricao': 'Exigir CPF/CNPJ apenas quando houver levantamento',
                'tipo': 'BOOLEANO',
                'valor_padrao': 'true',
            },
            {
                'chave': 'LEAD_STATUS_INICIAL',
                'descricao': 'Status inicial do lead ao cadastrar',
                'tipo': 'TEXTO',
                'valor_padrao': 'NOVO',
            },
        ],
        'lead_pix': [
            {
                'chave': 'PIX_VALOR_LEVANTAMENTO',
                'descricao': 'Valor da cobrança PIX para levantamento',
                'tipo': 'NUMERO',
                'valor_padrao': '0.50',
            },
            {
                'chave': 'PIX_DESCRICAO',
                'descricao': 'Descrição padrão da cobrança PIX',
                'tipo': 'TEXTO',
                'valor_padrao': 'Levantamento de informações (PIX)',
            },
            {
                'chave': 'PIX_EXPIRA_MINUTOS',
                'descricao': 'Tempo (minutos) para expiração do PIX',
                'tipo': 'NUMERO',
                'valor_padrao': '60',
            },
            {
                'chave': 'ASAAS_MAX_RETRIES',
                'descricao': 'Número máximo de tentativas com a API ASAAS',
                'tipo': 'NUMERO',
                'valor_padrao': '3',
            },
            {
                'chave': 'ASAAS_TIMEOUT',
                'descricao': 'Timeout (segundos) nas requisições ASAAS',
                'tipo': 'NUMERO',
                'valor_padrao': '30',
            },
        ],
        'lead_pagamento': [
            {
                'chave': 'LEAD_STATUS_APOS_PAGAMENTO',
                'descricao': 'Status do lead após pagamento confirmado',
                'tipo': 'TEXTO',
                'valor_padrao': 'LEVANTAMENTO_PAGO',
            },
        ],
        'lead_comissao': [
            {
                'chave': 'COMISSAO_ATIVA',
                'descricao': 'Ativar comissionamento automático',
                'tipo': 'BOOLEANO',
                'valor_padrao': 'true',
            },
            {
                'chave': 'COMISSAO_ATENDENTE_VALOR_FIXO',
                'descricao': 'Valor fixo de comissão por lead pago',
                'tipo': 'NUMERO',
                'valor_padrao': '0.50',
            },
        ],
        'captadores': [
            {
                'chave': 'CAPTADOR_WHATSAPP_NUMERO',
                'descricao': 'Número WhatsApp para links de indicação (formato: 5511978891213)',
                'tipo': 'TEXTO',
                'valor_padrao': '5511978891213',
            },
            {
                'chave': 'CAPTADOR_WHATSAPP_MENSAGEM',
                'descricao': 'Mensagem padrão do link de indicação',
                'tipo': 'TEXTO',
                'valor_padrao': 'Olá! Fui indicado por um captador.',
            },
            {
                'chave': 'CAPTADOR_COMISSAO_PERCENTUAL',
                'descricao': 'Percentual de comissão dos captadores (%)',
                'tipo': 'NUMERO',
                'valor_padrao': '20',
            },
        ],
        'lead_acompanhamento': [
            {
                'chave': 'FOLLOWUP_INTERVALO_PADRAO_DIAS',
                'descricao': 'Intervalo padrão (dias) para acompanhamento comercial',
                'tipo': 'NUMERO',
                'valor_padrao': '2',
            },
            {
                'chave': 'LEAD_STATUS_CONTATO',
                'descricao': 'Status usado quando iniciar contato comercial',
                'tipo': 'TEXTO',
                'valor_padrao': 'CONTATADO',
            },
        ],
        'auditoria_logs': [
            {
                'chave': 'LOG_ATIVO',
                'descricao': 'Ativar logs de auditoria',
                'tipo': 'BOOLEANO',
                'valor_padrao': 'true',
            },
            {
                'chave': 'LOG_NIVEL_MINIMO',
                'descricao': 'Nível mínimo dos logs (DEBUG, INFO, WARNING, ERROR)',
                'tipo': 'TEXTO',
                'valor_padrao': 'INFO',
            },
        ],
    }

    # Criar chaves ausentes com valores padrão
    for categoria, itens in definicoes_por_categoria.items():
        for d in itens:
            obj, created = ConfiguracaoSistema.objects.get_or_create(
                chave=d['chave'],
                defaults={
                    'valor': d['valor_padrao'],
                    'descricao': d['descricao'],
                    'tipo': d['tipo'],
                },
            )
            # Se já existe mas está sem descrição ou tipo, completar
            update_fields = []
            if not obj.descricao:
                obj.descricao = d['descricao']; update_fields.append('descricao')
            if not obj.tipo:
                obj.tipo = d['tipo']; update_fields.append('tipo')
            if update_fields:
                obj.save(update_fields=update_fields)

    # Montar formulários por categoria
    configs_forms_por_categoria = {}
    for categoria, itens in definicoes_por_categoria.items():
        chaves = [i['chave'] for i in itens]
        configs = ConfiguracaoSistema.objects.filter(chave__in=chaves).order_by('chave')
        configs_forms = [
            (config, ConfiguracaoSistemaForm(instance=config, prefix=config.chave))
            for config in configs
        ]
        configs_forms_por_categoria[categoria] = configs_forms

    # Ações de POST: salvar configuração individual ou testar ASAAS
    if request.method == 'POST':
        acao = request.POST.get('acao')
        if acao == 'testar_asaas':
            try:
                from .asaas_service import AsaasService
                svc = AsaasService()
                diag = svc.diagnosticar_configuracao()
                # Armazena um JSON no messages para ser lido pelo template
                import json as _json
                messages.add_message(request, messages.INFO, _json.dumps({
                    'tipo': 'asaas_diag',
                    'ok': diag.get('ok'),
                    'config': diag.get('config'),
                    'checks': diag.get('checks'),
                    'executado_em': str(diag.get('executado_em')),
                }))
                if diag.get('ok'):
                    messages.success(request, 'Integração ASAAS validada com sucesso!')
                else:
                    messages.error(request, 'Falha ao validar a integração ASAAS. Veja detalhes no relatório.')
            except Exception as e:
                messages.error(request, f'Erro ao validar ASAAS: {str(e)}')
            return redirect('core:painel_configuracoes')

        config_chave = request.POST.get('config_chave')
        if config_chave:
            try:
                config = ConfiguracaoSistema.objects.get(chave=config_chave)
                form = ConfiguracaoSistemaForm(request.POST, instance=config, prefix=config.chave)
                if form.is_valid():
                    form.save()
                    messages.success(request, f'Configuração {config.chave} atualizada com sucesso!')
                else:
                    messages.error(request, f'Erro nos dados: {form.errors.as_text()}')
            except Exception as e:
                messages.error(request, f'Erro ao atualizar configuração: {str(e)}')
        return redirect('core:painel_configuracoes')

    # Adiciona dados para a aba de Configuração de Grupos
    User = get_user_model()
    usuarios = User.objects.all().order_by('first_name', 'last_name', 'username')
    grupos_info = GrupoService.listar_grupos_sistema()  # Usar service para listar grupos
    selected_user_id = request.GET.get('selected_user')

    return render(request, 'core/painel_configuracoes.html', {
        'configs_forms_por_categoria': configs_forms_por_categoria,
        'usuarios': usuarios,
        'grupos': grupos_info,  # Passar grupos com metadados
        'selected_user_id': selected_user_id,
        'titulo': 'Painel de Configurações',
    })


@login_required
def documentacao(request):
    """
    View para exibir a documentação do sistema, guias do usuário e documentação técnica.
    """
    origem = request.GET.get('from')
    if origem == 'jornadas':
        back_url = reverse('core:documentacao_jornadas')
        back_label = 'Voltar às Jornadas'
        breadcrumbs = [
            {'label': 'Documentação', 'url': reverse('core:documentacao_jornadas')},
            {'label': 'Jornada Lead', 'url': None},
        ]
    else:
        back_url = reverse('accounts:dashboard')
        back_label = 'Voltar ao Dashboard'
        breadcrumbs = [
            {'label': 'Documentação', 'url': None},
            {'label': 'Jornada Lead', 'url': None},
        ]
    # Coleta valores ATUAIS do Painel de Configurações para exibir na documentação
    definicoes_por_categoria = {
        'lead_captura': [
            {'chave': 'LEAD_OBRIGAR_EMAIL', 'descricao': 'Requerer e-mail no cadastro do lead', 'tipo': 'BOOLEANO', 'valor_padrao': 'false'},
            {'chave': 'LEAD_OBRIGAR_CPF_PARA_LEVANTAMENTO', 'descricao': 'Exigir CPF/CNPJ apenas quando houver levantamento', 'tipo': 'BOOLEANO', 'valor_padrao': 'true'},
            {'chave': 'LEAD_STATUS_INICIAL', 'descricao': 'Status inicial do lead ao cadastrar', 'tipo': 'TEXTO', 'valor_padrao': 'NOVO'},
        ],
        'lead_pix': [
            {'chave': 'PIX_VALOR_LEVANTAMENTO', 'descricao': 'Valor da cobrança PIX para levantamento', 'tipo': 'NUMERO', 'valor_padrao': '0.50'},
            {'chave': 'PIX_DESCRICAO', 'descricao': 'Descrição padrão da cobrança PIX', 'tipo': 'TEXTO', 'valor_padrao': 'Levantamento de informações (PIX)'},
            {'chave': 'PIX_EXPIRA_MINUTOS', 'descricao': 'Tempo (minutos) para expiração do PIX', 'tipo': 'NUMERO', 'valor_padrao': '60'},
            {'chave': 'ASAAS_MAX_RETRIES', 'descricao': 'Número máximo de tentativas com a API ASAAS', 'tipo': 'NUMERO', 'valor_padrao': '3'},
            {'chave': 'ASAAS_TIMEOUT', 'descricao': 'Timeout (segundos) nas requisições ASAAS', 'tipo': 'NUMERO', 'valor_padrao': '30'},
        ],
        'lead_pagamento': [
            {'chave': 'LEAD_STATUS_APOS_PAGAMENTO', 'descricao': 'Status do lead após pagamento confirmado', 'tipo': 'TEXTO', 'valor_padrao': 'LEVANTAMENTO_PAGO'},
        ],
        'lead_comissao': [
            {'chave': 'COMISSAO_ATIVA', 'descricao': 'Ativar comissionamento automático', 'tipo': 'BOOLEANO', 'valor_padrao': 'true'},
            {'chave': 'COMISSAO_ATENDENTE_VALOR_FIXO', 'descricao': 'Valor fixo de comissão por lead pago', 'tipo': 'NUMERO', 'valor_padrao': '0.50'},
        ],
        'lead_acompanhamento': [
            {'chave': 'FOLLOWUP_INTERVALO_PADRAO_DIAS', 'descricao': 'Intervalo padrão (dias) para acompanhamento comercial', 'tipo': 'NUMERO', 'valor_padrao': '2'},
            {'chave': 'LEAD_STATUS_CONTATO', 'descricao': 'Status usado quando iniciar contato comercial', 'tipo': 'TEXTO', 'valor_padrao': 'CONTATADO'},
        ],
        'auditoria_logs': [
            {'chave': 'LOG_ATIVO', 'descricao': 'Ativar logs de auditoria', 'tipo': 'BOOLEANO', 'valor_padrao': 'true'},
            {'chave': 'LOG_NIVEL_MINIMO', 'descricao': 'Nível mínimo dos logs (DEBUG, INFO, WARNING, ERROR)', 'tipo': 'TEXTO', 'valor_padrao': 'INFO'},
        ],
    }

    # Garante a existência das chaves principais (auto-criação caso ainda não tenha passado no painel)
    from .models import ConfiguracaoSistema
    for categoria, itens in definicoes_por_categoria.items():
        for d in itens:
            ConfiguracaoSistema.objects.get_or_create(
                chave=d['chave'],
                defaults={
                    'valor': d['valor_padrao'],
                    'descricao': d['descricao'],
                    'tipo': d['tipo'],
                },
            )

    # Monta estrutura com valores atuais por categoria
    config_values_by_category = {}
    for categoria, itens in definicoes_por_categoria.items():
        chaves = [i['chave'] for i in itens]
        valores = {c.chave: c for c in ConfiguracaoSistema.objects.filter(chave__in=chaves)}
        lista = []
        for d in itens:
            c = valores.get(d['chave'])
            lista.append({
                'chave': d['chave'],
                'tipo': (c.tipo if c and c.tipo else d['tipo']),
                'descricao': (c.descricao if c and c.descricao else d['descricao']),
                'valor_padrao': d['valor_padrao'],
                'valor_atual': (c.valor if c else d['valor_padrao']),
            })
        config_values_by_category[categoria] = lista

    return render(request, 'core/lead_jornada_documentacao.html', {
        'titulo': 'Documentação do Sistema',
        'back_url': back_url,
        'back_label': back_label,
        'breadcrumbs': breadcrumbs,
        'config_values_by_category': config_values_by_category,
    })


@login_required
def central_documentacao(request):
    """
    Painel central de documentação com acesso a jornadas, módulos e guias.
    """
    return render(request, 'core/central_documentacao.html')


@login_required
def documentacao_jornadas(request):
    """Página anterior: lista as jornadas como módulos, cada uma redireciona para sua documentação."""
    return render(request, 'core/documentacao_jornadas.html')


@login_required
def documentacao_sistema(request):
    """Documentação completa do Sistema Mr. Baruch com arquitetura, módulos e guias."""
    return render(request, 'core/documentacao_sistema.html')


@login_required
def doc_comissoes(request):
    """Documentação do Módulo de Comissões."""
    return render(request, 'core/doc_comissoes.html', {
        'doc_title': 'Documentação - Sistema de Comissões',
        'doc_subtitle': 'Guia completo do módulo de comissões do Sistema Mr. Baruch',
        'doc_module': 'comissoes',
        'doc_date': '14 de Outubro de 2025',
        'doc_version': 'v1.0',
        'doc_status': 'Produção',
    })


@login_required
def doc_relatorios(request):
    """Documentação do Módulo de Relatórios."""
    return render(request, 'core/doc_relatorios.html', {
        'doc_title': 'Documentação - Módulo de Relatórios',
        'doc_subtitle': 'Guia completo do sistema de relatórios gerenciais',
        'doc_module': 'relatorios',
        'doc_date': '14 de Outubro de 2025',
        'doc_version': 'v1.0',
        'doc_status': 'Produção',
    })


@login_required
def documentacao_modulos(request):
    """Página com lista de módulos documentados."""
    return render(request, 'core/documentacao_modulos.html')


@login_required
def documentacao_tecnica(request):
    """Documentação técnica do sistema (stack, arquitetura, deploy)."""
    return render(request, 'core/documentacao_tecnica.html')


@require_POST
@login_required
@permission_required('auth.change_group')
@require_POST
@login_required
@permission_required('auth.change_group')
def adicionar_usuario_grupo(request):
    """Adiciona usuário a um grupo usando o GrupoService"""
    usuario_id = request.POST.get('usuario')
    grupo_name = request.POST.get('grupo')
    
    User = get_user_model()
    try:
        usuario = User.objects.get(id=usuario_id)
        
        # Usar service para adicionar
        sucesso, mensagem = GrupoService.adicionar_usuario_grupo(usuario, grupo_name)
        
        if sucesso:
            messages.success(request, mensagem)
        else:
            messages.warning(request, mensagem)
        
        # Se for AJAX, retornar JSON com grupos atualizados
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            grupos_usuario = GrupoService.obter_grupos_usuario(usuario)
            return JsonResponse({
                'success': sucesso,
                'message': mensagem,
                'groups': [g['name'] for g in grupos_usuario],
                'groups_info': grupos_usuario
            })
    
    except User.DoesNotExist:
        mensagem = 'Usuário não encontrado'
        messages.error(request, mensagem)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': mensagem})
    
    return redirect(f"{reverse('core:painel_configuracoes')}?selected_user={usuario_id}")

@require_POST
@login_required
@permission_required('auth.change_group')
def remover_usuario_grupo(request):
    """Remove usuário de um grupo usando o GrupoService"""
    usuario_id = request.POST.get('usuario_remover')
    grupo_name = request.POST.get('grupo_remover')
    
    User = get_user_model()
    try:
        usuario = User.objects.get(id=usuario_id)
        
        # Usar service para remover
        sucesso, mensagem = GrupoService.remover_usuario_grupo(usuario, grupo_name)
        
        if sucesso:
            messages.success(request, mensagem)
        else:
            messages.warning(request, mensagem)
        
        # Se for AJAX, retornar JSON com grupos atualizados
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            grupos_usuario = GrupoService.obter_grupos_usuario(usuario)
            return JsonResponse({
                'success': sucesso,
                'message': mensagem,
                'groups': [g['name'] for g in grupos_usuario],
                'groups_info': grupos_usuario
            })
    
    except User.DoesNotExist:
        mensagem = 'Usuário não encontrado'
        messages.error(request, mensagem)
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': mensagem})
    
    return redirect(f"{reverse('core:painel_configuracoes')}?selected_user={usuario_id}")


@login_required
@permission_required('auth.view_group')
def obter_grupos_usuario_ajax(request, usuario_id):
    """API AJAX para obter grupos do usuário em tempo real"""
    try:
        User = get_user_model()
        usuario = User.objects.get(id=usuario_id)
        
        # Obter grupos do usuário usando o service
        grupos_usuario = GrupoService.obter_grupos_usuario(usuario)
        
        # Obter todos os grupos disponíveis
        todos_grupos = GrupoService.listar_grupos_sistema()
        
        # Filtrar grupos que o usuário ainda não tem
        grupos_disponiveis = [
            g for g in todos_grupos 
            if g['name'] not in [gu['name'] for gu in grupos_usuario] 
            and not g.get('nao_existe', False)
        ]
        
        return JsonResponse({
            'success': True,
            'usuario': {
                'id': usuario.id,
                'nome': usuario.get_full_name() or usuario.username,
                'email': usuario.email
            },
            'grupos_atuais': grupos_usuario,
            'grupos_disponiveis': grupos_disponiveis
        })
    
    except User.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Usuário não encontrado'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# ==================== WEBHOOK ASAAS ====================
import json
import logging
import traceback
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .services import LogService

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Obtém IP real do cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


@csrf_exempt
@require_POST
def webhook_asaas(request):
    """
    Endpoint para receber webhooks do ASAAS com log completo
    
    Eventos suportados:
    - PAYMENT_CREATED: Cobrança criada
    - PAYMENT_UPDATED: Cobrança atualizada
    - PAYMENT_CONFIRMED: Pagamento confirmado (aguardando compensação)
    - PAYMENT_RECEIVED: Pagamento recebido e compensado
    - PAYMENT_OVERDUE: Pagamento vencido
    - PAYMENT_DELETED: Cobrança deletada
    - PAYMENT_REFUNDED: Pagamento estornado
    - PAYMENT_RECEIVED_IN_CASH: Pagamento recebido em dinheiro
    - PAYMENT_CHARGEBACK_REQUESTED: Chargeback solicitado
    - PAYMENT_CHARGEBACK_DISPUTE: Contestação de chargeback
    """
    from .models import WebhookLog
    from decimal import Decimal
    
    webhook_log = None
    
    try:
        # 1. Obter dados do webhook
        body = request.body.decode('utf-8')
        logger.info(f"[webhook_asaas] Recebido webhook ASAAS: {body[:200]}...")
        
        try:
            dados_webhook = json.loads(body)
        except json.JSONDecodeError as e:
            logger.error(f"[webhook_asaas] Erro ao decodificar JSON: {str(e)}")
            # Tentar criar log de erro
            try:
                WebhookLog.objects.create(
                    tipo='ASAAS',
                    evento='ERRO_PARSE',
                    payload={'error': str(e), 'body': body[:1000]},
                    status_processamento='ERROR',
                    mensagem_erro=f"Erro ao decodificar JSON: {str(e)}",
                    ip_origem=get_client_ip(request)
                )
            except:
                pass
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON'
            }, status=400)
        
        # 2. Extrair informações principais
        event = dados_webhook.get('event')
        payment_data = dados_webhook.get('payment', {})
        payment_id = payment_data.get('id')
        payment_status = payment_data.get('status')
        payment_value = payment_data.get('value')
        billing_type = payment_data.get('billingType')
        customer_id = payment_data.get('customer')
        
        # 3. Capturar headers importantes
        headers = {
            'Content-Type': request.META.get('CONTENT_TYPE'),
            'User-Agent': request.META.get('HTTP_USER_AGENT'),
            'X-Forwarded-For': request.META.get('HTTP_X_FORWARDED_FOR'),
            'X-Real-IP': request.META.get('HTTP_X_REAL_IP'),
        }
        
        # 4. Criar log no banco de dados
        webhook_log = WebhookLog.objects.create(
            tipo='ASAAS',
            evento=event or 'DESCONHECIDO',
            payload=dados_webhook,
            headers=headers,
            payment_id=payment_id or '',
            customer_id=customer_id or '',
            payment_status=payment_status or '',
            valor=Decimal(str(payment_value)) if payment_value else None,
            ip_origem=get_client_ip(request),
            status_processamento='SUCCESS'  # Será atualizado se houver erro
        )
        
        logger.info(f"[webhook_asaas] Webhook #{webhook_log.id} | Event: {event} | Payment: {payment_id} | Status: {payment_status} | Type: {billing_type} | Value: R$ {payment_value}")
        
        # 5. Validar dados obrigatórios
        if not event or not payment_id:
            logger.warning(f"[webhook_asaas] Webhook sem event ou payment_id")
            webhook_log.status_processamento = 'ERROR'
            webhook_log.mensagem_erro = 'Missing event or payment_id'
            webhook_log.save(update_fields=['status_processamento', 'mensagem_erro'])
            return JsonResponse({
                'success': False,
                'error': 'Missing event or payment_id',
                'webhook_id': webhook_log.id
            }, status=400)
        
        # 6. Registrar no log do sistema
        LogService.registrar(
            nivel='INFO',
            mensagem=f"Webhook #{webhook_log.id} ASAAS recebido - Event: {event} - Payment: {payment_id} - Status: {payment_status}",
            modulo='core',
            acao='webhook_asaas_recebido'
        )
        
        # 7. Processar por tipo de evento
        success = False
        
        if event in ['PAYMENT_RECEIVED', 'PAYMENT_CONFIRMED', 'PAYMENT_RECEIVED_IN_CASH']:
            # Pagamento confirmado/recebido
            success = _processar_pagamento_confirmado(payment_data)
            
        elif event == 'PAYMENT_OVERDUE':
            # Pagamento vencido
            success = _processar_pagamento_vencido(payment_data)
            
        elif event == 'PAYMENT_DELETED':
            # Cobrança deletada
            success = _processar_pagamento_deletado(payment_data)
            
        elif event == 'PAYMENT_REFUNDED':
            # Pagamento estornado
            success = _processar_pagamento_estornado(payment_data)
            
        elif event in ['PAYMENT_CREATED', 'PAYMENT_UPDATED']:
            # Apenas registrar no log, não precisa ação
            logger.info(f"[webhook_asaas] Webhook #{webhook_log.id} - Evento {event} registrado - sem ação necessária")
            success = True
            
        else:
            # Evento não tratado
            logger.warning(f"[webhook_asaas] Webhook #{webhook_log.id} - Evento não tratado: {event}")
            LogService.registrar(
                nivel='WARNING',
                mensagem=f"Evento webhook não tratado: {event}",
                modulo='core',
                acao='webhook_evento_nao_tratado'
            )
            webhook_log.status_processamento = 'IGNORED'
            webhook_log.mensagem_erro = f'Evento não tratado: {event}'
            webhook_log.save(update_fields=['status_processamento', 'mensagem_erro'])
            success = True  # Retorna sucesso para não reenviar
        
        # 8. Atualizar status do log
        if success:
            webhook_log.status_processamento = 'SUCCESS'
            webhook_log.save(update_fields=['status_processamento'])
            logger.info(f"[webhook_asaas] Webhook #{webhook_log.id} processado com sucesso")
            return JsonResponse({
                'success': True,
                'webhook_id': webhook_log.id
            }, status=200)
        else:
            webhook_log.status_processamento = 'ERROR'
            webhook_log.mensagem_erro = 'Falha no processamento'
            webhook_log.save(update_fields=['status_processamento', 'mensagem_erro'])
            return JsonResponse({
                'success': False,
                'error': 'Processing failed',
                'webhook_id': webhook_log.id
            }, status=500)
            
    except Exception as e:
        logger.error(f"[webhook_asaas] Erro crítico: {str(e)}", exc_info=True)
        
        # Atualizar log com erro
        if webhook_log:
            webhook_log.status_processamento = 'ERROR'
            webhook_log.mensagem_erro = f"{str(e)}\n\n{traceback.format_exc()}"
            webhook_log.save(update_fields=['status_processamento', 'mensagem_erro'])
        
        LogService.registrar(
            nivel='ERROR',
            mensagem=f"Erro crítico no webhook ASAAS: {str(e)}",
            modulo='core',
            acao='webhook_asaas_erro'
        )
        return JsonResponse({
            'success': False,
            'error': 'Internal server error',
            'webhook_id': webhook_log.id if webhook_log else None
        }, status=500)


def _processar_pagamento_confirmado(payment_data):
    """
    Processa pagamento confirmado/recebido
    
    Atualiza:
    - PixLevantamento (se for PIX de levantamento)
    - Parcela (se for parcela de venda)
    - Lead status
    
    IMPORTANTE: As comissões são criadas automaticamente via SIGNALS.
    Caso falhe, o validador automático irá recuperar.
    """
    payment_id = payment_data.get('id')
    value = payment_data.get('value')
    billing_type = payment_data.get('billingType')
    
    logger.info(f"[webhook] Processando pagamento confirmado: {payment_id}")
    
    try:
        # 1. Tentar atualizar PIX Levantamento
        from financeiro.models import PixLevantamento, PixEntrada, Parcela
        
        try:
            pix_levantamento = PixLevantamento.objects.get(asaas_payment_id=payment_id)
            pix_levantamento.status_pagamento = 'pago'
            pix_levantamento.save(update_fields=['status_pagamento'])
            
            # Atualizar Lead
            if pix_levantamento.lead:
                pix_levantamento.lead.status = 'LEVANTAMENTO_PAGO'
                pix_levantamento.lead.fez_levantamento = True
                pix_levantamento.lead.save(update_fields=['status', 'fez_levantamento'])
                
                logger.info(f"[webhook] PIX Levantamento pago: {payment_id} - Lead {pix_levantamento.lead.id} atualizado")
                
                LogService.registrar(
                    nivel='INFO',
                    mensagem=f"PIX Levantamento confirmado: Lead {pix_levantamento.lead.id} - R$ {value}",
                    modulo='financeiro',
                    acao='pix_levantamento_pago'
                )
                
                # GERAR COMISSÃO DO ATENDENTE
                try:
                    from core.commission_service import CommissionService
                    comissao_atendente = CommissionService.criar_comissao_atendente(pix_levantamento.lead)
                    logger.info(f"[webhook] Comissão atendente criada: R$ {comissao_atendente.valor:.2f}")
                    
                    LogService.registrar(
                        nivel='INFO',
                        mensagem=f"Comissão atendente criada: Lead {pix_levantamento.lead.id} - R$ {comissao_atendente.valor}",
                        modulo='comissoes',
                        acao='comissao_atendente_criada'
                    )
                except Exception as e_comissao:
                    logger.error(f"[webhook] Erro ao criar comissão atendente: {str(e_comissao)}")
                    LogService.registrar(
                        nivel='ERROR',
                        mensagem=f"Erro ao criar comissão atendente: {str(e_comissao)}",
                        modulo='comissoes',
                        acao='erro_comissao_atendente'
                    )
            
            return True
            
        except PixLevantamento.DoesNotExist:
            logger.debug(f"[webhook] Não é PIX Levantamento: {payment_id}")
        
        # 2. Tentar atualizar PIX de Entrada da Venda
        try:
            pix_entrada = PixEntrada.objects.select_related('venda', 'venda__cliente').get(asaas_payment_id=payment_id)
            pix_entrada.status_pagamento = 'pago'
            pix_entrada.data_pagamento = timezone.now()
            pix_entrada.save(update_fields=['status_pagamento', 'data_pagamento'])
            
            logger.info(f"[webhook] PIX Entrada pago: {payment_id} - Venda {pix_entrada.venda.id}")
            
            # ✅ Atualizar status da venda para CONTRATO_ASSINADO E marcar entrada como PAGA
            venda = pix_entrada.venda
            venda.status = 'CONTRATO_ASSINADO'  # Muda para indicar que entrada foi paga
            venda.status_pagamento_entrada = 'PAGO'  # ✅ MARCA ENTRADA COMO PAGA
            venda.save(update_fields=['status', 'status_pagamento_entrada'])
            
            LogService.registrar(
                nivel='INFO',
                mensagem=f"PIX Entrada confirmado: Venda {venda.id} - R$ {value} - Status atualizado",
                modulo='financeiro',
                acao='pix_entrada_pago'
            )
            
            # GERAR CONTRATO AUTOMATICAMENTE
            try:
                from juridico.models import Contrato
                
                # Criar ou buscar contrato
                contrato, contrato_created = Contrato.objects.get_or_create(
                    venda=venda,
                    cliente=venda.cliente,
                    defaults={'status': 'AGUARDANDO_GERACAO'}
                )
                
                if contrato_created or contrato.status == 'AGUARDANDO_GERACAO':
                    # Gerar número do contrato
                    if not contrato.numero_contrato:
                        contrato.gerar_numero_contrato()
                    
                    # Mudar status para GERADO (pronto para ser baixado e enviado)
                    contrato.mudar_status('GERADO', None, 'Contrato gerado automaticamente após pagamento da entrada')
                    
                    logger.info(f"[webhook] Contrato gerado automaticamente: {contrato.numero_contrato}")
                    
                    LogService.registrar(
                        nivel='INFO',
                        mensagem=f"Contrato {contrato.numero_contrato} gerado automaticamente para Venda {venda.id}",
                        modulo='juridico',
                        acao='contrato_gerado_auto'
                    )
                
            except Exception as e_contrato:
                logger.error(f"[webhook] Erro ao gerar contrato: {str(e_contrato)}")
                LogService.registrar(
                    nivel='ERROR',
                    mensagem=f"Erro ao gerar contrato automaticamente: {str(e_contrato)}",
                    modulo='juridico',
                    acao='erro_gerar_contrato_auto'
                )
            
            # ✅ ATUALIZAR STATUS DAS COMISSÕES DA ENTRADA (já foram criadas no cadastro)
            try:
                from financeiro.models import Comissao
                
                # Buscar comissões da entrada (captador + consultor)
                comissoes_entrada = Comissao.objects.filter(
                    venda=venda,
                    parcela__isnull=True,  # Comissões da entrada não têm parcela vinculada
                    tipo_comissao__in=['CAPTADOR_ENTRADA', 'CONSULTOR_ENTRADA'],
                    status='pendente'
                )
                
                quantidade_atualizada = 0
                for comissao in comissoes_entrada:
                    comissao.status = 'paga'
                    comissao.data_pagamento = timezone.now().date()
                    comissao.save(update_fields=['status', 'data_pagamento'])
                    quantidade_atualizada += 1
                    
                    logger.info(
                        f"[webhook] Comissão {comissao.tipo_comissao} ATUALIZADA para paga: "
                        f"{comissao.usuario.email} - R$ {comissao.valor_comissao:.2f}"
                    )
                
                if quantidade_atualizada > 0:
                    LogService.registrar(
                        nivel='INFO',
                        mensagem=f"Comissões da entrada ATUALIZADAS para paga: {quantidade_atualizada} comissões - Venda {venda.id}",
                        modulo='comissoes',
                        acao='comissoes_entrada_atualizadas'
                    )
                else:
                    logger.warning(f"[webhook] Nenhuma comissão de entrada encontrada para atualizar - Venda {venda.id}")
                    
            except Exception as e_comissao:
                logger.error(f"[webhook] Erro ao atualizar comissões da entrada: {str(e_comissao)}")
                LogService.registrar(
                    nivel='ERROR',
                    mensagem=f"Erro ao atualizar comissões da entrada: {str(e_comissao)}",
                    modulo='comissoes',
                    acao='erro_atualizar_comissoes_entrada'
                )
            
            return True
            
        except PixEntrada.DoesNotExist:
            logger.debug(f"[webhook] Não é PIX Entrada: {payment_id}")
        
        # 3. Tentar atualizar Parcela de Venda
        try:
            parcela = Parcela.objects.get(id_asaas=payment_id)
            parcela.status = 'paga'
            parcela.data_pagamento = timezone.now().date()
            parcela.save(update_fields=['status', 'data_pagamento'])
            
            logger.info(f"[webhook] Parcela paga: {payment_id} - Venda {parcela.venda.id}")
            
            # ✅ SE FOR ENTRADA (numero_parcela = 0), MARCAR STATUS_PAGAMENTO_ENTRADA
            if parcela.numero_parcela == 0:
                venda = parcela.venda
                venda.status_pagamento_entrada = 'PAGO'
                venda.save(update_fields=['status_pagamento_entrada'])
                
                logger.info(f"[webhook] Entrada via BOLETO paga - Venda {venda.id} atualizada")
                
                LogService.registrar(
                    nivel='INFO',
                    mensagem=f"Entrada BOLETO confirmada: Venda {venda.id} - R$ {value}",
                    modulo='financeiro',
                    acao='entrada_boleto_paga'
                )
            
            LogService.registrar(
                nivel='INFO',
                mensagem=f"Parcela confirmada: Venda {parcela.venda.id} - Parcela {parcela.numero_parcela} - R$ {value}",
                modulo='financeiro',
                acao='parcela_paga'
            )

            # ✅ ATUALIZAR STATUS DAS COMISSÕES DA PARCELA (já foram criadas no cadastro)
            try:
                from financeiro.models import Comissao
                
                # Buscar comissões vinculadas a esta parcela específica
                comissoes_parcela = Comissao.objects.filter(
                    venda=parcela.venda,
                    parcela=parcela,  # Vinculadas a esta parcela específica
                    tipo_comissao__in=['CAPTADOR_PARCELA', 'CONSULTOR_PARCELA'],
                    status='pendente'
                )
                
                quantidade_atualizada = 0
                for comissao in comissoes_parcela:
                    comissao.status = 'paga'
                    comissao.data_pagamento = timezone.now().date()
                    comissao.observacoes = f"Parcela {parcela.numero_parcela} paga em {timezone.now().date().strftime('%d/%m/%Y')}"
                    comissao.save(update_fields=['status', 'data_pagamento', 'observacoes'])
                    quantidade_atualizada += 1
                    
                    logger.info(
                        f"[webhook] Comissão {comissao.tipo_comissao} ATUALIZADA para paga: "
                        f"{comissao.usuario.email} - Parcela {parcela.numero_parcela} - R$ {comissao.valor_comissao:.2f}"
                    )
                
                if quantidade_atualizada > 0:
                    LogService.registrar(
                        nivel='INFO',
                        mensagem=f"Comissões da parcela {parcela.numero_parcela} ATUALIZADAS para paga: {quantidade_atualizada} comissões - Venda {parcela.venda.id}",
                        modulo='comissoes',
                        acao='comissoes_parcela_atualizadas'
                    )
                else:
                    logger.warning(f"[webhook] Nenhuma comissão encontrada para parcela {parcela.numero_parcela} - Venda {parcela.venda.id}")
                    
            except Exception as e_comissao:
                logger.error(f"[webhook] Erro ao atualizar comissões da parcela: {str(e_comissao)}")
                LogService.registrar(
                    nivel='ERROR',
                    mensagem=f"Erro ao atualizar comissões da parcela: {str(e_comissao)}",
                    modulo='comissoes',
                    acao='erro_atualizar_comissoes_parcela'
                )
            
            # Verificar se todas as parcelas foram pagas
            _verificar_venda_quitada(parcela.venda)
            
            return True
            
        except Parcela.DoesNotExist:
            logger.warning(f"[webhook] Payment ID {payment_id} não encontrado em PIX Levantamento, PIX Entrada nem Parcela")
            LogService.registrar(
                nivel='WARNING',
                mensagem=f"Payment ID {payment_id} não encontrado no sistema",
                modulo='financeiro',
                acao='payment_nao_encontrado'
            )
            return True  # Retorna sucesso para não reenviar
        
    except Exception as e:
        logger.error(f"[webhook] Erro ao processar pagamento confirmado: {str(e)}", exc_info=True)
        return False


def _processar_pagamento_vencido(payment_data):
    """Processa pagamento vencido"""
    payment_id = payment_data.get('id')
    
    logger.info(f"[webhook] Processando pagamento vencido: {payment_id}")
    
    try:
        from financeiro.models import PixLevantamento, Parcela
        
        # Tentar PIX Levantamento
        try:
            pix_levantamento = PixLevantamento.objects.get(asaas_payment_id=payment_id)
            pix_levantamento.status_pagamento = 'vencido'
            pix_levantamento.save(update_fields=['status_pagamento'])
            
            if pix_levantamento.lead:
                pix_levantamento.lead.status = 'PERDIDO'
                pix_levantamento.lead.save(update_fields=['status'])
            
            logger.info(f"[webhook] PIX Levantamento vencido: {payment_id}")
            return True
            
        except PixLevantamento.DoesNotExist:
            pass
        
        # Tentar Parcela
        try:
            parcela = Parcela.objects.get(id_asaas=payment_id)
            parcela.status = 'vencida'
            parcela.save(update_fields=['status'])
            
            logger.info(f"[webhook] Parcela vencida: {payment_id}")
            return True
            
        except Parcela.DoesNotExist:
            logger.warning(f"[webhook] Payment vencido não encontrado: {payment_id}")
            return True
        
    except Exception as e:
        logger.error(f"[webhook] Erro ao processar vencido: {str(e)}", exc_info=True)
        return False


def _processar_pagamento_deletado(payment_data):
    """Processa cobrança deletada"""
    payment_id = payment_data.get('id')
    
    logger.info(f"[webhook] Cobrança deletada: {payment_id}")
    
    LogService.registrar(
        nivel='INFO',
        mensagem=f"Cobrança deletada no ASAAS: {payment_id}",
        modulo='financeiro',
        acao='cobranca_deletada'
    )
    
    return True


def _processar_pagamento_estornado(payment_data):
    """Processa pagamento estornado"""
    payment_id = payment_data.get('id')
    value = payment_data.get('value')
    
    logger.info(f"[webhook] Pagamento estornado: {payment_id} - R$ {value}")
    
    try:
        from financeiro.models import Parcela
        
        try:
            parcela = Parcela.objects.get(id_asaas=payment_id)
            parcela.status = 'cancelada'
            parcela.data_pagamento = None
            parcela.save(update_fields=['status', 'data_pagamento'])
            
            LogService.registrar(
                nivel='WARNING',
                mensagem=f"Pagamento estornado: Venda {parcela.venda.id} - Parcela {parcela.numero_parcela} - R$ {value}",
                modulo='financeiro',
                acao='pagamento_estornado'
            )
            
            return True
            
        except Parcela.DoesNotExist:
            logger.warning(f"[webhook] Parcela para estorno não encontrada: {payment_id}")
            return True
        
    except Exception as e:
        logger.error(f"[webhook] Erro ao processar estorno: {str(e)}", exc_info=True)
        return False


def _verificar_venda_quitada(venda):
    """Verifica se todas as parcelas foram pagas e atualiza status da venda"""
    from financeiro.models import Parcela
    
    total_parcelas = Parcela.objects.filter(venda=venda).count()
    parcelas_pagas = Parcela.objects.filter(venda=venda, status='paga').count()
    
    if total_parcelas == parcelas_pagas and total_parcelas > 0:
        logger.info(f"[webhook] Venda {venda.id} quitada - {parcelas_pagas}/{total_parcelas} parcelas pagas")
        
        LogService.registrar(
            nivel='INFO',
            mensagem=f"Venda {venda.id} totalmente quitada",
            modulo='financeiro',
            acao='venda_quitada'
        )


# ==================== VISUALIZAÇÃO DE LOGS DE WEBHOOK ====================

@login_required
def webhook_logs(request):
    """Visualizar histórico de webhooks recebidos"""
    from django.core.paginator import Paginator
    from .models import WebhookLog
    from django.shortcuts import get_object_or_404
    
    logs = WebhookLog.objects.all().order_by('-data_recebimento')
    
    # Filtros
    tipo = request.GET.get('tipo')
    evento = request.GET.get('evento')
    status = request.GET.get('status')
    payment_id = request.GET.get('payment_id')
    
    if tipo:
        logs = logs.filter(tipo=tipo)
    if evento:
        logs = logs.filter(evento__icontains=evento)
    if status:
        logs = logs.filter(status_processamento=status)
    if payment_id:
        logs = logs.filter(payment_id__icontains=payment_id)
    
    # Paginação
    paginator = Paginator(logs, 50)
    page = request.GET.get('page', 1)
    logs_page = paginator.get_page(page)
    
    # Estatísticas
    stats = {
        'total': WebhookLog.objects.count(),
        'success': WebhookLog.objects.filter(status_processamento='SUCCESS').count(),
        'error': WebhookLog.objects.filter(status_processamento='ERROR').count(),
        'ignored': WebhookLog.objects.filter(status_processamento='IGNORED').count(),
    }
    
    # Montar dict customer_id -> nome_completo e adicionar ao objeto log
    for log in logs_page:
        customer_id = getattr(log, 'customer_id', None)
        log.nome_cliente = None
        if customer_id:
            try:
                cliente_asaas = ClienteAsaas.objects.select_related('lead').get(asaas_customer_id=customer_id)
                log.nome_cliente = cliente_asaas.lead.nome_completo
            except ClienteAsaas.DoesNotExist:
                log.nome_cliente = None

    context = {
        'logs': logs_page,
        'stats': stats,
        'filtros': {
            'tipo': tipo,
            'evento': evento,
            'status': status,
            'payment_id': payment_id,
        },
    }
    
    return render(request, 'core/webhook_logs.html', context)


@login_required
def webhook_log_detalhe(request, log_id):
    """Visualizar detalhes de um webhook específico"""
    from .models import WebhookLog
    from django.shortcuts import get_object_or_404
    
    log = get_object_or_404(WebhookLog, id=log_id)
    
    nome_cliente = None
    if log.customer_id:
        try:
            cliente_asaas = ClienteAsaas.objects.select_related('lead').get(asaas_customer_id=log.customer_id)
            nome_cliente = cliente_asaas.lead.nome_completo
        except ClienteAsaas.DoesNotExist:
            nome_cliente = None
    
    context = {
        'log': log,
        'payload_formatado': json.dumps(log.payload, indent=2, ensure_ascii=False),
        'nome_cliente': nome_cliente,
    }
    
    return render(request, 'core/webhook_log_detalhe.html', context)


@login_required
@permission_required('core.change_configuracaosistema')
def resend_pending_webhooks(request):
    """
    Busca e reenvia todos os webhooks pendentes do Asaas
    """
    from .asaas_webhook_manager import AsaasWebhookManager
    import json
    
    if request.method == 'POST':
        try:
            # Inicializar gerenciador de webhooks
            webhook_manager = AsaasWebhookManager()
            
            # Obter limite (padrão 100)
            max_webhooks = int(request.POST.get('max_webhooks', 100))
            
            # Reenviar webhooks pendentes
            result = webhook_manager.resend_all_pending(max_webhooks=max_webhooks)
            
            if result['success']:
                succeeded = result['succeeded']
                failed = result['failed']
                processed = result['processed']
                total_pending = result['total_pending']
                has_more = result.get('has_more', False)
                
                if processed == 0:
                    messages.info(
                        request,
                        '✅ Nenhum webhook pendente encontrado no momento.'
                    )
                else:
                    # Criar mensagem detalhada
                    msg = f'✅ Processados {processed} webhooks: {succeeded} reenviados com sucesso, {failed} falharam.'
                    
                    if has_more:
                        msg += f' (Ainda existem mais webhooks pendentes, total: {total_pending})'
                    
                    messages.success(request, msg)
                    
                    # Se houver falhas, listar detalhes
                    if failed > 0:
                        failed_webhooks = [r for r in result['results'] if not r['success']]
                        details = '<br>'.join([
                            f"• Webhook {r['webhook_id']} ({r.get('event', 'unknown')}): {r.get('error', 'Erro desconhecido')}"
                            for r in failed_webhooks[:5]  # Mostrar apenas os 5 primeiros
                        ])
                        messages.warning(request, f'Falhas detectadas:<br>{details}')
            else:
                messages.error(
                    request,
                    f'❌ Erro ao processar webhooks: {result.get("error", "Erro desconhecido")}'
                )
        
        except Exception as e:
            messages.error(
                request,
                f'❌ Erro inesperado ao reenviar webhooks: {str(e)}'
            )
    
    return redirect('core:painel_configuracoes')


@login_required
@permission_required('core.change_configuracaosistema')
def webhook_statistics(request):
    """
    Retorna estatísticas dos webhooks recebidos e processados
    """
    from .models import WebhookLog
    from django.db.models import Count, Q, Sum
    import datetime
    
    try:
        # Últimas 24 horas
        data_24h = timezone.now() - datetime.timedelta(hours=24)
        # Últimos 7 dias
        data_7d = timezone.now() - datetime.timedelta(days=7)
        # Último mês
        data_30d = timezone.now() - datetime.timedelta(days=30)
        
        # Estatísticas gerais
        stats_24h = WebhookLog.objects.filter(data_recebimento__gte=data_24h).aggregate(
            total=Count('id'),
            sucesso=Count('id', filter=Q(status_processamento='SUCCESS')),
            erro=Count('id', filter=Q(status_processamento='ERROR')),
            ignorado=Count('id', filter=Q(status_processamento='IGNORED'))
        )
        
        stats_7d = WebhookLog.objects.filter(data_recebimento__gte=data_7d).aggregate(
            total=Count('id'),
            sucesso=Count('id', filter=Q(status_processamento='SUCCESS')),
            erro=Count('id', filter=Q(status_processamento='ERROR'))
        )
        
        stats_30d = WebhookLog.objects.filter(data_recebimento__gte=data_30d).aggregate(
            total=Count('id'),
            sucesso=Count('id', filter=Q(status_processamento='SUCCESS'))
        )
        
        # Eventos mais comuns
        eventos_comuns = list(WebhookLog.objects.filter(
            data_recebimento__gte=data_7d
        ).values('evento').annotate(
            count=Count('id')
        ).order_by('-count')[:5])
        
        # Últimos erros
        ultimos_erros = WebhookLog.objects.filter(
            status_processamento='ERROR',
            data_recebimento__gte=data_7d
        ).values('evento', 'mensagem_erro', 'data_recebimento')[:5]
        
        return JsonResponse({
            'success': True,
            'periodo_24h': stats_24h,
            'periodo_7d': stats_7d,
            'periodo_30d': stats_30d,
            'eventos_comuns': eventos_comuns,
            'ultimos_erros': list(ultimos_erros),
            'total_historico': WebhookLog.objects.count(),
            'nota': 'Estatísticas baseadas nos webhooks recebidos e processados pelo sistema'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@permission_required('core.change_configuracaosistema')
def list_pending_webhooks(request):
    """
    Lista webhooks recebidos e seu status de processamento
    Nota: A API do Asaas não fornece lista de eventos pendentes no sandbox,
    então mostramos os webhooks recebidos pelo sistema.
    """
    from .models import WebhookLog
    from django.db.models import Count, Q
    import datetime
    
    try:
        # Últimas 24 horas
        data_limite = timezone.now() - datetime.timedelta(hours=24)
        
        # Estatísticas dos webhooks recebidos
        stats = WebhookLog.objects.filter(
            data_recebimento__gte=data_limite
        ).aggregate(
            total=Count('id'),
            sucesso=Count('id', filter=Q(status_processamento='SUCCESS')),
            erro=Count('id', filter=Q(status_processamento='ERROR')),
            ignorado=Count('id', filter=Q(status_processamento='IGNORED'))
        )
        
        # Últimos webhooks recebidos
        limit = int(request.GET.get('limit', 20))
        webhooks = WebhookLog.objects.all()[:limit]
        
        webhooks_data = [{
            'id': w.id,
            'evento': w.evento or 'Desconhecido',
            'status': w.status_processamento,
            'payment_id': w.payment_id,
            'valor': float(w.valor) if w.valor else 0,
            'data_recebimento': w.data_recebimento.strftime('%d/%m/%Y %H:%M:%S'),
            'mensagem_erro': w.mensagem_erro if w.status_processamento == 'ERROR' else None
        } for w in webhooks]
        
        return JsonResponse({
            'success': True,
            'stats': stats,
            'data': webhooks_data,
            'totalCount': WebhookLog.objects.count(),
            'periodo': '24h',
            'nota': 'Mostrando webhooks recebidos pelo sistema (últimas 24h)'
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
