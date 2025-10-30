from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone
from .models import Cliente
from vendas.models import Venda, ProgressoServico
from financeiro.models import Parcela


def is_cliente(user):
    """Verifica se o usuário pertence ao grupo 'cliente' ou é admin"""
    if user.is_superuser or user.groups.filter(name='admin').exists():
        return True
    return user.groups.filter(name='cliente').exists()


@login_required
@user_passes_test(is_cliente)
def area_cliente(request):
    """
    Área do cliente - Acompanhamento do progresso do serviço
    """
    print("="*80)
    print(f"🔵 AREA_CLIENTE VIEW EXECUTANDO")
    print(f"User: {request.user}")
    print(f"User ID: {request.user.id}")
    print(f"Is authenticated: {request.user.is_authenticated}")
    print(f"Groups: {list(request.user.groups.values_list('name', flat=True))}")
    print("="*80)
    
    try:
        # Busca o cliente relacionado ao usuário logado
        cliente = Cliente.objects.get(usuario_portal=request.user)
        print(f"✅ Cliente encontrado: {cliente}")
        
        # Busca a venda mais recente do cliente
        venda = Venda.objects.filter(cliente=cliente).order_by('-data_criacao').first()
        print(f"Venda encontrada: {venda}")
        
        if not venda:
            # Renderiza página informando que ainda não há serviços
            print("⚠️ Nenhuma venda encontrada, renderizando página sem serviços")
            context = {
                'cliente': cliente,
                'sem_servicos': True,
                'usuario': request.user
            }
            return render(request, 'clientes/area_cliente.html', context)
        
        # Busca ou cria o progresso do serviço
        progresso, criado = ProgressoServico.objects.get_or_create(
            venda=venda,
            defaults={
                'etapa_atual': 0,
                'data_etapa_1': timezone.now()
            }
        )
        
        # Próxima atualização prevista
        proxima_atualizacao = progresso.get_proxima_atualizacao()
        
        # Situação do serviço
        if progresso.etapa_atual == 100:
            situacao = "Concluído"
        else:
            situacao = "Em andamento"
        
        # Estatísticas do serviço
        total_etapas = 6
        etapas_concluidas = progresso.etapa_atual // 20
        
        # Informações das etapas
        etapas = [
            {
                'numero': 1,
                'percentual': 0,
                'titulo': 'Atendimento Iniciado e Preparação da Defesa',
                'status': '✅ Concluído' if progresso.etapa_atual >= 0 else '⏳ Pendente',
                'descricao': 'Seu atendimento foi iniciado e nossos especialistas já elaboraram o resumo técnico do caso.',
                'concluida': progresso.etapa_atual >= 0,
                'data_conclusao': progresso.data_etapa_1
            },
            {
                'numero': 2,
                'percentual': 20,
                'titulo': 'Elaboração e Protocolo da Defesa (15 dias)',
                'status': '✅ Concluído' if progresso.etapa_atual >= 20 else ('⚙️ Em andamento' if progresso.etapa_atual == 0 else '⏳ Pendente'),
                'descricao': 'Nossa equipe elabora a defesa administrativa personalizada e encaminha aos órgãos de proteção ao crédito.',
                'concluida': progresso.etapa_atual >= 20,
                'data_conclusao': progresso.data_etapa_2
            },
            {
                'numero': 3,
                'percentual': 40,
                'titulo': 'Análise e Retorno dos Órgãos (30 dias)',
                'status': '✅ Concluído' if progresso.etapa_atual >= 40 else ('⚙️ Em andamento' if progresso.etapa_atual == 20 else '⏳ Pendente'),
                'descricao': 'As defesas protocoladas estão sendo analisadas pelos órgãos competentes.',
                'concluida': progresso.etapa_atual >= 40,
                'data_conclusao': progresso.data_etapa_3
            },
            {
                'numero': 4,
                'percentual': 60,
                'titulo': 'Monitoramento das Atualizações (45 dias)',
                'status': '✅ Concluído' if progresso.etapa_atual >= 60 else ('🔄 Em andamento' if progresso.etapa_atual == 40 else '⏳ Pendente'),
                'descricao': 'Monitoramento constante dos sistemas de crédito para identificar eventuais alterações.',
                'concluida': progresso.etapa_atual >= 60,
                'data_conclusao': progresso.data_etapa_4
            },
            {
                'numero': 5,
                'percentual': 80,
                'titulo': 'Conclusão das Atualizações (60 dias)',
                'status': '✅ Concluído' if progresso.etapa_atual >= 80 else ('🔄 Em andamento' if progresso.etapa_atual == 60 else '⏳ Pendente'),
                'descricao': 'Grande parte das respostas já foram recebidas. Atuando sobre os casos pendentes.',
                'concluida': progresso.etapa_atual >= 80,
                'data_conclusao': progresso.data_etapa_5
            },
            {
                'numero': 6,
                'percentual': 100,
                'titulo': 'Encerramento e Confirmação Final (90 dias)',
                'status': '✅ Concluído' if progresso.etapa_atual >= 100 else ('🏁 Em fase final' if progresso.etapa_atual == 80 else '⏳ Pendente'),
                'descricao': 'Validação final das atualizações e comunicação de encerramento do atendimento.',
                'concluida': progresso.etapa_atual >= 100,
                'data_conclusao': progresso.data_etapa_6
            },
        ]
        
        # Busca parcelas do cliente
        parcelas = Parcela.objects.filter(venda=venda).order_by('data_vencimento')[:5]
        
        context = {
            'cliente': cliente,
            'venda': venda,
            'progresso': progresso,
            'proxima_atualizacao': proxima_atualizacao,
            'situacao': situacao,
            'total_etapas': total_etapas,
            'etapas_concluidas': etapas_concluidas,
            'etapas': etapas,
            'parcelas': parcelas,
        }
        
        return render(request, 'clientes/area_cliente.html', context)
        
    except Cliente.DoesNotExist:
        print(f"❌ ERRO: Cliente não encontrado para usuário {request.user.username}")
        # Renderiza página informando que o perfil não foi encontrado
        context = {
            'sem_perfil': True,
            'usuario': request.user,
            'mensagem': f'Perfil de cliente não encontrado para o usuário: {request.user.username}. Entre em contato com o suporte para criar seu perfil.'
        }
        return render(request, 'clientes/area_cliente.html', context)
    except Exception as e:
        print(f"❌ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()
        # Renderiza página de erro
        context = {
            'erro_geral': True,
            'usuario': request.user,
            'mensagem': f'Erro ao carregar área do cliente: {str(e)}'
        }
        return render(request, 'clientes/area_cliente.html', context)


@login_required
@user_passes_test(is_cliente)
def boletos_cliente(request):
    """
    Tela para o cliente visualizar e baixar seus boletos
    """
    print("="*80)
    print(f"🔵 BOLETOS_CLIENTE VIEW EXECUTANDO")
    print(f"User: {request.user}")
    print("="*80)
    
    try:
        # Busca o cliente relacionado ao usuário logado
        cliente = Cliente.objects.get(usuario_portal=request.user)
        print(f"✅ Cliente encontrado: {cliente}")
        
        # Busca a venda mais recente do cliente
        venda = Venda.objects.filter(cliente=cliente).order_by('-data_criacao').first()
        print(f"Venda encontrada: {venda}")
        
        if not venda:
            context = {
                'cliente': cliente,
                'sem_servicos': True,
            }
            return render(request, 'clientes/boletos_cliente.html', context)
        
        # Busca todas as parcelas do cliente
        parcelas = Parcela.objects.filter(venda=venda).order_by('numero_parcela')
        
        # Estatísticas
        from datetime import date
        total_parcelas = parcelas.count()
        parcelas_pagas = parcelas.filter(status='paga').count()
        parcelas_vencidas = parcelas.filter(status='vencida').count()
        parcelas_abertas = parcelas.filter(status='aberta').count()
        
        # Calcular valor total, pago e pendente
        valor_total = sum([p.valor for p in parcelas])
        valor_pago = sum([p.valor for p in parcelas if p.status == 'paga'])
        valor_pendente = valor_total - valor_pago
        
        # Calcular percentual pago
        percentual_pago = (valor_pago / valor_total * 100) if valor_total > 0 else 0
        
        # Calcular dias de atraso para parcelas vencidas
        hoje = date.today()
        for parcela in parcelas:
            if parcela.status == 'vencida' and not parcela.data_pagamento:
                parcela.dias_atraso = (hoje - parcela.data_vencimento).days
            else:
                parcela.dias_atraso = 0
        
        context = {
            'cliente': cliente,
            'venda': venda,
            'parcelas': parcelas,
            'total_parcelas': total_parcelas,
            'parcelas_pagas': parcelas_pagas,
            'parcelas_vencidas': parcelas_vencidas,
            'parcelas_abertas': parcelas_abertas,
            'valor_total': valor_total,
            'valor_pago': valor_pago,
            'valor_pendente': valor_pendente,
            'percentual_pago': percentual_pago,
            'hoje': hoje,
        }
        
        return render(request, 'clientes/boletos_cliente.html', context)
        
    except Cliente.DoesNotExist:
        print(f"❌ ERRO: Cliente não encontrado para usuário {request.user.username}")
        context = {
            'sem_perfil': True,
            'mensagem': f'Perfil de cliente não encontrado para o usuário: {request.user.username}.'
        }
        return render(request, 'clientes/boletos_cliente.html', context)
    except Exception as e:
        print(f"❌ ERRO GERAL: {e}")
        import traceback
        traceback.print_exc()
        context = {
            'erro_geral': True,
            'mensagem': f'Erro ao carregar boletos: {str(e)}'
        }
        return render(request, 'clientes/boletos_cliente.html', context)
