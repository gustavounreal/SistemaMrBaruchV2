from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, Count
from django.http import Http404, JsonResponse
from django.contrib import messages
from django.views.decorators.http import require_POST
from datetime import date
from vendas.models import Venda
from financeiro.models import Parcela
from .models import LinkCurto, ClickLinkCurto, MaterialDivulgacao
from accounts.models import DadosUsuario
from core.services import ConfiguracaoService


@login_required
def area_captador(request):
    """
    Área do captador - Dashboard com estatísticas, boletos e materiais
    """
    captador = request.user
    
    # Garantir que DadosUsuario existe
    dados_usuario, created = DadosUsuario.objects.get_or_create(user=captador)
    
    # Obter configurações do sistema
    whatsapp_numero = ConfiguracaoService.obter_config('CAPTADOR_WHATSAPP_NUMERO', '5511978891213')
    whatsapp_mensagem = ConfiguracaoService.obter_config('CAPTADOR_WHATSAPP_MENSAGEM', 'Olá! Fui indicado por um captador.')
    percentual_comissao_config = ConfiguracaoService.obter_config('CAPTADOR_COMISSAO_PERCENTUAL', 20)
    
    # Criar ou recuperar link curto do captador
    link_curto, created = LinkCurto.objects.get_or_create(
        captador=captador,
        defaults={
            'codigo': LinkCurto.gerar_codigo_unico(),
            'url_completa': f"https://wa.me/{whatsapp_numero}?text={whatsapp_mensagem} ID: {captador.id}"
        }
    )
    
    # Se o link já existe, atualizar a URL caso as configurações tenham mudado
    if not created:
        nova_url = f"https://wa.me/{whatsapp_numero}?text={whatsapp_mensagem} ID: {captador.id}"
        if link_curto.url_completa != nova_url:
            link_curto.url_completa = nova_url
            link_curto.save(update_fields=['url_completa'])
    
    # Buscar todas as vendas onde o captador foi indicado
    vendas = Venda.objects.filter(captador=captador).select_related('cliente__lead', 'servico')
    
    # Estatísticas financeiras
    total_vendas = vendas.count()
    valor_total_indicacoes = vendas.aggregate(total=Sum('valor_total'))['total'] or 0
    
    # ✅ CORREÇÃO: Buscar comissões reais do captador (não calcular estimativa)
    from decimal import Decimal
    from financeiro.models import Comissao
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    
    comissoes_captador_all = Comissao.objects.filter(
        usuario=captador,
        tipo_comissao__in=['CAPTADOR_ENTRADA', 'CAPTADOR_PARCELA']
    ).select_related('venda__cliente__lead', 'parcela').order_by('-data_calculada')
    
    # Comissão total (soma de todas as comissões registradas)
    comissao_total = comissoes_captador_all.aggregate(
        total=Sum('valor_comissao')
    )['total'] or Decimal('0')
    
    # Comissão recebida (comissões já pagas)
    comissao_recebida = comissoes_captador_all.filter(
        status='paga'
    ).aggregate(total=Sum('valor_comissao'))['total'] or Decimal('0')
    
    # Comissão a receber (comissões pendentes)
    comissao_a_receber = comissoes_captador_all.filter(
        status='pendente'
    ).aggregate(total=Sum('valor_comissao'))['total'] or Decimal('0')
    
    # Percentual de comissão para exibição (obtém da primeira comissão ou configuração)
    percentual_comissao = percentual_comissao_config
    primeira_comissao = comissoes_captador_all.first()
    if primeira_comissao:
        percentual_comissao = int(primeira_comissao.percentual_comissao)
    
    # ✅ PAGINAÇÃO: 10 comissões por página
    paginator = Paginator(comissoes_captador_all, 10)
    page = request.GET.get('page', 1)
    
    try:
        comissoes_captador = paginator.page(page)
    except PageNotAnInteger:
        comissoes_captador = paginator.page(1)
    except EmptyPage:
        comissoes_captador = paginator.page(paginator.num_pages)
    
    # Buscar todas as parcelas das vendas do captador
    parcelas = Parcela.objects.filter(venda__captador=captador).select_related('venda__cliente__lead')
    
    # Estatísticas de boletos
    total_parcelas = parcelas.count()
    parcelas_pagas = parcelas.filter(status='paga').count()
    parcelas_vencidas = parcelas.filter(status='vencida').count()
    parcelas_abertas = parcelas.filter(status='aberta').count()
    
    # Valores das parcelas (para estatísticas)
    valor_pago = parcelas.filter(status='paga').aggregate(total=Sum('valor'))['total'] or 0
    valor_pendente = parcelas.exclude(status='paga').aggregate(total=Sum('valor'))['total'] or 0
    
    # Calcular dias de atraso para parcelas vencidas
    hoje = date.today()
    parcelas_com_atraso = []
    for parcela in parcelas:
        if parcela.status == 'vencida' and not parcela.data_pagamento:
            parcela.dias_atraso = (hoje - parcela.data_vencimento).days
        else:
            parcela.dias_atraso = 0
    
    # Separar boletos por status
    boletos_pagos = parcelas.filter(status='paga').order_by('-data_pagamento')[:10]
    boletos_vencidos = parcelas.filter(status='vencida').order_by('data_vencimento')
    boletos_a_vencer = parcelas.filter(status='aberta').order_by('data_vencimento')[:10]
    
    # Próximo recebimento (próxima parcela a vencer)
    proxima_parcela = parcelas.filter(status='aberta').order_by('data_vencimento').first()
    proximo_recebimento = proxima_parcela.data_vencimento if proxima_parcela else None
    
    # Link de indicação do WhatsApp (agora usa o link curto)
    link_curto_url = link_curto.get_url_curta(request)
    whatsapp_link = link_curto.url_completa  # Link completo para caso precisem ver
    
    # Buscar materiais de divulgação ativos do banco de dados
    materiais = MaterialDivulgacao.objects.filter(ativo=True).order_by('ordem', '-criado_em')
    
    # Verificar se usuário é administrador
    is_admin = request.user.groups.filter(name__in=['Administrador', 'Admin']).exists() or request.user.is_superuser
    
    context = {
        'captador': captador,
        'dados_usuario': dados_usuario,
        'total_vendas': total_vendas,
        'valor_total_indicacoes': valor_total_indicacoes,
        'comissao_total': comissao_total,
        'comissao_recebida': comissao_recebida,
        'comissao_a_receber': comissao_a_receber,
        'percentual_comissao': percentual_comissao,
        'total_parcelas': total_parcelas,
        'parcelas_pagas': parcelas_pagas,
        'parcelas_vencidas': parcelas_vencidas,
        'parcelas_abertas': parcelas_abertas,
        'valor_pago': valor_pago,
        'valor_pendente': valor_pendente,
        'proximo_recebimento': proximo_recebimento,
        'boletos_pagos': boletos_pagos,
        'boletos_vencidos': boletos_vencidos,
        'boletos_a_vencer': boletos_a_vencer,
        'whatsapp_link': whatsapp_link,
        'link_curto_url': link_curto_url,  # URL curta para compartilhar
        'link_curto': link_curto,  # Objeto completo para analytics
        'materiais': materiais,
        'is_admin': is_admin,
        'hoje': hoje,
        'comissoes_captador': comissoes_captador,  # ✅ Adiciona lista de comissões para detalhamento
    }
    
    return render(request, 'captadores/area_captador.html', context)


def redirecionar_link_curto(request, codigo):
    """
    View pública que redireciona link curto para WhatsApp.
    Registra analytics (cliques, IP, user agent, referer).
    """
    # Buscar link curto pelo código
    link_curto = get_object_or_404(LinkCurto, codigo=codigo, ativo=True)
    
    # Registrar clique para analytics
    ip_address = request.META.get('REMOTE_ADDR')
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    referer = request.META.get('HTTP_REFERER', None)
    
    # Criar registro de clique
    ClickLinkCurto.objects.create(
        link_curto=link_curto,
        ip_address=ip_address,
        user_agent=user_agent,
        referer=referer
    )
    
    # Incrementar contador
    link_curto.incrementar_clique()
    
    # Redirecionar para o WhatsApp
    return redirect(link_curto.url_completa)


@login_required
@require_POST
def upload_material(request):
    """
    View para upload de material de divulgação (apenas administradores)
    """
    # Verificar se é administrador
    if not (request.user.groups.filter(name__in=['Administrador', 'Admin']).exists() or request.user.is_superuser):
        messages.error(request, 'Você não tem permissão para fazer upload de materiais.')
        return redirect('captadores:area_captador')
    
    try:
        arquivo = request.FILES.get('arquivo')
        nome = request.POST.get('nome', '')
        descricao = request.POST.get('descricao', '')
        
        if not arquivo:
            messages.error(request, 'Nenhum arquivo foi selecionado.')
            return redirect('captadores:area_captador')
        
        if not nome:
            nome = arquivo.name
        
        # Criar material
        material = MaterialDivulgacao.objects.create(
            nome=nome,
            descricao=descricao,
            arquivo=arquivo,
            criado_por=request.user
        )
        
        messages.success(request, f'Material "{material.nome}" enviado com sucesso!')
        
    except Exception as e:
        messages.error(request, f'Erro ao fazer upload: {str(e)}')
    
    return redirect('captadores:area_captador')


@login_required
@require_POST
def deletar_material(request, material_id):
    """
    View para deletar material de divulgação (apenas administradores)
    """
    # Verificar se é administrador
    if not (request.user.groups.filter(name__in=['Administrador', 'Admin']).exists() or request.user.is_superuser):
        return JsonResponse({'success': False, 'error': 'Permissão negada'}, status=403)
    
    try:
        material = get_object_or_404(MaterialDivulgacao, id=material_id)
        nome = material.nome
        material.delete()
        
        return JsonResponse({'success': True, 'message': f'Material "{nome}" excluído com sucesso!'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=500)


@login_required
@require_POST
def atualizar_dados_captador(request):
    """
    View para o captador atualizar suas próprias informações
    """
    print("🔵 FUNÇÃO atualizar_dados_captador CHAMADA!")
    print(f"🔵 Method: {request.method}")
    print(f"🔵 User: {request.user}")
    print(f"🔵 POST keys: {request.POST.keys()}")
    
    try:
        captador = request.user
        
        print("=== DEBUG ATUALIZAR DADOS ===")
        print(f"User ID: {captador.id}")
        print(f"POST data: {request.POST}")
        
        # Garantir que DadosUsuario existe
        dados_usuario, created = DadosUsuario.objects.get_or_create(user=captador)
        print(f"DadosUsuario criado: {created}")
        
        # Atualizar campos do User
        captador.nome_completo = request.POST.get('nome_completo', '').strip()
        captador.rg = request.POST.get('rg', '').strip()
        captador.cpf = request.POST.get('cpf', '').strip()
        
        print(f"Nome completo: {captador.nome_completo}")
        print(f"RG: {captador.rg}")
        print(f"CPF: {captador.cpf}")
        
        # Atualizar endereço detalhado
        captador.cep = request.POST.get('cep', '').strip()
        captador.logradouro = request.POST.get('logradouro', '').strip()
        captador.numero = request.POST.get('numero', '').strip()
        captador.complemento = request.POST.get('complemento', '').strip()
        captador.bairro = request.POST.get('bairro', '').strip()
        captador.cidade = request.POST.get('cidade', '').strip()
        captador.estado = request.POST.get('estado', '').strip()
        
        # Montar endereço completo (para compatibilidade)
        partes_endereco = []
        if captador.logradouro:
            partes_endereco.append(captador.logradouro)
        if captador.numero:
            partes_endereco.append(f"nº {captador.numero}")
        if captador.complemento:
            partes_endereco.append(captador.complemento)
        if captador.bairro:
            partes_endereco.append(f"Bairro: {captador.bairro}")
        if captador.cidade and captador.estado:
            partes_endereco.append(f"{captador.cidade} - {captador.estado}")
        if captador.cep:
            partes_endereco.append(f"CEP: {captador.cep}")
        
        captador.endereco_completo = ', '.join(partes_endereco) if partes_endereco else ''
        
        captador.chave_pix = request.POST.get('chave_pix', '').strip()
        
        # Atualizar campos do DadosUsuario
        dados_usuario.whatsapp_pessoal = request.POST.get('whatsapp_pessoal', '').strip()
        dados_usuario.contato_recado = request.POST.get('contato_recado', '').strip()
        
        # Atualizar conta bancária (JSON)
        banco = request.POST.get('banco', '').strip()
        agencia = request.POST.get('agencia', '').strip()
        conta = request.POST.get('conta', '').strip()
        
        if banco or agencia or conta:
            captador.conta_bancaria = {
                'banco': banco,
                'agencia': agencia,
                'conta': conta
            }
        
        print(f"WhatsApp: {dados_usuario.whatsapp_pessoal}")
        print(f"Contato recado: {dados_usuario.contato_recado}")
        print(f"Chave PIX: {captador.chave_pix}")
        
        # Salvar
        captador.save()
        dados_usuario.save()
        
        print("✅ Dados salvos com sucesso!")
        print(f"Captador após save - Nome: {captador.nome_completo}, CPF: {captador.cpf}")
        
        messages.success(request, 'Seus dados foram atualizados com sucesso!')
        
    except Exception as e:
        messages.error(request, f'Erro ao atualizar dados: {str(e)}')
    
    return redirect('captadores:area_captador')


