from datetime import timedelta   
from django.views.decorators.http import require_POST
import logging
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.views.decorators.http import require_http_methods
import json
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage



# IMPORTAR SERVIÇOS DO CORE
from core.services import LogService, NotificacaoService, ConfiguracaoService
from core.asaas_service import asaas_service
from core.utils import Validadores, FormularioUtils
from core.webhook_handlers import webhook_handler

# IMPORTAR FORMULÁRIOS E MODELOS LOCAIS
from marketing.models import Lead, OrigemContato, OrigemLead
from financeiro.views import criar_cliente_asaas
from comissoes.models import ComissaoLead
from financeiro.models import PixLevantamento, ClienteAsaas

from django.views.decorators.cache import never_cache

# Obter o logger correto
logger = logging.getLogger(__name__)

def autenticar_via_token(request, token):
    """
    Autenticação segura via token JWT com validações
    """
    try:
        # Validação básica do token
        if not token or len(token) < 10:
            return {'success': False, 'error': 'Token inválido'}
        
        from rest_framework_simplejwt.tokens import AccessToken
        from django.contrib.auth import get_user_model
        from django.contrib.auth import login
        
        # Decodifica e valida o token
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        
        # Verifica expiração
        from django.utils import timezone
        if access_token['exp'] < timezone.now().timestamp():
            return {'success': False, 'error': 'Token expirado'}
        
        # Busca usuário
        User = get_user_model()
        user = User.objects.get(id=user_id)
        
        # Verifica se usuário está ativo
        if not user.is_active:
            return {'success': False, 'error': 'Usuário inativo'}
        
        # Realiza login na sessão
        user.backend = 'django.contrib.auth.backends.ModelBackend'
        login(request, user)
        
        return {'success': True, 'user': user}
        
    except Exception as e:
        logger.error(f"Erro autenticação token: {str(e)}")
        return {'success': False, 'error': str(e)}

def get_client_ip(request):
    """Obtém IP real do cliente"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip



@never_cache
@require_http_methods(["GET", "POST"])
def novo_atendimento(request):
    """
    Novo atendimento com autenticação híbrida segura
    """
    
    # USAR CONFIGURAÇÃO DO CORE
    valor_consulta_padrao = ConfiguracaoService.obter_config(
        'VALOR_CONSULTA_PADRAO', 
        29.90
    )
    
    # === FASE 1: AUTENTICAÇÃO HÍBRIDA SEGURA ===
    token = request.GET.get('token')
    
    if token and not request.user.is_authenticated:
        auth_result = autenticar_via_token(request, token)
        if auth_result['success']:
            # USAR LOG SERVICE DO CORE
            LogService.registrar(
                usuario=auth_result['user'],
                nivel='INFO',
                mensagem=f"Autenticação via token bem-sucedida",
                modulo='atendimento',
                acao='autenticacao_token',
                ip=get_client_ip(request)
            )
            response = redirect('atendimento:novo_atendimento')
            return response
        else:
            LogService.registrar(
                nivel='WARNING',
                mensagem=f"Falha autenticação token: {auth_result['error']}",
                modulo='atendimento',
                acao='autenticacao_falha',
                ip=get_client_ip(request)
            )
            return redirect(f'/accounts/login/?next=/atendimento/novo/')
    
    if not request.user.is_authenticated:
        LogService.registrar(
            nivel='WARNING',
            mensagem="Acesso não autorizado a novo_atendimento",
            modulo='atendimento',
            acao='acesso_nao_autorizado',
            ip=get_client_ip(request)
        )
        return redirect(f'/accounts/login/?next=/atendimento/novo/')
    
    # LOG DE AUDITORIA COM SERVIÇO DO CORE
    LogService.registrar(
        usuario=request.user,
        nivel='INFO',
        mensagem=f"Acesso autorizado ao formulário de atendimento",
        modulo='atendimento',
        acao='acesso_formulario',
        ip=get_client_ip(request)
    )
    
    # === LÓGICA PRINCIPAL DA VIEW ===
    if request.method == 'POST':
        return processar_formulario_atendimento(request, valor_consulta_padrao)
    else:
        return exibir_formulario_atendimento(request, valor_consulta_padrao)
    


@login_required
def exibir_formulario_atendimento(request, valor_consulta_padrao=None):
    """Exibe formulário vazio para novo atendimento"""
    form = None  # Formulário removido, usar campos do Lead
    valor_consulta = float(valor_consulta_padrao or ConfiguracaoService.obter_config('VALOR_CONSULTA_PADRAO', 29.90))
    origens = OrigemLead.objects.filter(ativo=True).order_by('nome')
    return render(request, 'atendimento/novo_atendimento.html', {
        'form': form,
        'valor_consulta': valor_consulta,
        'origens': origens
    })


@login_required
@require_http_methods(["POST"])
def buscar_lead_por_cpf_cnpj(request):
    """
    API para buscar lead existente por CPF/CNPJ
    Retorna dados do lead + informações sobre pré-vendas e levantamentos
    """
    try:
        data = json.loads(request.body)
        cpf_cnpj = data.get('cpf_cnpj', '').strip()
        
        if not cpf_cnpj:
            return JsonResponse({
                'success': False,
                'message': 'CPF/CNPJ não informado.'
            })
        
        # Remove caracteres especiais para busca
        cpf_cnpj_limpo = ''.join(filter(str.isdigit, cpf_cnpj))
        
        # Busca lead por CPF/CNPJ (com ou sem formatação)
        # Usa .first() para pegar apenas o mais recente se houver múltiplos
        from django.db.models import Q
        leads = Lead.objects.filter(
            Q(cpf_cnpj=cpf_cnpj) | Q(cpf_cnpj=cpf_cnpj_limpo)
        ).order_by('-data_cadastro')
        
        # Verifica se há múltiplos leads com mesmo CPF/CNPJ
        total_leads = leads.count()
        if total_leads == 0:
            return JsonResponse({
                'success': False,
                'encontrado': False,
                'message': 'Nenhum lead encontrado com este CPF/CNPJ.'
            })
        
        # Pega o lead mais recente
        lead = leads.first()
        
        # Busca informações de pré-vendas e levantamentos
        from vendas.models import PreVenda
        pre_vendas = PreVenda.objects.filter(lead=lead).order_by('-data_criacao')
        pix_levantamento = PixLevantamento.objects.filter(lead=lead).order_by('-data_criacao').first()
        
        # Monta resposta com dados do lead
        response_data = {
            'success': True,
            'encontrado': True,
            'total_leads_encontrados': total_leads,  # Informa se há duplicatas
            'lead': {
                'id': lead.id,
                'nome_completo': lead.nome_completo,
                'telefone': lead.telefone,
                'email': lead.email or '',
                'cpf_cnpj': lead.cpf_cnpj,
                'status': lead.status,
                'status_display': lead.get_status_display(),
                'fez_levantamento': lead.fez_levantamento,
                'origem_id': lead.origem.id if lead.origem else None,
                'origem_nome': lead.origem.nome if lead.origem else None,
                'captador_id': lead.captador.id if lead.captador else None,
                'captador_nome': lead.captador.get_full_name() if lead.captador else None,
                'data_cadastro': lead.data_cadastro.strftime('%d/%m/%Y %H:%M'),
            },
            'historico': {
                'tem_levantamento': pix_levantamento is not None,
                'levantamento_pago': pix_levantamento.status_pagamento == 'pago' if pix_levantamento else False,
                'total_pre_vendas': pre_vendas.count(),
                'ultima_pre_venda': None,
                'tem_pre_venda_ativa': False,
            },
            'situacao': 'novo'  # novo, reativacao, levantamento_feito
        }
        
        # Alerta se há múltiplos leads com mesmo CPF/CNPJ
        if total_leads > 1:
            response_data['aviso'] = f'Atenção: Existem {total_leads} leads com este CPF/CNPJ. Usando o mais recente (ID: {lead.id}).'
        
        # Analisa situação do lead para definir fluxo de reativação
        if pre_vendas.exists():
            ultima = pre_vendas.first()
            response_data['historico']['ultima_pre_venda'] = {
                'status': ultima.status,
                'status_display': ultima.get_status_display(),
                'servico': ultima.servico_interesse,
                'valor_proposto': float(ultima.valor_proposto) if ultima.valor_proposto else None,
                'data': ultima.data_criacao.strftime('%d/%m/%Y %H:%M'),
                'motivo_recusa': ultima.motivo_recusa if ultima.status == 'RECUSADO' else None,
            }
            
            # Verifica se tem pré-venda pendente/ativa
            if ultima.status in ['PENDENTE', 'ACEITO']:
                response_data['historico']['tem_pre_venda_ativa'] = True
                response_data['situacao'] = 'pre_venda_ativa'
            else:
                response_data['situacao'] = 'reativacao'
        
        # Se fez levantamento mas não tem pré-venda ativa
        if lead.fez_levantamento and pix_levantamento and pix_levantamento.status_pagamento == 'pago':
            if not response_data['historico']['tem_pre_venda_ativa']:
                response_data['situacao'] = 'levantamento_feito'
        
        return JsonResponse(response_data)
        
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Dados inválidos.'
        })
    except Exception as e:
        logger.error(f"Erro ao buscar lead por CPF/CNPJ: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': f'Erro ao buscar lead: {str(e)}'
        })


# View para salvar lead sem levantamento
@login_required
@require_POST
def salvar_lead_sem_levantamento(request):
    """Salva os dados do lead quando NÃO fez levantamento"""
    try:
        nome_completo = request.POST.get('nome_completo', '').strip()
        telefone = request.POST.get('telefone', '').strip()
        email = request.POST.get('email', '').strip()
        cpf_cnpj = request.POST.get('cpf_cnpj', '').strip()
        origem_id = request.POST.get('origem')
        captador_id = request.POST.get('captador')

        if not nome_completo or not telefone:
            return JsonResponse({'success': False, 'message': 'Nome e telefone são obrigatórios.'})
        
        # Validar CPF/CNPJ se fornecido - remove caracteres não numéricos antes de validar
        if cpf_cnpj:
            import re
            cpf_cnpj_limpo = re.sub(r'\D', '', cpf_cnpj)
            if len(cpf_cnpj_limpo) == 11:  # CPF
                if not Validadores.validar_cpf(cpf_cnpj_limpo):
                    return JsonResponse({'success': False, 'message': 'CPF inválido.'})
                cpf_cnpj = cpf_cnpj_limpo
            elif len(cpf_cnpj_limpo) == 14:  # CNPJ
                if not Validadores.validar_cnpj(cpf_cnpj_limpo):
                    return JsonResponse({'success': False, 'message': 'CNPJ inválido.'})
                cpf_cnpj = cpf_cnpj_limpo
            elif cpf_cnpj_limpo:  # Se tem valor mas não é 11 nem 14 dígitos
                return JsonResponse({'success': False, 'message': 'CPF ou CNPJ inválido.'})
        
        # E-mail obrigatório? (config)
        obrigar_email = ConfiguracaoService.obter_config('LEAD_OBRIGAR_EMAIL', False)
        if obrigar_email and not email:
            return JsonResponse({'success': False, 'message': 'E-mail é obrigatório.'})
        if not origem_id:
            return JsonResponse({'success': False, 'message': 'Origem do lead é obrigatória.'})

        from marketing.models import Lead, OrigemLead
        try:
            origem = OrigemLead.objects.get(id=origem_id)
        except OrigemLead.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Origem do lead inválida.'})

        from django.contrib.auth import get_user_model
        User = get_user_model()
        captador = None
        if captador_id:
            try:
                captador = User.objects.get(id=captador_id)
            except User.DoesNotExist:
                pass
        status_inicial = str(ConfiguracaoService.obter_config('LEAD_STATUS_INICIAL', 'NOVO') or 'NOVO')
        lead, created = Lead.objects.get_or_create(
            telefone=telefone,
            defaults={
                'nome_completo': nome_completo,
                'email': email,
                'cpf_cnpj': cpf_cnpj,
                'origem': origem,
                'status': status_inicial,
                'captador': captador or request.user,
                'atendente': request.user,
            }
        )
        if not created:
            # Atualiza dados se já existe
            lead.nome_completo = nome_completo
            lead.email = email
            lead.cpf_cnpj = cpf_cnpj
            lead.origem = origem
            lead.captador = captador or request.user
            lead.atendente = request.user
            lead.status = status_inicial
            lead.save()

        return JsonResponse({'success': True, 'lead_id': lead.id, 'message': 'Lead salvo com sucesso.'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Erro ao salvar lead: {str(e)}'})
 

@login_required
@require_http_methods(["POST"])
def salvar_lead_api(request):
    """API para salvar apenas o lead (Etapa 1)"""

    try:
        # Obter dados do formulário
        nome_completo = request.POST.get('nome_completo', '').strip()
        telefone = request.POST.get('telefone', '').strip()
        email = request.POST.get('email', '').strip()
        cpf_cnpj = request.POST.get('cpf_cnpj', '').strip()
        origem_id = request.POST.get('origem')  # Recebe o ID da origem
        captador_id = request.POST.get('captador')

        # Validar CPF/CNPJ - remove caracteres não numéricos antes de validar
        if cpf_cnpj:
            import re
            cpf_cnpj_limpo = re.sub(r'\D', '', cpf_cnpj)
            if len(cpf_cnpj_limpo) == 11:  # CPF
                if not Validadores.validar_cpf(cpf_cnpj_limpo):
                    return JsonResponse({'success': False, 'message': 'CPF inválido.'})
                cpf_cnpj = cpf_cnpj_limpo  # Atualiza para o valor limpo
            elif len(cpf_cnpj_limpo) == 14:  # CNPJ
                if not Validadores.validar_cnpj(cpf_cnpj_limpo):
                    return JsonResponse({'success': False, 'message': 'CNPJ inválido.'})
                cpf_cnpj = cpf_cnpj_limpo  # Atualiza para o valor limpo
            else:
                return JsonResponse({'success': False, 'message': 'CPF ou CNPJ inválido.'})

        # Validar outros campos obrigatórios conforme política do painel
        obrigar_email = ConfiguracaoService.obter_config('LEAD_OBRIGAR_EMAIL', False)
        validacao = FormularioUtils.validar_etapa_lead(
            nome_completo,
            telefone,
            email if obrigar_email else None
        )
        if not validacao['valido']:
            return JsonResponse({
                'success': False,
                'message': validacao['erros'][0] if validacao['erros'] else 'Dados inválidos'
            })

        if not origem_id:
            return JsonResponse({'success': False, 'message': 'Origem do lead é obrigatória'})

        # Buscar a origem no banco de dados
        try:
            origem = OrigemLead.objects.get(id=origem_id)
        except OrigemLead.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Origem do lead inválida'})

        # Salvar ou atualizar o lead
        from django.contrib.auth import get_user_model
        User = get_user_model()
        captador = None
        if captador_id:
            try:
                captador = User.objects.get(id=captador_id)
            except User.DoesNotExist:
                captador = None
        status_inicial = str(ConfiguracaoService.obter_config('LEAD_STATUS_INICIAL', 'CONTATADO') or 'CONTATADO')
        lead, created = Lead.objects.get_or_create(
            telefone=telefone,
            defaults={
                'nome_completo': nome_completo,
                'email': email,
                'cpf_cnpj': cpf_cnpj,
                'origem': origem,
                'status': status_inicial,
                'captador': captador or request.user,
                'atendente': request.user,
            }
        )

        if not created:
            # Atualizar os dados do lead existente
            lead.nome_completo = nome_completo
            lead.email = email
            lead.cpf_cnpj = cpf_cnpj
            lead.origem = origem
            lead.status = status_inicial
            lead.data_atualizacao = timezone.now()
            lead.save()

        # Registrar log de criação ou atualização
        LogService.registrar(
            usuario=request.user,
            nivel='INFO',
            mensagem=f'Lead {"criado" if created else "atualizado"}: {nome_completo}',
            modulo='atendimento',
            acao='CRIAR_LEAD' if created else 'ATUALIZAR_LEAD',
            ip=get_client_ip(request)
        )

        return JsonResponse({
            'success': True,
            'lead_id': lead.id,
            'message': f'Lead {"criado" if created else "atualizado"} com sucesso!'
        })

    except Exception as e:
        LogService.registrar(
            usuario=request.user,
            nivel='ERROR',
            mensagem=f'Erro ao salvar lead: {str(e)}',
            modulo='atendimento',
            acao='ERRO_LEAD',
            ip=get_client_ip(request)
        )
        return JsonResponse({'success': False, 'message': f'Erro interno: {str(e)}'})


def processar_formulario_atendimento(request, valor_consulta):
    """Processa o formulário de atendimento usando serviços do core"""
    form = None  # Formulário removido, usar campos do Lead
    
    if form.is_valid():
        try:
            # Salva o atendimento
            atendimento = form.save(commit=False)
            atendimento.atendente = request.user
            atendimento.valor_consulta = valor_consulta  # Usa valor configurado
            atendimento.save()
            
            #LOG DE CRIAÇÃO COM SERVIÇO DO CORE
            LogService.registrar(
                usuario=request.user,
                nivel='INFO',
                mensagem=f"Novo atendimento criado - ID: {atendimento.id}, Cliente: {atendimento.nome_completo}",
                modulo='atendimento',
                acao='criacao_atendimento',
                ip=get_client_ip(request)
            )
            
            #VALIDAÇÃO DE TELEFONE COM UTILS DO CORE
            if not Validadores.validar_telefone(atendimento.telefone):
                form.add_error('telefone', 'Telefone inválido')
                return render(request, 'atendimento/novo_atendimento.html', {'form': form})
            
            # Formata dados do Lead para o ASAAS
            lead = getattr(atendimento, 'lead', None)
            if lead is None:
                # Se não houver lead vinculado, buscar pelo telefone/email
                lead = Lead.objects.filter(telefone=atendimento.telefone).first()
            if lead:
                customer_data = asaas_service.formatar_dados_lead(lead)
                customer_response = asaas_service.criar_cliente(customer_data)
            else:
                customer_data = None
                customer_response = None
            
            if customer_response and 'id' in customer_response:
                customer_id = customer_response['id']
                # Cria cobrança PIX usando dados do Lead
                cobranca_data = {
                    'customer_id': customer_id,
                    'billing_type': 'PIX',
                    'value': float(valor_consulta),
                    'dueDate': timezone.now().date().isoformat(),
                    'description': f'Taxa de levantamento - {lead.nome_completo if lead else atendimento.nome_completo}',
                    'externalReference': f'atendimento_{atendimento.id}'
                }
                payment_response = asaas_service.criar_cobranca(cobranca_data)
                
                if payment_response and 'id' in payment_response:
                    # Obtém QR Code PIX
                    pix_data = asaas_service.obter_qr_code_pix(payment_response['id'])
                    
                    if pix_data:
                        atendimento.asaas_payment_id = payment_response['id']
                        atendimento.pix_code = pix_data.get('payload', '')
                        atendimento.pix_qr_code = pix_data.get('encodedImage', '')
                        atendimento.status = 'AGUARDANDO_PAGAMENTO'
                        atendimento.save()
                        
                        #NOTIFICAÇÃO DE SUCESSO
                        NotificacaoService.criar_notificacao(
                            usuario=request.user,
                            titulo='PIX Gerado com Sucesso',
                            mensagem=f'PIX gerado para {atendimento.nome_completo} - R$ {valor_consulta}',
                            tipo='SUCESSO',
                            link=f'/atendimento/{atendimento.id}/'
                        )
                        
                        LogService.registrar(
                            usuario=request.user,
                            nivel='INFO',
                            mensagem=f"PIX gerado - Atendimento ID: {atendimento.id}, Valor: R$ {valor_consulta}",
                            modulo='atendimento',
                            acao='pix_gerado',
                            ip=get_client_ip(request)
                        )
                        
                        context = {
                            'atendimento': atendimento,
                            'pix_data': {
                                'payload': pix_data.get('payload', ''),
                                'encodedImage': pix_data.get('encodedImage', ''),
                                'valor_formatado': Validadores.formatar_moeda(valor_consulta)
                            }
                        }
                        
                        return render(request, 'atendimento/pix_gerado.html', context)
            
            # Se algo deu errado
            LogService.registrar(
                usuario=request.user,
                nivel='ERROR',
                mensagem=f"Erro ao gerar PIX - Atendimento ID: {atendimento.id}",
                modulo='atendimento',
                acao='erro_pix',
                ip=get_client_ip(request)
            )
            form.add_error(None, 'Erro ao gerar PIX. Tente novamente.')
            
        except Exception as e:
            logger.error(f"Erro processar atendimento: {str(e)}")
            LogService.registrar(
                usuario=request.user,
                nivel='ERROR',
                mensagem=f"Erro processar atendimento: {str(e)}",
                modulo='atendimento',
                acao='erro_processamento',
                ip=get_client_ip(request)
            )
            form.add_error(None, f'Erro no sistema: {str(e)}')
    
    return render(request, 'atendimento/novo_atendimento.html', {'form': form})


#@login_required
#@require_http_methods(["POST"])
# def salvar_atendimento_api(request):
#     """API para salvar atendimento e gerar PIX (Etapa 2)"""
#     lead_id = request.POST.get('lead_id')
#     
#     if not lead_id:
#         return JsonResponse({'success': False, 'message': 'Lead ID é obrigatório'})
#     
#     try:
#         lead = Lead.objects.get(id=lead_id)
#         
#         # Criar obj atendimento
    # atendimento removido, fluxo agora é pelo Lead
#             lead=lead,
#             nome_completo=lead.nome_completo,
#             telefone=lead.telefone,
#             email=lead.email,
#             origem=request.POST.get('origem'),
#             motivo=request.POST.get('motivo'),
#             perfil_emocional=request.POST.get('perfil_emocional'),
#             valor_consulta=float(ConfiguracaoService.obter_config('VALOR_CONSULTA_PADRAO', 29.90)),
#             atendente=request.user,
#             observacoes=request.POST.get('observacoes', ''),
#         )
#         
#         # Gerar PIX usando FormularioUtils
#         valor_consulta = float(ConfiguracaoService.obter_config('VALOR_CONSULTA_PADRAO', 29.90))
#         descricao_pix = f"Consulta {lead.nome_completo[:20]}"
#         codigo_pix = FormularioUtils.gerar_codigo_pix(valor_consulta, descricao_pix)
#         
#         # Salvar o código PIX no atendimento
#         atendimento.codigo_pix = codigo_pix
#         atendimento.save()
#         
#         # Registrar log
#         LogService.registrar(
#             usuario=request.user,
#             nivel='INFO',
#             mensagem=f'Atendimento criado para {lead.nome_completo}',
#             modulo='atendimento',
#             acao='CRIAR_ATENDIMENTO',
#             ip=get_client_ip(request)
#         )
#         
#         return JsonResponse({
#             'success': True,
#             'atendimento_id': atendimento.id,
#             'message': 'Atendimento criado e PIX gerado com sucesso!'
#         })
#         
#     except Lead.DoesNotExist:
#         return JsonResponse({'success': False, 'message': 'Lead não encontrado'})
#     except Exception as e:
#         LogService.registrar(
#             usuario=request.user,
#             nivel='ERROR',
#             mensagem=f'Erro ao salvar atendimento: {str(e)}',
#             modulo='atendimento',
#             acao='ERRO_ATENDIMENTO',
#             ip=get_client_ip(request)
#         )
#         return JsonResponse({'success': False, 'message': f'Erro interno: {str(e)}'})


@login_required
def gerar_pix_api(request, lead_id):
    """API para gerar PIX para um lead"""
    try:
        lead = Lead.objects.get(id=lead_id)
        
        logger.info(f"Iniciando geração de PIX para lead {lead_id}: {lead.nome_completo}")
        
        # Validar CPF/CNPJ obrigatório
        exigir_cpf = ConfiguracaoService.obter_config('LEAD_OBRIGAR_CPF_PARA_LEVANTAMENTO', True)
        if exigir_cpf and not lead.cpf_cnpj:
            logger.warning(f"Lead {lead_id} sem CPF/CNPJ")
            return JsonResponse({
                'success': False,
                'message': 'CPF ou CNPJ do lead é obrigatório para gerar o PIX.'
            })
        
        logger.info(f"Lead {lead_id} validado com CPF/CNPJ: {lead.cpf_cnpj}")
        
        # ESTRATÉGIA ROBUSTA: Sempre recriar cliente ASAAS ao gerar PIX pelo painel
        # Isso garante sincronização total com os dados atuais do lead
        
        # 1. Verificar se já existe cliente ASAAS
        cliente_asaas_antigo = ClienteAsaas.objects.filter(lead=lead).first()
        
        if cliente_asaas_antigo:
            logger.info(f"Cliente ASAAS antigo encontrado: {cliente_asaas_antigo.asaas_customer_id} - Excluindo para recriar")
            
            # Deletar cliente no ASAAS
            try:
                asaas_service.excluir_cliente(cliente_asaas_antigo.asaas_customer_id)
                logger.info(f"Cliente {cliente_asaas_antigo.asaas_customer_id} deletado no ASAAS")
            except Exception as e:
                logger.warning(f"Erro ao deletar cliente no ASAAS (continuando): {str(e)}")
            
            # Deletar registro local
            cliente_asaas_antigo.delete()
            logger.info("Registro local do cliente antigo deletado")
        
        # 2. Criar novo cliente ASAAS com dados atualizados do lead
        logger.info(f"Criando novo cliente ASAAS para lead {lead_id}")
        try:
            cliente_asaas = criar_cliente_asaas(lead)
            logger.info(f"Cliente ASAAS criado com sucesso: {cliente_asaas.asaas_customer_id}")
        except ValueError as e:
            logger.error(f"ValueError ao criar cliente ASAAS: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
        except Exception as e:
            logger.error(f"Erro ao criar cliente ASAAS: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Erro ao criar cliente no ASAAS. Verifique os dados do lead.'
            })
        
        # 3. Validar que cliente foi criado
        if cliente_asaas is None:
            logger.error("Cliente ASAAS é None após tentativa de criação")
            return JsonResponse({
                'success': False,
                'message': 'Não foi possível criar o cliente no ASAAS. Verifique os dados do lead.'
            })
        
        logger.info(f"Usando customer_id: {cliente_asaas.asaas_customer_id}")
        
        # Obter valor do PIX da configuração
        valor_pix = float(ConfiguracaoService.obter_config('PIX_VALOR_LEVANTAMENTO', ConfiguracaoService.obter_config('VALOR_CONSULTA_PADRAO', 29.90)))
        
        # ASAAS exige valor mínimo de R$ 5,00 por parcela
        if valor_pix < 5.00:
            valor_pix = 5.00
        
        descricao_pix = str(ConfiguracaoService.obter_config('PIX_DESCRICAO', f"Consulta {lead.nome_completo[:20]}"))
        
        # Dados para criar cobrança PIX usando dados do Lead
        cobranca_data = {
            'customer_id': cliente_asaas.asaas_customer_id,  # ID do cliente no Asaas
            'billing_type': 'PIX',
            'value': valor_pix,
            'dueDate': timezone.now().date().isoformat(),
            'description': descricao_pix,
            'externalReference': f"lead_{lead.id}",
            'nome': lead.nome_completo,
            'cpf_cnpj': lead.cpf_cnpj,
            'email': lead.email,
            'telefone': lead.telefone
        }
        
        # Criar cobrança no Asaas
        cobranca_response = asaas_service.criar_cobranca(cobranca_data)
        
        if cobranca_response and 'id' in cobranca_response:
            # Obter QR Code PIX
            pix_data = asaas_service.obter_qr_code_pix(cobranca_response['id'])
            
            if pix_data:
                # Salvar os dados do PIX na tabela PixLevantamento
                PixLevantamento.objects.create(
                    lead=lead,
                    asaas_payment_id=cobranca_response['id'],
                    valor=valor_pix,
                    pix_code=pix_data.get('payload', ''),
                    pix_qr_code_url=pix_data.get('encodedImage', ''),
                    status_pagamento='pendente'
                )
                
                # Atualiza status para pendente de pagamento
                lead.status = 'LEVANTAMENTO_PENDENTE'
                lead.save(update_fields=['status'])
                
                LogService.registrar(
                    usuario=request.user,
                    nivel='INFO',
                    mensagem=f'PIX gerado com sucesso para lead {lead.id}',
                    modulo='atendimento',
                    acao='gerar_pix_sucesso'
                )
                
                return JsonResponse({
                    'success': True,
                    'valor': f"R$ {valor_pix:.2f}",
                    'pix_copia_cola': pix_data.get('payload', ''),
                    'lead_nome': lead.nome_completo
                })
        
        # Se houve erro, tentar retornar mensagem detalhada do Asaas
        error_message = 'Erro ao gerar PIX. Tente novamente.'
        if cobranca_response and 'errors' in cobranca_response:
            # Pega a primeira mensagem de erro do Asaas
            error_message = cobranca_response['errors'][0].get('description', error_message)
        
        LogService.registrar(
            usuario=request.user,
            nivel='ERROR',
            mensagem=f'Erro ao gerar PIX para lead {lead.id}: {error_message}',
            modulo='atendimento',
            acao='gerar_pix_erro'
        )
        
        return JsonResponse({
            'success': False,
            'message': error_message
        })
    
    except Lead.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Lead não encontrado'
        })
    except Exception as e:
        logger.error(f"Erro inesperado ao gerar PIX: {str(e)}")
        LogService.registrar(
            usuario=request.user,
            nivel='ERROR',
            mensagem=f'Erro ao gerar PIX: {str(e)}',
            modulo='atendimento',
            acao='ERRO_PIX',
            ip=get_client_ip(request)
        )
        return JsonResponse({
            'success': False,
            'message': 'Erro ao gerar PIX'
        })
    

@csrf_exempt
def webhook_pagamento_pix(request):
    """
    Webhook para receber confirmações de pagamento do ASAAS
    Usando o handler do core
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            #  USAR WEBHOOK HANDLER DO CORE
            resultado = webhook_handler.processar_webhook_pagamento(data)
            
            if resultado:
                # Lógica específica do atendimento
                payment = data.get('payment', {})
                payment_id = payment.get('id')
                status = payment.get('status')
                
                if status == 'RECEIVED':
                    # Atualizar Lead: fez_levantamento = True
                    try:
                        pix = PixLevantamento.objects.get(asaas_payment_id=payment_id)
                        lead = pix.lead
                        lead.fez_levantamento = True
                        # Atualizar status conforme configuração
                        status_pos = str(ConfiguracaoService.obter_config('LEAD_STATUS_APOS_PAGAMENTO', 'LEVANTAMENTO_PAGO') or 'LEVANTAMENTO_PAGO')
                        lead.status = status_pos
                        lead.save()
                    except Exception as e:
                        logger.error(f'Erro ao atualizar Lead após pagamento PIX: {str(e)}')
                    
                    # Comissionamento automático (se ativo)
                    try:
                        if ConfiguracaoService.obter_config('COMISSAO_ATIVA', True) and lead.atendente:
                            valor_comissao = ConfiguracaoService.obter_config('COMISSAO_ATENDENTE_VALOR_FIXO', 0.50)
                            # Cria se não existir (unique_together garante unicidade)
                            ComissaoLead.objects.get_or_create(
                                lead=lead,
                                atendente=lead.atendente,
                                defaults={'valor': valor_comissao}
                            )
                    except Exception as e:
                        logger.error(f'Erro ao registrar comissão: {str(e)}')

                    # Agendar follow-up (notificação) conforme configuração
                    try:
                        intervalo = int(ConfiguracaoService.obter_config('FOLLOWUP_INTERVALO_PADRAO_DIAS', 2) or 2)
                        data_follow = timezone.now() + timedelta(days=intervalo)
                        usuario_destino = lead.atendente or lead.captador
                        if usuario_destino:
                            NotificacaoService.criar_notificacao(
                                usuario=usuario_destino,
                                titulo='Agendar Follow-up',
                                mensagem=f"Realizar follow-up com {lead.nome_completo} em {data_follow.strftime('%d/%m/%Y')}",
                                tipo='INFO',
                                link=f'/atendimento/lead/{lead.id}/'
                            )
                        # Atualiza status para contato se definido
                        status_contato = ConfiguracaoService.obter_config('LEAD_STATUS_CONTATO', None)
                        if status_contato:
                            lead.status = str(status_contato)
                            lead.save(update_fields=['status'])
                    except Exception as e:
                        logger.error(f'Erro ao agendar follow-up: {str(e)}')

                    #  NOTIFICAÇÃO DE PAGAMENTO
                    NotificacaoService.criar_notificacao(
                        usuario=lead.captador,
                        titulo='Pagamento Confirmado',
                        mensagem=f'Pagamento confirmado para {lead.nome_completo}',
                        tipo='SUCESSO',
                        link=f'/atendimento/lead/{lead.id}/'
                    )
                    
                    LogService.registrar(
                        usuario=lead.captador,
                        nivel='INFO',
                        mensagem=f"Pagamento confirmado - Lead ID: {lead.id}",
                        modulo='atendimento',
                        acao='pagamento_confirmado',
                        ip=None  # Webhook não tem IP do cliente
                    )
            
            return JsonResponse({'status': 'success'})
            
        except Exception as e:
            logger.error(f"Erro no webhook: {str(e)}")
            LogService.registrar(
                nivel='ERROR',
                mensagem=f"Erro no webhook atendimento: {str(e)}",
                modulo='atendimento',
                acao='erro_webhook',
                ip=None
            )
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
    
    return JsonResponse({'status': 'method not allowed'}, status=405)
# ===========================

@csrf_exempt
def api_autenticar_e_redirecionar(request):
    """API para autenticar e redirecionar o usuário"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = data.get('token')
            
            if not token:
                return JsonResponse({'success': False, 'error': 'Token não fornecido'}, status=400)
            
            # Autentica com o token
            auth_result = autenticar_via_token(request, token)
            
            if auth_result['success']:
                # Garante que o login crie uma sessão Django
                from django.contrib.auth import login
                user = auth_result['user']
                user.backend = 'django.contrib.auth.backends.ModelBackend'
                login(request, user)
                
                return JsonResponse({
                    'success': True, 
                    'redirect_url': '/atendimento/leads-pix/'
                })
            else:
                return JsonResponse({
                    'success': False, 
                    'error': auth_result['error'],
                    'redirect_url': '/accounts/login/?next=/atendimento/leads-pix/'
                }, status=401)
                
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'error': 'Método não permitido'}, status=405)

# ===========================
from django.utils import timezone
from datetime import timedelta
import random

@login_required
def lista_leads_pix(request):
    """Lista de leads PIX com autenticação híbrida e suporte à paginação"""
    # Verifica se o usuário está autenticado via sessão
    if not request.user.is_authenticated:
        # Tenta autenticação JWT se disponível
        auth_header = request.META.get('HTTP_AUTHORIZATION')
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            auth_result = autenticar_via_token(request, token)
            if not auth_result['success']:
                return redirect('/accounts/login/?next=/atendimento/leads-pix/')

    agora = timezone.now()
    limite = agora - timedelta(hours=24)
    leads = Lead.objects.filter(
        captador=request.user,
        data_cadastro__gte=limite
    ).select_related('cliente_asaas').prefetch_related('pix_levantamentos').order_by('-data_cadastro')

    # Paginação
    page = request.GET.get('page', 1)
    paginator = Paginator(leads, 10)  # 10 leads por página

    try:
        leads_paginated = paginator.page(page)
    except PageNotAnInteger:
        leads_paginated = paginator.page(1)
    except EmptyPage:
        leads_paginated = paginator.page(paginator.num_pages)

    # Adiciona dados reais do PIX Levantamento para cada lead
    for lead in leads_paginated:
        # Busca o PIX mais recente do lead
        pix_levantamento = lead.pix_levantamentos.order_by('-data_criacao').first()
        
        if pix_levantamento:
            lead.pix_real = pix_levantamento
            lead.pix_code = pix_levantamento.pix_code
            lead.pix_valor = pix_levantamento.valor
            lead.pix_status = pix_levantamento.status_pagamento
        else:
            lead.pix_real = None
            lead.pix_code = ''
            lead.pix_valor = 0
            lead.pix_status = 'sem_pix'

    return render(request, 'atendimento/lista_leads_pix.html', {'leads': leads_paginated})


@login_required
def lista_atendimentos(request):
    """Lista todos os atendimentos do usuário"""
    logger.info(f" Lista atendimentos acessada por: {request.user.email}")
    atendimentos = Lead.objects.filter(captador=request.user).order_by('-data_cadastro')
    return render(request, 'atendimento/lista_atendimentos.html', {'atendimentos': atendimentos})




@login_required
def painel_atendente(request):
    """Exibe o painel do atendente com resumo e histórico real"""
    from marketing.models import Lead
    from financeiro.models import PixLevantamento, Comissao
    from django.utils import timezone
    from datetime import timedelta
    from django.db import models

    user = request.user
    now = timezone.now()
    inicio_mes = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Leads cadastrados pelo atendente
    total_leads = Lead.objects.filter(captador=user).count()
    leads_mes = Lead.objects.filter(captador=user, data_cadastro__gte=inicio_mes).count()

    # Levantamentos realizados com sucesso (status_pagamento='pago')
    levantamentos_total = PixLevantamento.objects.filter(lead__captador=user, status_pagamento='pago').count()
    levantamentos_mes = PixLevantamento.objects.filter(lead__captador=user, status_pagamento='pago', data_criacao__gte=inicio_mes).count()

    # Comissão recebida e a receber (R$ 0,50 por levantamento pago)
    comissoes_recebidas = Comissao.objects.filter(usuario=user, status='paga').aggregate(total=models.Sum('valor_comissao'))['total'] or 0
    comissoes_a_receber = Comissao.objects.filter(usuario=user, status='pendente').aggregate(total=models.Sum('valor_comissao'))['total'] or 0

    # Histórico de consultas (últimos 7 dias)
    sete_dias_atras = now - timedelta(days=7)
    historico_consultas = Lead.objects.filter(
        captador=user,
        data_cadastro__gte=sete_dias_atras
    ).order_by('-data_cadastro')

    context = {
        'total_leads': total_leads,
        'leads_mes': leads_mes,
        'levantamentos_total': levantamentos_total,
        'levantamentos_mes': levantamentos_mes,
        'comissoes_recebidas': comissoes_recebidas,
        'comissoes_a_receber': comissoes_a_receber,
        'historico_consultas': historico_consultas,
    }
    return render(request, 'atendimento/painel_atendente.html', context)
    


@login_required
def area_de_trabalho_atendente(request):
    """Exibe o novo painel para gerenciar informações adicionais."""
    context = {
        'exemplo_1': 100,
        'exemplo_2': 200,
    }
    return render(request, 'atendimento/area_de_trabalho_atendente.html', context)