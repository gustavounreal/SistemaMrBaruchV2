from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import JsonResponse, HttpResponse, FileResponse
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib import messages
from django.core.paginator import Paginator
from django.urls import reverse
from .models import (
    AnaliseCompliance, GestaoDocumentosPosVenda, HistoricoAnaliseCompliance,
    StatusAnaliseCompliance, ClassificacaoLead, StatusPosVendaCompliance,
    ConferenciaVendaCompliance, DocumentoVendaCompliance, ContratoCompliance,
    StatusPagamentoEntrada, TipoDocumento, StatusDocumento
)
from .services import (
    ComplianceStatsService, ComplianceAnaliseService, ConsultorAtribuicaoService
)
from marketing.models import Lead
from vendas.models import PreVenda, Venda
import json
from datetime import datetime, timedelta

User = get_user_model()


def is_compliance(user):
    """Verifica se o usuário pertence ao grupo compliance ou é admin/superuser"""
    if user.is_superuser:
        return True
    return user.groups.filter(name__in=['compliance', 'admin']).exists()


def is_compliance_or_juridico(user):
    """
    Verifica se o usuário é do Compliance OU Jurídico.
    Permite que ambos os grupos acessem recursos compartilhados.
    """
    if user.is_superuser:
        return True
    return user.groups.filter(
        name__in=['compliance', 'juridico', 'admin']
    ).exists()


@login_required
@user_passes_test(is_compliance)
def painel_compliance(request):
    """Painel principal do Compliance"""
    user = request.user
    
    # Usar service para buscar estatísticas
    stats = ComplianceStatsService.get_dashboard_stats()
    leads_aguardando = ComplianceStatsService.get_leads_aguardando(limit=10)
    leads_em_analise = ComplianceStatsService.get_leads_em_analise_by_user(user, limit=10)
    historico_recente = ComplianceStatsService.get_historico_recente(limit=15)
    
    context = {
        **stats,  # Desempacota todas as estatísticas
        'leads_aguardando': leads_aguardando,
        'leads_em_analise': leads_em_analise,
        'historico_recente': historico_recente,
    }
    
    return render(request, 'compliance/painel.html', context)


@login_required
@user_passes_test(is_compliance)
def lista_analises(request):
    """Lista todas as análises de compliance com filtros"""
    status_filtro = request.GET.get('status', '')
    classificacao_filtro = request.GET.get('classificacao', '')
    busca = request.GET.get('busca', '')
    
    # Usar service para filtrar análises
    analises = ComplianceAnaliseService.filtrar_analises(
        status=status_filtro or None,
        classificacao=classificacao_filtro or None,
        busca=busca or None
    )
    
    context = {
        'analises': analises,
        'status_choices': StatusAnaliseCompliance.choices,
        'classificacao_choices': ClassificacaoLead.choices,
        'status_filtro': status_filtro,
        'classificacao_filtro': classificacao_filtro,
        'busca': busca,
    }
    
    return render(request, 'compliance/lista_analises.html', context)


@login_required
@user_passes_test(is_compliance)
def detalhes_lead_compliance(request, lead_id):
    """Exibe detalhes do lead para análise de compliance"""
    lead = get_object_or_404(Lead, id=lead_id)
    
    # Busca ou cria análise de compliance
    analise, created = AnaliseCompliance.objects.get_or_create(
        lead=lead,
        defaults={'status': StatusAnaliseCompliance.AGUARDANDO}
    )
    
    # Busca levantamentos
    from financeiro.models import PixLevantamento
    levantamentos = PixLevantamento.objects.filter(lead=lead).order_by('-data_criacao')
    
    # Busca pré-vendas
    pre_vendas = PreVenda.objects.filter(lead=lead).order_by('-data_criacao')
    
    # Histórico da análise
    historico = HistoricoAnaliseCompliance.objects.filter(
        analise=analise
    ).select_related('usuario').order_by('-data')
    
    # Lista de consultores disponíveis (usar service)
    consultores = ConsultorAtribuicaoService.listar_consultores_disponiveis()
    
    context = {
        'lead': lead,
        'analise': analise,
        'levantamentos': levantamentos,
        'pre_vendas': pre_vendas,
        'historico': historico,
        'consultores': consultores,
        'classificacoes': ClassificacaoLead.choices,
    }
    
    return render(request, 'compliance/detalhes_lead.html', context)


@login_required
@user_passes_test(is_compliance)
def analisar_lead(request, analise_id):
    """API para realizar análise do lead"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        analise = get_object_or_404(AnaliseCompliance, id=analise_id)
        
        acao = data.get('acao')  # 'iniciar', 'aprovar', 'reprovar'
        valor_divida = data.get('valor_divida')
        observacoes = data.get('observacoes', '')
        motivo_reprovacao = data.get('motivo_reprovacao', '')
        
        if acao == 'iniciar':
            # Usar service para iniciar análise
            analise = ComplianceAnaliseService.iniciar_analise(
                analise=analise,
                usuario=request.user,
                valor_divida=valor_divida,
                observacoes=observacoes
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Análise iniciada com sucesso',
                'classificacao': analise.get_classificacao_display()
            })
        
        elif acao == 'aprovar':
            # Usar service para aprovar análise
            analise = ComplianceAnaliseService.aprovar_analise(
                analise=analise,
                usuario=request.user,
                observacoes=observacoes
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Lead aprovado. Agora pode ser atribuído a um consultor.'
            })
        
        elif acao == 'reprovar':
            # Usar service para reprovar análise
            analise = ComplianceAnaliseService.reprovar_analise(
                analise=analise,
                usuario=request.user,
                motivo=motivo_reprovacao,
                observacoes=observacoes
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Lead reprovado.'
            })
        
        else:
            return JsonResponse({'success': False, 'message': 'Ação inválida'}, status=400)
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@user_passes_test(is_compliance)
def atribuir_consultor(request, analise_id):
    """API para atribuir lead a um consultor"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        analise = get_object_or_404(AnaliseCompliance, id=analise_id)
        consultor_id = data.get('consultor_id')
        
        if not consultor_id:
            return JsonResponse({'success': False, 'message': 'Consultor não informado'}, status=400)
        
        consultor = get_object_or_404(User, id=consultor_id)
        
        # Verifica se é realmente um consultor
        if not consultor.groups.filter(name='comercial1').exists():  # Atualizado de 'consultor' para 'comercial1'
            return JsonResponse({'success': False, 'message': 'Usuário não é consultor'}, status=400)
        
        # Usar service para atribuir consultor
        ConsultorAtribuicaoService.atribuir_lead_consultor(
            analise=analise,
            consultor=consultor,
            usuario=request.user
        )
        
        return JsonResponse({
            'success': True,
            'message': f'Lead atribuído ao consultor {consultor.get_full_name() or consultor.username}'
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@user_passes_test(is_compliance)
def gestao_pos_venda_lista(request):
    """Lista gestões pós-venda pendentes"""
    status_filtro = request.GET.get('status', '')
    
    gestoes = GestaoDocumentosPosVenda.objects.select_related(
        'pre_venda__lead', 'responsavel'
    ).all()
    
    if status_filtro:
        gestoes = gestoes.filter(status=status_filtro)
    
    gestoes = gestoes.order_by('-data_criacao')
    
    context = {
        'gestoes': gestoes,
        'status_choices': StatusPosVendaCompliance.choices,
        'status_filtro': status_filtro,
    }
    
    return render(request, 'compliance/gestao_pos_venda_lista.html', context)


@login_required
@user_passes_test(is_compliance)
def gestao_pos_venda_detalhes(request, gestao_id):
    """Detalhes e ações da gestão pós-venda"""
    gestao = get_object_or_404(GestaoDocumentosPosVenda, id=gestao_id)
    
    context = {
        'gestao': gestao,
        'pre_venda': gestao.pre_venda,
        'lead': gestao.pre_venda.lead,
    }
    
    return render(request, 'compliance/gestao_pos_venda_detalhes.html', context)


@login_required
@user_passes_test(is_compliance)
def acao_pos_venda(request, gestao_id):
    """API para executar ações na gestão pós-venda"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)
    
    try:
        data = json.loads(request.body)
        gestao = get_object_or_404(GestaoDocumentosPosVenda, id=gestao_id)
        
        acao = data.get('acao')
        observacoes = data.get('observacoes', '')
        documentos = data.get('documentos', [])
        
        if acao == 'conferir_cadastro':
            gestao.conferir_cadastro(request.user, observacoes)
            mensagem = 'Cadastro conferido com sucesso'
        
        elif acao == 'registrar_documentos':
            gestao.registrar_coleta_documentos(request.user, documentos)
            mensagem = 'Documentos registrados com sucesso'
        
        elif acao == 'emitir_contrato':
            gestao.emitir_contrato(request.user)
            mensagem = 'Contrato emitido'
        
        elif acao == 'enviar_contrato':
            gestao.enviar_contrato(request.user)
            mensagem = 'Contrato enviado'
        
        elif acao == 'confirmar_assinatura':
            gestao.confirmar_assinatura(request.user)
            mensagem = 'Assinatura confirmada. Processo concluído!'
        
        else:
            return JsonResponse({'success': False, 'message': 'Ação inválida'}, status=400)
        
        return JsonResponse({
            'success': True,
            'message': mensagem,
            'novo_status': gestao.get_status_display()
        })
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@login_required
@user_passes_test(is_compliance)
def perfil_compliance(request):
    """Perfil do usuário Compliance"""
    from accounts.forms import PerfilAtendenteForm
    
    user = request.user
    
    if request.method == 'POST':
        user_form = PerfilAtendenteForm(request.POST, instance=user)
        
        if user_form.is_valid():
            user_form.save()
            
            # Atualizar email se fornecido
            new_email = request.POST.get('new_email')
            confirm_email = request.POST.get('confirm_email')
            if new_email and new_email == confirm_email:
                user.email = new_email
                user.save()
            
            # Atualizar senha se fornecida
            new_password = request.POST.get('new_password')
            confirm_password = request.POST.get('confirm_password')
            if new_password and new_password == confirm_password:
                user.set_password(new_password)
                user.save()
            
            return redirect('compliance:perfil_compliance')
    else:
        user_form = PerfilAtendenteForm(instance=user)
    
    context = {
        'user_form': user_form,
    }
    
    return render(request, 'compliance/perfil_compliance.html', context)


# ============================================================================
# VIEWS PARA GESTÃO PÓS-VENDA
# ============================================================================

@login_required
@user_passes_test(is_compliance)
def painel_pos_venda(request):
    """
    Painel principal de gestão pós-venda.
    Lista todas as vendas cadastradas com filtros.
    """
    # Filtros
    filtro_status = request.GET.get('status', '')
    filtro_pagamento = request.GET.get('pagamento', '')
    filtro_busca = request.GET.get('busca', '')
    
    # Query base - buscar todas as vendas
    vendas = Venda.objects.select_related(
        'cliente', 'cliente__lead', 'servico', 'consultor', 'captador'
    ).order_by('-data_criacao')
    
    # Aplicar filtros
    if filtro_status:
        vendas = vendas.filter(status_compliance_pos_venda=filtro_status)
    
    if filtro_pagamento:
        vendas = vendas.filter(status_pagamento_entrada=filtro_pagamento)
    
    if filtro_busca:
        vendas = vendas.filter(
            Q(cliente__lead__nome_completo__icontains=filtro_busca) |
            Q(cliente__lead__cpf_cnpj__icontains=filtro_busca) |
            Q(id__icontains=filtro_busca)
        )
    
    # Estatísticas
    total_vendas = vendas.count()
    aguardando_conferencia = vendas.filter(
        status_compliance_pos_venda=StatusPosVendaCompliance.AGUARDANDO_CONFERENCIA
    ).count()
    coletando_documentos = vendas.filter(
        status_compliance_pos_venda=StatusPosVendaCompliance.COLETANDO_DOCUMENTOS
    ).count()
    aguardando_assinatura = vendas.filter(
        status_compliance_pos_venda=StatusPosVendaCompliance.AGUARDANDO_ASSINATURA
    ).count()
    concluidos_hoje = vendas.filter(
        status_compliance_pos_venda=StatusPosVendaCompliance.CONCLUIDO,
        data_atualizacao__date=timezone.now().date()
    ).count()
    
    # Paginação
    paginator = Paginator(vendas, 20)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    
    # Choices para os filtros
    status_choices = StatusPosVendaCompliance.choices
    pagamento_choices = StatusPagamentoEntrada.choices
    
    context = {
        'vendas': page_obj,
        'total_vendas': total_vendas,
        'aguardando_conferencia': aguardando_conferencia,
        'coletando_documentos': coletando_documentos,
        'aguardando_assinatura': aguardando_assinatura,
        'concluidos_hoje': concluidos_hoje,
        'status_choices': status_choices,
        'pagamento_choices': pagamento_choices,
        'filtro_status': filtro_status,
        'filtro_pagamento': filtro_pagamento,
        'filtro_busca': filtro_busca,
    }
    
    return render(request, 'compliance/pos_venda/painel.html', context)


@login_required
@user_passes_test(is_compliance_or_juridico)
def gestao_pos_venda(request, venda_id):
    """
    PAINEL UNIFICADO de pós-venda.
    Integra Compliance + Jurídico em uma única interface.
    
    Fluxo:
    1. Compliance: Upload e aprovação de documentos
    2. Jurídico (integrado): Geração, envio e assinatura de contrato
    3. Compliance: Conclusão do pós-venda
    """
    venda = get_object_or_404(
        Venda.objects.select_related('cliente', 'cliente__lead', 'servico', 'consultor'),
        id=venda_id
    )
    
    # Obter ou criar conferência
    conferencia, created = ConferenciaVendaCompliance.objects.get_or_create(
        venda=venda,
        defaults={'analista': request.user}
    )
    
    # Se foi criada, criar documentos obrigatórios
    if created:
        documentos_obrigatorios = [
            TipoDocumento.RG_FRENTE,
            TipoDocumento.RG_VERSO,
            TipoDocumento.CPF,
            TipoDocumento.COMP_RESIDENCIA,
            TipoDocumento.SELFIE_DOC,
        ]
        for tipo in documentos_obrigatorios:
            DocumentoVendaCompliance.objects.create(
                conferencia=conferencia,
                tipo=tipo,
                obrigatorio=True
            )
    
    # Buscar documentos
    documentos = conferencia.documentos.all().order_by('obrigatorio', 'tipo')
    
    # Buscar valores reais das parcelas se os campos da venda estiverem vazios
    from financeiro.models import Parcela
    from decimal import Decimal
    
    parcelas = Parcela.objects.filter(venda=venda).order_by('numero_parcela')
    
    # Calcular valores reais a partir das parcelas
    valor_total_real = venda.valor_total
    valor_entrada_real = venda.valor_entrada
    valor_parcela_real = venda.valor_parcela
    quantidade_parcelas_real = venda.quantidade_parcelas
    
    if parcelas.exists():
        # Se temos parcelas, calcular a partir delas
        primeira_parcela = parcelas.first()
        valor_parcela_real = primeira_parcela.valor if primeira_parcela else valor_parcela_real
        quantidade_parcelas_real = parcelas.count()
        
        # Calcular valor total das parcelas
        total_parcelas = sum([p.valor for p in parcelas])
        
        # Se valor_entrada estiver vazio, buscar do PixEntrada
        if not valor_entrada_real or valor_entrada_real == 0:
            from financeiro.models import PixEntrada
            pix = PixEntrada.objects.filter(venda=venda).first()
            valor_entrada_real = pix.valor if pix else Decimal('0')
        
        # Calcular valor total
        if not valor_total_real or valor_total_real == 0:
            valor_total_real = total_parcelas + (valor_entrada_real or Decimal('0'))
    
    # INTEGRAÇÃO JURÍDICO: Buscar contrato do módulo juridico
    from juridico.models import Contrato
    from financeiro.models import PixEntrada
    
    contrato_juridico = Contrato.objects.filter(venda=venda).first()
    
    # Verificar se a entrada foi paga (ou se é sem entrada)
    entrada_paga = False
    pix_entrada = None
    
    if venda.sem_entrada:
        entrada_paga = True  # Não precisa de entrada
    else:
        # Buscar PIX de entrada
        pix_entrada = PixEntrada.objects.filter(venda=venda).first()
        if pix_entrada and pix_entrada.status_pagamento == 'PAGO':
            entrada_paga = True
    
    # Determinar ações disponíveis
    # IMPORTANTE: Como a etapa de documentos está comentada,
    # verificamos apenas se a conferência de cadastro foi aprovada
    conferencia_aprovada = (
        conferencia.dados_cliente_conferidos and 
        conferencia.dados_venda_conferidos
    )
    
    pode_gerar_contrato = (
        conferencia_aprovada and 
        entrada_paga and  # NOVA VALIDAÇÃO: Entrada deve estar paga
        not contrato_juridico
    )
    
    pode_marcar_enviado = (
        contrato_juridico and 
        contrato_juridico.status == 'GERADO'
    )
    
    pode_marcar_assinado = (
        contrato_juridico and 
        contrato_juridico.status == 'ENVIADO'
    )
    
    # URLs do Jurídico (para os botões)
    url_gerar_contrato = reverse('juridico:gerar_contrato', args=[venda_id]) if pode_gerar_contrato else None
    url_marcar_enviado = reverse('juridico:marcar_contrato_enviado', args=[contrato_juridico.id]) if pode_marcar_enviado else None
    url_marcar_assinado = reverse('juridico:marcar_contrato_assinado', args=[contrato_juridico.id]) if pode_marcar_assinado else None
    url_download_contrato = reverse('juridico:download_contrato', args=[contrato_juridico.id]) if contrato_juridico else None
    
    context = {
        'venda': venda,
        'conferencia': conferencia,
        'documentos': documentos,
        
        # Valores reais calculados
        'valor_total_real': valor_total_real,
        'valor_entrada_real': valor_entrada_real,
        'valor_parcela_real': valor_parcela_real,
        'quantidade_parcelas_real': quantidade_parcelas_real,
        
        # Integração Jurídico
        'contrato': contrato_juridico,
        'pode_gerar_contrato': pode_gerar_contrato,
        'pode_marcar_enviado': pode_marcar_enviado,
        'pode_marcar_assinado': pode_marcar_assinado,
        
        # Validação de Entrada
        'entrada_paga': entrada_paga,
        'pix_entrada': pix_entrada,
        'sem_entrada': venda.sem_entrada,
        
        # URLs do Jurídico
        'url_gerar_contrato': url_gerar_contrato,
        'url_marcar_enviado': url_marcar_enviado,
        'url_marcar_assinado': url_marcar_assinado,
        'url_download_contrato': url_download_contrato,
        
        # Choices
        'status_choices': StatusPosVendaCompliance.choices,
        'tipo_documento_choices': TipoDocumento.choices,
        'formas_pagamento': Venda.FORMA_PAGAMENTO_CHOICES,
        'frequencias': Venda.FREQUENCIA_CHOICES,
    }
    
    return render(request, 'compliance/pos_venda/gestao_detalhada.html', context)


@login_required
@user_passes_test(is_compliance)
def realizar_conferencia(request, venda_id):
    """
    Realiza a conferência dos dados da venda.
    """
    venda = get_object_or_404(Venda, id=venda_id)
    conferencia = get_object_or_404(ConferenciaVendaCompliance, venda=venda)
    
    if request.method == 'POST':
        # Conferência do Cliente
        conferencia.nome_ok = request.POST.get('nome_ok') == 'on'
        conferencia.cpf_ok = request.POST.get('cpf_ok') == 'on'
        conferencia.telefone_ok = request.POST.get('telefone_ok') == 'on'
        conferencia.email_ok = request.POST.get('email_ok') == 'on'
        conferencia.endereco_ok = request.POST.get('endereco_ok') == 'on'
        
        # Conferência da Venda
        conferencia.servico_ok = request.POST.get('servico_ok') == 'on'
        conferencia.valores_ok = request.POST.get('valores_ok') == 'on'
        conferencia.parcelas_ok = request.POST.get('parcelas_ok') == 'on'
        conferencia.forma_pagamento_ok = request.POST.get('forma_pagamento_ok') == 'on'
        conferencia.datas_ok = request.POST.get('datas_ok') == 'on'
        
        # Verificar se todos os campos do cliente estão OK
        conferencia.dados_cliente_conferidos = all([
            conferencia.nome_ok,
            conferencia.cpf_ok,
            conferencia.telefone_ok,
            conferencia.email_ok,
            conferencia.endereco_ok
        ])
        
        # Verificar se todos os campos da venda estão OK
        conferencia.dados_venda_conferidos = all([
            conferencia.servico_ok,
            conferencia.valores_ok,
            conferencia.parcelas_ok,
            conferencia.forma_pagamento_ok,
            conferencia.datas_ok
        ])
        
        conferencia.observacoes_conferencia = request.POST.get('observacoes', '')
        conferencia.save()
        
        messages.success(request, 'Conferência atualizada com sucesso!')
        return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
    
    return redirect('compliance:gestao_pos_venda', venda_id=venda_id)


@login_required
@user_passes_test(is_compliance)
def aprovar_conferencia(request, venda_id):
    """
    Aprova a conferência e avança para coleta de documentos.
    """
    if request.method == 'POST':
        venda = get_object_or_404(Venda, id=venda_id)
        conferencia = get_object_or_404(ConferenciaVendaCompliance, venda=venda)
        
        # Verificar se todos os dados foram conferidos
        if not (conferencia.dados_cliente_conferidos and conferencia.dados_venda_conferidos):
            messages.error(request, 'Todos os dados devem ser conferidos antes de aprovar!')
            return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
        
        # Aprovar conferência
        conferencia.aprovar_conferencia(request.user)
        
        # AJUSTE: Como a etapa de documentos está desabilitada,
        # marcamos todos_documentos_ok = True automaticamente
        # para permitir a geração do contrato
        conferencia.todos_documentos_ok = True
        
        # Atualizar status para EMITINDO_CONTRATO
        conferencia.status = StatusPosVendaCompliance.EMITINDO_CONTRATO
        conferencia.save()
        
        messages.success(request, 'Conferência aprovada! Agora você pode gerar o contrato.')
        return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
    
    return redirect('compliance:painel_pos_venda')


@login_required
@user_passes_test(is_compliance)
def reprovar_conferencia(request, venda_id):
    """
    Reprova a conferência e solicita correções ao consultor.
    """
    if request.method == 'POST':
        venda = get_object_or_404(Venda, id=venda_id)
        conferencia = get_object_or_404(ConferenciaVendaCompliance, venda=venda)
        
        motivo = request.POST.get('motivo_reprovacao', '')
        if not motivo:
            messages.error(request, 'É necessário informar o motivo da reprovação!')
            return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
        
        # Reprovar conferência
        conferencia.reprovar_conferencia(request.user, motivo)
        
        # TODO: Enviar notificação ao consultor
        
        messages.warning(request, f'Conferência reprovada. Consultor será notificado.')
        return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
    
    return redirect('compliance:painel_pos_venda')


@login_required
@user_passes_test(is_compliance)
def reabrir_conferencia(request, venda_id):
    """
    Reabre uma conferência aprovada para edição.
    """
    if request.method == 'POST':
        venda = get_object_or_404(Venda, id=venda_id)
        conferencia = get_object_or_404(ConferenciaVendaCompliance, venda=venda)
        
        # Voltar status para aguardando conferência
        conferencia.status = StatusPosVendaCompliance.AGUARDANDO_CONFERENCIA
        conferencia.save()
        
        # Voltar status da venda também
        venda.status_compliance_pos_venda = StatusPosVendaCompliance.AGUARDANDO_CONFERENCIA
        venda.save()
        
        conferencia.adicionar_historico(
            acao='CONFERENCIA_REABERTA',
            usuario=request.user,
            descricao='Conferência reaberta para edição/correção'
        )
        
        messages.info(request, 'Conferência reaberta para edição. Faça as correções necessárias.')
        return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
    
    return redirect('compliance:painel_pos_venda')


@login_required
@user_passes_test(is_compliance)
def corrigir_status_pos_venda(request, venda_id):
    """
    Corrige o status de pós-venda para AGUARDANDO_ASSINATURA quando o contrato já foi enviado.
    """
    if request.method == 'POST':
        venda = get_object_or_404(Venda, id=venda_id)
        conferencia = get_object_or_404(ConferenciaVendaCompliance, venda=venda)
        
        novo_status = request.POST.get('novo_status')
        
        if novo_status in dict(StatusPosVendaCompliance.choices):
            conferencia.status = novo_status
            conferencia.save()
            
            conferencia.adicionar_historico(
                acao='STATUS_CORRIGIDO',
                usuario=request.user,
                descricao=f'Status corrigido manualmente para {conferencia.get_status_display()}'
            )
            
            messages.success(request, f'Status atualizado para: {conferencia.get_status_display()}')
        else:
            messages.error(request, 'Status inválido!')
        
        return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
    
    return redirect('compliance:painel_pos_venda')


@login_required
@user_passes_test(is_compliance)
def editar_dados_venda(request, venda_id):
    """
    Permite editar dados da venda e do cliente.
    """
    if request.method == 'POST':
        venda = get_object_or_404(Venda, id=venda_id)
        cliente = venda.cliente
        lead = cliente.lead
        
        # Atualizar dados do Lead
        lead.nome_completo = request.POST.get('nome_completo', lead.nome_completo)
        lead.cpf_cnpj = request.POST.get('cpf_cnpj', lead.cpf_cnpj)
        lead.telefone = request.POST.get('telefone', lead.telefone)
        lead.email = request.POST.get('email', lead.email)
        lead.save()
        
        # Atualizar dados do Cliente
        cliente.rg = request.POST.get('rg', cliente.rg)
        data_nasc = request.POST.get('data_nascimento')
        if data_nasc:
            cliente.data_nascimento = data_nasc
        cliente.profissao = request.POST.get('profissao', cliente.profissao)
        cliente.nacionalidade = request.POST.get('nacionalidade', cliente.nacionalidade)
        cliente.estado_civil = request.POST.get('estado_civil', cliente.estado_civil)
        cliente.cep = request.POST.get('cep', cliente.cep)
        cliente.rua = request.POST.get('rua', cliente.rua)
        cliente.numero = request.POST.get('numero', cliente.numero)
        cliente.bairro = request.POST.get('bairro', cliente.bairro)
        cliente.cidade = request.POST.get('cidade', cliente.cidade)
        cliente.estado = request.POST.get('estado', cliente.estado)
        cliente.save()
        
        # Atualizar dados da Venda (convertendo tipos corretamente)
        from decimal import Decimal, InvalidOperation
        def parse_decimal(val, default):
            try:
                return Decimal(str(val).replace(',', '.'))
            except (InvalidOperation, TypeError, ValueError):
                return default

        def parse_int(val, default):
            try:
                return int(val)
            except (TypeError, ValueError):
                return default

        valor_total = request.POST.get('valor_total', venda.valor_total)
        venda.valor_total = parse_decimal(valor_total, venda.valor_total)

        valor_entrada = request.POST.get('valor_entrada', venda.valor_entrada)
        venda.valor_entrada = parse_decimal(valor_entrada, venda.valor_entrada)

        quantidade_parcelas = request.POST.get('quantidade_parcelas', venda.quantidade_parcelas)
        venda.quantidade_parcelas = parse_int(quantidade_parcelas, venda.quantidade_parcelas)

        valor_parcela = request.POST.get('valor_parcela', venda.valor_parcela)
        venda.valor_parcela = parse_decimal(valor_parcela, venda.valor_parcela)

        venda.frequencia_pagamento = request.POST.get('frequencia_pagamento', venda.frequencia_pagamento)
        venda.forma_entrada = request.POST.get('forma_entrada', venda.forma_entrada)
        venda.forma_pagamento = request.POST.get('forma_pagamento', venda.forma_pagamento)

        data_venc = request.POST.get('data_vencimento_primeira')
        if data_venc:
            venda.data_vencimento_primeira = data_venc

        data_inicio = request.POST.get('data_inicio_servico')
        if data_inicio:
            venda.data_inicio_servico = data_inicio

        dias_conclusao = request.POST.get('dias_para_conclusao')
        if dias_conclusao:
            venda.dias_para_conclusao = parse_int(dias_conclusao, venda.dias_para_conclusao)

        venda.save()
        
        messages.success(request, 'Dados atualizados com sucesso!')
        return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
    
    return redirect('compliance:gestao_pos_venda', venda_id=venda_id)


@login_required
@user_passes_test(is_compliance)
def upload_documento(request, venda_id):
    """
    Upload de documento para a venda.
    """
    if request.method == 'POST':
        venda = get_object_or_404(Venda, id=venda_id)
        conferencia = get_object_or_404(ConferenciaVendaCompliance, venda=venda)
        
        documento_id = request.POST.get('documento_id')
        arquivo = request.FILES.get('arquivo')
        
        if not arquivo:
            messages.error(request, 'Nenhum arquivo foi enviado!')
            return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
        
        documento = get_object_or_404(DocumentoVendaCompliance, id=documento_id, conferencia=conferencia)
        documento.arquivo = arquivo
        documento.status = StatusDocumento.RECEBIDO
        documento.data_upload = timezone.now()
        documento.save()
        
        conferencia.adicionar_historico(
            acao='DOCUMENTO_RECEBIDO',
            usuario=request.user,
            descricao=f'Documento {documento.get_tipo_display()} recebido'
        )
        
        messages.success(request, f'Documento {documento.get_tipo_display()} enviado com sucesso!')
        return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
    
    return redirect('compliance:painel_pos_venda')


@login_required
@user_passes_test(is_compliance)
def validar_documento(request, venda_id, documento_id):
    """
    Valida (aprova ou rejeita) um documento.
    """
    if request.method == 'POST':
        venda = get_object_or_404(Venda, id=venda_id)
        conferencia = get_object_or_404(ConferenciaVendaCompliance, venda=venda)
        documento = get_object_or_404(DocumentoVendaCompliance, id=documento_id, conferencia=conferencia)
        
        acao = request.POST.get('acao')  # 'aprovar' ou 'rejeitar'
        
        if acao == 'aprovar':
            documento.aprovar(request.user)
            messages.success(request, f'Documento {documento.get_tipo_display()} aprovado!')
        elif acao == 'rejeitar':
            motivo = request.POST.get('motivo_rejeicao', '')
            if not motivo:
                messages.error(request, 'É necessário informar o motivo da rejeição!')
                return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
            
            documento.rejeitar(request.user, motivo)
            messages.warning(request, f'Documento {documento.get_tipo_display()} rejeitado.')
        
        # Verificar se todos os documentos obrigatórios foram aprovados
        documentos_obrigatorios = conferencia.documentos.filter(obrigatorio=True)
        todos_aprovados = all(doc.status == StatusDocumento.APROVADO for doc in documentos_obrigatorios)
        
        if todos_aprovados:
            conferencia.todos_documentos_ok = True
            conferencia.status = StatusPosVendaCompliance.DOCUMENTOS_OK
            conferencia.save()
            
            venda.status_compliance_pos_venda = StatusPosVendaCompliance.DOCUMENTOS_OK
            venda.save()
            
            messages.success(request, 'Todos os documentos obrigatórios foram aprovados!')
        
        return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
    
    return redirect('compliance:painel_pos_venda')


@login_required
@user_passes_test(is_compliance)
def gerar_contrato(request, venda_id):
    """
    Gera o contrato em PDF para a venda.
    """
    if request.method == 'POST':
        venda = get_object_or_404(Venda, id=venda_id)
        conferencia = get_object_or_404(ConferenciaVendaCompliance, venda=venda)
        
        # Verificar se documentos estão OK
        if not conferencia.todos_documentos_ok:
            messages.error(request, 'Todos os documentos obrigatórios devem estar aprovados antes de gerar o contrato!')
            return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
        
        # Obter ou criar contrato
        contrato, created = ContratoCompliance.objects.get_or_create(
            venda=venda,
            defaults={'conferencia': conferencia}
        )
        
        if not contrato.numero_contrato:
            contrato.gerar_numero_contrato()
        
        template = request.POST.get('template', 'padrao')
        contrato.template_utilizado = template
        
        # TODO: Implementar geração real do PDF
        # Por enquanto, apenas marcar como gerado
        contrato.marcar_como_gerado(request.user)
        
        # Atualizar status da conferência
        conferencia.status = StatusPosVendaCompliance.EMITINDO_CONTRATO
        conferencia.save()
        
        messages.success(request, f'Contrato {contrato.numero_contrato} gerado com sucesso!')
        return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
    
    return redirect('compliance:painel_pos_venda')


@login_required
@user_passes_test(is_compliance)
def enviar_contrato(request, venda_id):
    """
    Envia o contrato por WhatsApp e/ou Email.
    """
    if request.method == 'POST':
        venda = get_object_or_404(Venda, id=venda_id)
        contrato = get_object_or_404(ContratoCompliance, venda=venda)
        
        enviar_whatsapp = request.POST.get('enviar_whatsapp') == 'on'
        enviar_email = request.POST.get('enviar_email') == 'on'
        
        if not (enviar_whatsapp or enviar_email):
            messages.error(request, 'Selecione pelo menos um canal de envio!')
            return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
        
        # TODO: Implementar envio real via WhatsApp e Email
        
        if enviar_whatsapp:
            numero = venda.cliente.lead.telefone
            contrato.marcar_envio_whatsapp(request.user, numero)
            messages.success(request, f'Contrato enviado via WhatsApp para {numero}')
        
        if enviar_email:
            email = venda.cliente.lead.email
            contrato.marcar_envio_email(request.user, email)
            messages.success(request, f'Contrato enviado via Email para {email}')
        
        # Atualizar status da conferência
        contrato.conferencia.status = StatusPosVendaCompliance.AGUARDANDO_ASSINATURA
        contrato.conferencia.save()
        
        return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
    
    return redirect('compliance:painel_pos_venda')


@login_required
@user_passes_test(is_compliance)
def upload_contrato_assinado(request, venda_id):
    """
    Upload do contrato assinado (assinatura manual).
    """
    if request.method == 'POST':
        venda = get_object_or_404(Venda, id=venda_id)
        contrato = get_object_or_404(ContratoCompliance, venda=venda)
        
        arquivo = request.FILES.get('arquivo_assinado')
        tipo_assinatura = request.POST.get('tipo_assinatura')
        
        if not arquivo:
            messages.error(request, 'Nenhum arquivo foi enviado!')
            return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
        
        contrato.arquivo_assinado = arquivo
        contrato.marcar_como_assinado(request.user, tipo_assinatura)
        
        messages.success(request, 'Contrato assinado recebido!')
        return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
    
    return redirect('compliance:painel_pos_venda')


@login_required
@user_passes_test(is_compliance)
def validar_assinatura(request, venda_id):
    """
    Valida a assinatura do contrato e finaliza o processo.
    """
    if request.method == 'POST':
        venda = get_object_or_404(Venda, id=venda_id)
        contrato = get_object_or_404(ContratoCompliance, venda=venda)
        
        if not contrato.arquivo_assinado:
            messages.error(request, 'Nenhum contrato assinado foi recebido ainda!')
            return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
        
        # Validar assinatura
        contrato.validar_assinatura(request.user)
        
        messages.success(request, 'Assinatura validada! Processo pós-venda concluído.')
        return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
    
    return redirect('compliance:painel_pos_venda')


@login_required
@user_passes_test(is_compliance)
def visualizar_contrato(request, venda_id):
    """
    Visualiza o contrato gerado em PDF.
    """
    venda = get_object_or_404(Venda, id=venda_id)
    contrato = get_object_or_404(ContratoCompliance, venda=venda)
    
    if not contrato.arquivo_gerado:
        messages.error(request, 'Contrato ainda não foi gerado!')
        return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
    
    # Retornar o arquivo PDF
    return FileResponse(contrato.arquivo_gerado.open('rb'), content_type='application/pdf')


@login_required
@user_passes_test(is_compliance)
def adicionar_documento_extra(request, venda_id):
    """
    Adiciona um documento extra (não obrigatório) à conferência.
    """
    if request.method == 'POST':
        venda = get_object_or_404(Venda, id=venda_id)
        conferencia = get_object_or_404(ConferenciaVendaCompliance, venda=venda)
        
        tipo = request.POST.get('tipo_documento')
        observacao = request.POST.get('observacao', '')
        
        # Criar documento
        DocumentoVendaCompliance.objects.create(
            conferencia=conferencia,
            tipo=tipo,
            obrigatorio=False,
            observacao=observacao
        )
        
        conferencia.adicionar_historico(
            acao='DOCUMENTO_EXTRA_SOLICITADO',
            usuario=request.user,
            descricao=f'Documento adicional solicitado: {dict(TipoDocumento.choices).get(tipo)}'
        )
        
        messages.success(request, 'Documento adicional solicitado com sucesso!')
        return redirect('compliance:gestao_pos_venda', venda_id=venda_id)
    
    return redirect('compliance:painel_pos_venda')
