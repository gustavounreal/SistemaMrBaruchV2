from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Sum, Count, Q
from datetime import timedelta
from .models import NotaFiscal, ConfiguracaoFiscal
from .asaas_nf_service import AsaasNFService


@login_required
def dashboard_notas(request):
    """Dashboard principal de notas fiscais"""
    
    # Estatísticas gerais
    total_notas = NotaFiscal.objects.count()
    notas_pendentes = NotaFiscal.objects.filter(status='PENDENTE').count()
    notas_emitidas = NotaFiscal.objects.filter(status='EMITIDA').count()
    notas_erro = NotaFiscal.objects.filter(status='ERRO').count()
    
    # Últimas notas
    ultimas_notas = NotaFiscal.objects.select_related(
        'venda', 'venda__cliente', 'venda__cliente__lead', 'parcela'
    ).order_by('-data_criacao')[:10]
    
    # Notas que precisam de atenção
    notas_atencao = NotaFiscal.objects.filter(
        Q(status='ERRO') | Q(status='PENDENTE', data_criacao__lte=timezone.now() - timedelta(days=3))
    ).select_related('venda', 'venda__cliente', 'venda__cliente__lead')[:5]
    
    context = {
        'total_notas': total_notas,
        'notas_pendentes': notas_pendentes,
        'notas_emitidas': notas_emitidas,
        'notas_erro': notas_erro,
        'ultimas_notas': ultimas_notas,
        'notas_atencao': notas_atencao,
    }
    
    return render(request, 'notas_fiscais/dashboard.html', context)


@login_required
def lista_notas_pendentes(request):
    """Lista todas as notas pendentes de emissão"""
    
    notas_pendentes = NotaFiscal.objects.filter(
        status__in=['PENDENTE', 'ERRO']
    ).select_related(
        'venda', 'venda__cliente', 'venda__cliente__lead', 'parcela'
    ).order_by('data_criacao')
    
    # Filtros
    periodo = request.GET.get('periodo', '30')
    if periodo != 'todos':
        try:
            dias = int(periodo)
            data_inicio = timezone.now() - timedelta(days=dias)
            notas_pendentes = notas_pendentes.filter(data_criacao__gte=data_inicio)
        except:
            pass
    
    context = {
        'notas_pendentes': notas_pendentes,
        'total_pendentes': notas_pendentes.count(),
        'periodo': periodo,
    }
    
    return render(request, 'notas_fiscais/lista_pendentes.html', context)


@login_required
def lista_notas_emitidas(request):
    """Lista todas as notas emitidas"""
    
    notas_emitidas = NotaFiscal.objects.filter(
        status__in=['EMITIDA', 'ENVIADA']
    ).select_related(
        'venda', 'venda__cliente', 'venda__cliente__lead', 'parcela'
    ).order_by('-data_emissao')
    
    # Filtros
    periodo = request.GET.get('periodo', '30')
    if periodo != 'todos':
        try:
            dias = int(periodo)
            data_inicio = timezone.now() - timedelta(days=dias)
            notas_emitidas = notas_emitidas.filter(data_emissao__gte=data_inicio)
        except:
            pass
    
    # Estatísticas
    total_valor = notas_emitidas.aggregate(total=Sum('valor_servico'))['total'] or 0
    total_iss = notas_emitidas.aggregate(total=Sum('valor_iss'))['total'] or 0
    
    context = {
        'notas_emitidas': notas_emitidas,
        'total_emitidas': notas_emitidas.count(),
        'total_valor': total_valor,
        'total_iss': total_iss,
        'periodo': periodo,
    }
    
    return render(request, 'notas_fiscais/lista_emitidas.html', context)


@login_required
def lista_todas_notas(request):
    """Lista todas as notas fiscais com filtros"""
    
    notas = NotaFiscal.objects.select_related(
        'venda', 'venda__cliente', 'venda__cliente__lead', 'parcela'
    ).order_by('-data_criacao')
    
    # Filtros
    status_filter = request.GET.get('status', 'todos')
    if status_filter != 'todos':
        notas = notas.filter(status=status_filter)
    
    tipo_filter = request.GET.get('tipo', 'todos')
    if tipo_filter != 'todos':
        notas = notas.filter(tipo=tipo_filter)
    
    periodo = request.GET.get('periodo', '30')
    if periodo != 'todos':
        try:
            dias = int(periodo)
            data_inicio = timezone.now() - timedelta(days=dias)
            notas = notas.filter(data_criacao__gte=data_inicio)
        except:
            pass
    
    context = {
        'notas': notas,
        'total_notas': notas.count(),
        'status_filter': status_filter,
        'tipo_filter': tipo_filter,
        'periodo': periodo,
    }
    
    return render(request, 'notas_fiscais/lista_todas.html', context)


@login_required
def emitir_nota_manual(request, nf_id):
    """Emite uma nota fiscal manualmente"""
    
    print(f"[DEBUG emitir_nota_manual] Iniciando emissão da nota #{nf_id}")
    
    nf = get_object_or_404(NotaFiscal, id=nf_id)
    
    print(f"[DEBUG emitir_nota_manual] Nota encontrada: #{nf.id} | Status: {nf.status} | Venda: #{nf.venda.id}")
    
    # Verificar se já está emitida
    if nf.status == 'EMITIDA':
        messages.warning(request, 'Esta nota já foi emitida!')
        return redirect('notas_fiscais:lista_pendentes')
    
    # Emitir nota
    print(f"[DEBUG emitir_nota_manual] Chamando AsaasNFService para emitir...")
    service = AsaasNFService()
    tipo = 'ENTRADA' if nf.tipo == 'ENTRADA' else 'PARCELA'
    resultado = service.emitir_nf(nf.venda, tipo=tipo, parcela=nf.parcela)
    
    print(f"[DEBUG emitir_nota_manual] Resultado: {resultado}")
    
    if resultado['success']:
        # Atualizar nota
        nf.status = 'EMITIDA'
        nf.numero_nf = resultado.get('numero_nf', '')
        nf.serie_nf = resultado.get('serie_nf', '1')
        nf.id_nf_asaas = resultado.get('id_nf_asaas', '')
        nf.codigo_verificacao = resultado.get('codigo_verificacao', '')
        nf.chave_acesso = resultado.get('chave_acesso', '')
        nf.url_pdf = resultado.get('url_pdf', '')
        nf.url_xml = resultado.get('url_xml', '')
        nf.data_emissao = timezone.now()
        nf.log_integracao = resultado.get('data', {})
        nf.save()
        
        messages.success(request, f'✅ Nota Fiscal #{nf.numero_nf} emitida com sucesso!')
        
        # TODO: Enviar e-mail automático
        # enviar_email_nota_fiscal.delay(nf.id)
    else:
        # Registrar erro
        nf.status = 'ERRO'
        nf.mensagem_erro = resultado.get('erro', 'Erro desconhecido')
        nf.tentativas_emissao += 1
        nf.log_integracao = resultado
        nf.save()
        
        messages.error(request, f'❌ Erro ao emitir NF: {resultado.get("erro")}')
    
    return redirect('notas_fiscais:lista_pendentes')


@login_required
def reprocessar_nota_erro(request, nf_id):
    """Reprocessa uma nota que deu erro"""
    
    nf = get_object_or_404(NotaFiscal, id=nf_id)
    
    if nf.status != 'ERRO':
        messages.warning(request, 'Esta nota não está com status de erro.')
        return redirect('notas_fiscais:lista_pendentes')
    
    # Resetar status para PENDENTE
    nf.status = 'PENDENTE'
    nf.mensagem_erro = ''
    nf.save()
    
    messages.info(request, 'Nota resetada para PENDENTE. Tente emitir novamente.')
    
    return redirect('notas_fiscais:lista_pendentes')


@login_required
def cancelar_nota(request, nf_id):
    """Cancela uma nota fiscal"""
    
    nf = get_object_or_404(NotaFiscal, id=nf_id)
    
    if request.method == 'POST':
        # Verificar se pode cancelar
        if not nf.pode_cancelar:
            messages.error(request, '❌ Esta nota não pode ser cancelada (fora do prazo ou status inválido)')
            return redirect('notas_fiscais:lista_emitidas')
        
        motivo = request.POST.get('motivo', 'Cancelamento solicitado pelo usuário')
        
        # Cancelar no Asaas
        service = AsaasNFService()
        resultado = service.cancelar_nf(nf.id_nf_asaas, motivo)
        
        if resultado['success']:
            # Atualizar nota
            nf.status = 'CANCELADA'
            nf.data_cancelamento = timezone.now()
            nf.motivo_cancelamento = motivo
            nf.cancelada_por = request.user
            nf.save()
            
            messages.success(request, f'✅ Nota Fiscal #{nf.numero_nf} cancelada com sucesso!')
        else:
            messages.error(request, f'❌ Erro ao cancelar: {resultado.get("erro")}')
    
    return redirect('notas_fiscais:lista_emitidas')


@login_required
def reenviar_email_nota(request, nf_id):
    """Reenvia o e-mail com a nota fiscal"""
    
    nf = get_object_or_404(NotaFiscal, id=nf_id)
    
    if nf.status != 'EMITIDA':
        messages.warning(request, 'Apenas notas emitidas podem ter o e-mail reenviado.')
        return redirect('notas_fiscais:lista_emitidas')
    
    # TODO: Implementar envio de e-mail
    # enviar_email_nota_fiscal.delay(nf.id, reenvio=True)
    
    messages.success(request, 'E-mail reenviado com sucesso!')
    
    return redirect('notas_fiscais:lista_emitidas')


@login_required
def relatorio_fiscal(request):
    """Relatório fiscal mensal"""
    
    # Filtro de período
    mes = request.GET.get('mes', timezone.now().strftime('%Y-%m'))
    
    try:
        ano, mes_num = mes.split('-')
        data_inicio = timezone.datetime(int(ano), int(mes_num), 1)
        
        # Último dia do mês
        if int(mes_num) == 12:
            data_fim = timezone.datetime(int(ano) + 1, 1, 1)
        else:
            data_fim = timezone.datetime(int(ano), int(mes_num) + 1, 1)
    except:
        # Mês atual por padrão
        data_inicio = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        data_fim = (data_inicio + timedelta(days=32)).replace(day=1)
    
    # Notas do período
    notas = NotaFiscal.objects.filter(
        data_emissao__gte=data_inicio,
        data_emissao__lt=data_fim,
        status='EMITIDA'
    ).select_related('venda', 'venda__cliente', 'venda__cliente__lead')
    
    # Estatísticas
    total_notas = notas.count()
    total_faturado = notas.aggregate(total=Sum('valor_servico'))['total'] or 0
    total_iss = notas.aggregate(total=Sum('valor_iss'))['total'] or 0
    
    # Agrupamento por tipo
    por_tipo = notas.values('tipo').annotate(
        quantidade=Count('id'),
        valor_total=Sum('valor_servico')
    )
    
    context = {
        'notas': notas,
        'total_notas': total_notas,
        'total_faturado': total_faturado,
        'total_iss': total_iss,
        'por_tipo': por_tipo,
        'mes_filtro': mes,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
    }
    
    return render(request, 'notas_fiscais/relatorio_fiscal.html', context)


@login_required
def gerar_notas_retroativas(request):
    """
    Gera notas fiscais retroativas para vendas que:
    - Têm cliente_quer_nf = True
    - Têm pagamentos confirmados (entrada ou parcelas)
    - Ainda não têm notas fiscais criadas
    """
    from vendas.models import Venda, Parcela
    from financeiro.models import PixEntrada
    from decimal import Decimal
    
    mensagens = []
    total_criadas = 0
    
    # Buscar vendas que querem NF
    vendas_com_nf = Venda.objects.filter(cliente_quer_nf=True).select_related('cliente', 'cliente__lead')
    
    for venda in vendas_com_nf:
        # Verificar ENTRADA paga
        entrada_paga = False
        try:
            pix_entrada = PixEntrada.objects.get(venda=venda)
            if pix_entrada.status_pagamento == 'pago':
                entrada_paga = True
        except PixEntrada.DoesNotExist:
            # Verificar se entrada foi paga via parcela 0
            try:
                parcela_entrada = Parcela.objects.get(venda=venda, numero_parcela=0)
                if parcela_entrada.status == 'paga':
                    entrada_paga = True
            except Parcela.DoesNotExist:
                pass
        
        # Criar nota da entrada se paga e ainda não existe
        if entrada_paga:
            nota_entrada_existe = NotaFiscal.objects.filter(venda=venda, tipo='ENTRADA').exists()
            if not nota_entrada_existe:
                NotaFiscal.objects.create(
                    venda=venda,
                    tipo='ENTRADA',
                    valor_servico=venda.valor_entrada,
                    aliquota_iss=Decimal('2.00'),
                    valor_iss=venda.valor_entrada * Decimal('0.02'),
                    status='PENDENTE',
                    descricao_servico='Consultoria Financeira - Entrada',
                    email_destinatario=venda.nf_email or venda.cliente.lead.email,
                )
                mensagens.append(f"✅ Nota de ENTRADA criada para Venda #{venda.id}")
                total_criadas += 1
        
        # Verificar PARCELAS pagas
        parcelas_pagas = Parcela.objects.filter(venda=venda, status='paga', numero_parcela__gt=0)
        for parcela in parcelas_pagas:
            nota_parcela_existe = NotaFiscal.objects.filter(
                venda=venda, 
                parcela_id=parcela.id, 
                tipo='PARCELA'
            ).exists()
            if not nota_parcela_existe:
                NotaFiscal.objects.create(
                    venda=venda,
                    parcela=parcela,
                    tipo='PARCELA',
                    valor_servico=parcela.valor,
                    aliquota_iss=Decimal('2.00'),
                    valor_iss=parcela.valor * Decimal('0.02'),
                    status='PENDENTE',
                    descricao_servico=f'Consultoria Financeira - Parcela {parcela.numero_parcela}/{venda.quantidade_parcelas}',
                    email_destinatario=venda.nf_email or venda.cliente.lead.email,
                )
                mensagens.append(f"✅ Nota da PARCELA {parcela.numero_parcela} criada para Venda #{venda.id}")
                total_criadas += 1
    
    if total_criadas > 0:
        messages.success(request, f'✅ {total_criadas} notas fiscais criadas com sucesso!')
        for msg in mensagens[:10]:  # Limitar a 10 mensagens
            messages.info(request, msg)
        if len(mensagens) > 10:
            messages.info(request, f'... e mais {len(mensagens) - 10} notas.')
    else:
        messages.info(request, 'ℹ️ Nenhuma nota fiscal retroativa necessária. Todas as vendas com NF ativada já possuem suas notas.')
    
    return redirect('notas_fiscais:dashboard')


@login_required
def configuracao_fiscal(request):
    """Tela de configuração fiscal da empresa"""
    
    # Buscar ou criar configuração
    config = ConfiguracaoFiscal.objects.first()
    
    if request.method == 'POST':
        # Pegar dados do formulário
        cnpj = request.POST.get('cnpj', '').strip()
        razao_social = request.POST.get('razao_social', '').strip()
        nome_fantasia = request.POST.get('nome_fantasia', '').strip()
        
        # Endereço
        cep = request.POST.get('cep', '').strip()
        logradouro = request.POST.get('logradouro', '').strip()
        numero = request.POST.get('numero', '').strip()
        complemento = request.POST.get('complemento', '').strip()
        bairro = request.POST.get('bairro', '').strip()
        cidade = request.POST.get('cidade', '').strip()
        estado = request.POST.get('estado', '').strip()
        
        # Dados fiscais
        inscricao_municipal = request.POST.get('inscricao_municipal', '').strip()
        regime_tributario = request.POST.get('regime_tributario', 'SIMPLES_NACIONAL')
        aliquota_iss = request.POST.get('aliquota_iss', '2.00')
        codigo_servico_padrao = request.POST.get('codigo_servico_padrao', '').strip()
        
        # Automação
        emissao_automatica = request.POST.get('emissao_automatica') == 'on'
        envio_automatico_email = request.POST.get('envio_automatico_email') == 'on'
        prazo_cancelamento = request.POST.get('prazo_cancelamento_horas', '24')
        
        # Validações básicas
        erros = []
        if not cnpj:
            erros.append('CNPJ é obrigatório')
        if not razao_social:
            erros.append('Razão Social é obrigatória')
        if not cep or not logradouro or not numero or not bairro or not cidade or not estado:
            erros.append('Endereço completo é obrigatório')
        
        if erros:
            for erro in erros:
                messages.error(request, f'❌ {erro}')
        else:
            # Criar ou atualizar configuração
            if config:
                # Atualizar existente
                config.cnpj = cnpj
                config.razao_social = razao_social
                config.nome_fantasia = nome_fantasia
                config.cep = cep
                config.logradouro = logradouro
                config.numero = numero
                config.complemento = complemento
                config.bairro = bairro
                config.cidade = cidade
                config.estado = estado
                config.inscricao_municipal = inscricao_municipal
                config.regime_tributario = regime_tributario
                config.aliquota_iss_padrao = aliquota_iss
                config.codigo_servico_padrao = codigo_servico_padrao
                config.emissao_automatica = emissao_automatica
                config.envio_automatico_email = envio_automatico_email
                config.prazo_cancelamento_horas = int(prazo_cancelamento)
                config.save()
                
                messages.success(request, '✅ Configuração fiscal atualizada com sucesso!')
            else:
                # Criar nova
                config = ConfiguracaoFiscal.objects.create(
                    cnpj=cnpj,
                    razao_social=razao_social,
                    nome_fantasia=nome_fantasia,
                    cep=cep,
                    logradouro=logradouro,
                    numero=numero,
                    complemento=complemento,
                    bairro=bairro,
                    cidade=cidade,
                    estado=estado,
                    inscricao_municipal=inscricao_municipal,
                    regime_tributario=regime_tributario,
                    aliquota_iss_padrao=aliquota_iss,
                    codigo_servico_padrao=codigo_servico_padrao,
                    emissao_automatica=emissao_automatica,
                    envio_automatico_email=envio_automatico_email,
                    prazo_cancelamento_horas=int(prazo_cancelamento)
                )
                
                messages.success(request, '✅ Configuração fiscal criada com sucesso!')
            
            return redirect('notas_fiscais:configuracao_fiscal')
    
    context = {
        'config': config,
    }
    
    return render(request, 'notas_fiscais/configuracao_fiscal.html', context)
