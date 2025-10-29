from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.db.models import Count, Avg, Q, Sum
from django.utils import timezone
from datetime import timedelta
from vendas.models import Venda
from clientes.models import Cliente
from .forms import NovaInteracaoForm
from .models import (
    InteracaoCliente, PesquisaSatisfacao, Indicacao,
    ProgramaFidelidade, CanalComunicacao
)


@login_required
def painel_relacionamento(request):
    """Painel principal do módulo de relacionamento"""
    hoje = timezone.now().date()
    
    # Estatísticas gerais
    total_interacoes = InteracaoCliente.objects.count()
    interacoes_pendentes = InteracaoCliente.objects.filter(status='agendada').count()
    interacoes_hoje = InteracaoCliente.objects.filter(
        data_agendada__date=hoje
    ).count()
    
    # Pesquisas de satisfação
    pesquisas_respondidas = PesquisaSatisfacao.objects.filter(respondida_em__isnull=False).count()
    pesquisas_pendentes = PesquisaSatisfacao.objects.filter(respondida_em__isnull=True).count()
    media_satisfacao = PesquisaSatisfacao.objects.filter(
        nota_geral__isnull=False
    ).aggregate(Avg('nota_geral'))['nota_geral__avg'] or 0
    
    # Indicações
    total_indicacoes = Indicacao.objects.count()
    indicacoes_convertidas = Indicacao.objects.filter(status='convertido').count()
    taxa_conversao = (indicacoes_convertidas / total_indicacoes * 100) if total_indicacoes > 0 else 0
    
    # Últimas interações
    ultimas_interacoes = InteracaoCliente.objects.select_related(
        'cliente', 'responsavel', 'canal'
    ).order_by('-criado_em')[:10]
    
    # Interações agendadas próximas
    proximas_interacoes = InteracaoCliente.objects.filter(
        status='agendada',
        data_agendada__gte=timezone.now()
    ).select_related('cliente', 'responsavel').order_by('data_agendada')[:10]
    
    context = {
        'total_interacoes': total_interacoes,
        'interacoes_pendentes': interacoes_pendentes,
        'interacoes_hoje': interacoes_hoje,
        'pesquisas_respondidas': pesquisas_respondidas,
        'pesquisas_pendentes': pesquisas_pendentes,
        'media_satisfacao': round(media_satisfacao, 1),
        'total_indicacoes': total_indicacoes,
        'indicacoes_convertidas': indicacoes_convertidas,
        'taxa_conversao': round(taxa_conversao, 1),
        'ultimas_interacoes': ultimas_interacoes,
        'proximas_interacoes': proximas_interacoes,
    }
    
    return render(request, 'relacionamento/painel_relacionamento.html', context)


@login_required
def lista_interacoes(request):
    """Lista todas as interações com filtros"""
    interacoes = InteracaoCliente.objects.select_related(
        'cliente', 'responsavel', 'canal'
    ).order_by('-data_agendada', '-criado_em')
    
    # Filtros
    tipo = request.GET.get('tipo')
    status = request.GET.get('status')
    cliente_id = request.GET.get('cliente')
    
    if tipo:
        interacoes = interacoes.filter(tipo=tipo)
    if status:
        interacoes = interacoes.filter(status=status)
    if cliente_id:
        interacoes = interacoes.filter(cliente_id=cliente_id)
    
    context = {
        'interacoes': interacoes,
        'tipos': InteracaoCliente.TIPO_CHOICES,
        'status_choices': InteracaoCliente.STATUS_CHOICES,
    }
    
    return render(request, 'relacionamento/lista_interacoes.html', context)


@login_required
def nova_interacao(request):
    """Criar nova interação com cliente"""
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        tipo = request.POST.get('tipo')
        canal_id = request.POST.get('canal_id')
        assunto = request.POST.get('assunto')
        mensagem = request.POST.get('mensagem')
        data_agendada = request.POST.get('data_agendada')
        
        interacao = InteracaoCliente.objects.create(
            cliente_id=cliente_id,
            tipo=tipo,
            canal_id=canal_id,
            assunto=assunto,
            mensagem=mensagem,
            data_agendada=data_agendada if data_agendada else None,
            criado_por=request.user,
            responsavel=request.user,
        )
        
        return redirect('relacionamento:detalhe_interacao', pk=interacao.pk)
    
    clientes = Cliente.objects.select_related('lead').all().order_by('lead__nome_completo')
    canais = CanalComunicacao.objects.filter(ativo=True)

    form = NovaInteracaoForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        interacao = form.save(commit=False)
        interacao.criado_por = request.user
        interacao.responsavel = request.user
        interacao.save()
        return redirect('relacionamento:detalhe_interacao', pk=interacao.pk)

    context = {
        'form': form,
        'clientes': clientes,
        'canais': canais,
        'tipos': InteracaoCliente.TIPO_CHOICES,
    }

    return render(request, 'relacionamento/nova_interacao.html', context)


@login_required
def detalhe_interacao(request, pk):
    """Detalhes e edição de interação"""
    interacao = get_object_or_404(InteracaoCliente, pk=pk)
    
    if request.method == 'POST':
        interacao.status = request.POST.get('status', interacao.status)
        interacao.resposta_cliente = request.POST.get('resposta_cliente', interacao.resposta_cliente)
        interacao.observacoes = request.POST.get('observacoes', interacao.observacoes)
        
        if request.POST.get('status') == 'realizada' and not interacao.data_realizada:
            interacao.data_realizada = timezone.now()
        
        interacao.save()
        
        return redirect('relacionamento:detalhe_interacao', pk=pk)
    
    context = {
        'interacao': interacao,
        'status_choices': InteracaoCliente.STATUS_CHOICES,
    }
    
    return render(request, 'relacionamento/detalhe_interacao.html', context)


@login_required
def pesquisas_satisfacao(request):
    """Lista de pesquisas de satisfação"""
    pesquisas = PesquisaSatisfacao.objects.select_related(
        'cliente', 'venda'
    ).order_by('-enviada_em')
    
    # Filtros
    respondida = request.GET.get('respondida')
    if respondida == 'sim':
        pesquisas = pesquisas.filter(respondida_em__isnull=False)
    elif respondida == 'nao':
        pesquisas = pesquisas.filter(respondida_em__isnull=True)
    
    context = {
        'pesquisas': pesquisas,
    }
    
    return render(request, 'relacionamento/pesquisas_satisfacao.html', context)


@login_required
def nova_pesquisa(request):
    """Criar nova pesquisa de satisfação"""
    if request.method == 'POST':
        cliente_id = request.POST.get('cliente_id')
        venda_id = request.POST.get('venda_id')
        
        # Criar interação
        interacao = InteracaoCliente.objects.create(
            cliente_id=cliente_id,
            venda_id=venda_id if venda_id else None,
            tipo='pesquisa',
            assunto='Pesquisa de Satisfação',
            mensagem='Pesquisa de satisfação enviada ao cliente',
            criado_por=request.user,
            responsavel=request.user,
            status='realizada',
            data_realizada=timezone.now(),
        )
        
        # Criar pesquisa
        pesquisa = PesquisaSatisfacao.objects.create(
            interacao=interacao,
            cliente_id=cliente_id,
            venda_id=venda_id if venda_id else None,
        )
        
        return redirect('relacionamento:pesquisas_satisfacao')
    
    clientes = Cliente.objects.select_related('lead').all().order_by('lead__nome_completo')
    
    context = {
        'clientes': clientes,
    }
    
    return render(request, 'relacionamento/nova_pesquisa.html', context)


@login_required
def indicacoes(request):
    """Lista de indicações"""
    indicacoes_list = Indicacao.objects.select_related('cliente_indicador').all()
    context = {
        'indicacoes': indicacoes_list,
    }
    return render(request, 'relacionamento/indicacoes.html', context)


@login_required
def nova_indicacao(request):
    """Criar nova indicação"""
    if request.method == 'POST':
        # Processar formulário de indicação
        pass
    
    clientes = Cliente.objects.select_related('lead').all()
    context = {
        'clientes': clientes,
    }
    return render(request, 'relacionamento/nova_indicacao.html', context)


@login_required
def programa_fidelidade(request):
    """Painel do programa de fidelidade"""
    programas = ProgramaFidelidade.objects.select_related('cliente').order_by('-pontos_disponiveis')
    
    # Estatísticas
    total_clientes = programas.count()
    total_pontos = programas.aggregate(Sum('pontos_totais'))['pontos_totais__sum'] or 0
    
    context = {
        'programas': programas,
        'total_clientes': total_clientes,
        'total_pontos': total_pontos,
    }
    
    return render(request, 'relacionamento/programa_fidelidade.html', context)


@login_required
def detalhe_fidelidade(request, cliente_id):
    """Detalhes do programa de fidelidade de um cliente"""
    cliente = get_object_or_404(Cliente, pk=cliente_id)
    
    # Criar programa se não existir
    programa, created = ProgramaFidelidade.objects.get_or_create(cliente=cliente)
    
    # Histórico de movimentações
    movimentacoes = programa.movimentacoes.all()[:20]
    
    context = {
        'cliente': cliente,
        'programa': programa,
        'movimentacoes': movimentacoes,
    }
    
    return render(request, 'relacionamento/detalhe_fidelidade.html', context)
