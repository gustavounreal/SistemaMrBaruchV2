from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, Count
from django.http import Http404
from datetime import date
from vendas.models import Venda
from financeiro.models import Parcela
from .models import LinkCurto, ClickLinkCurto


@login_required
def area_captador(request):
    """
    Área do captador - Dashboard com estatísticas, boletos e materiais
    """
    captador = request.user
    
    # Criar ou recuperar link curto do captador
    link_curto, created = LinkCurto.objects.get_or_create(
        captador=captador,
        defaults={
            'codigo': LinkCurto.gerar_codigo_unico(),
            'url_completa': f"https://wa.me/5511978891213?text=Olá! Fui indicado pelo captador ID: {captador.id}"
        }
    )
    
    # Buscar todas as vendas onde o captador foi indicado
    vendas = Venda.objects.filter(captador=captador).select_related('cliente__lead', 'servico')
    
    # Estatísticas financeiras
    total_vendas = vendas.count()
    valor_total_indicacoes = vendas.aggregate(total=Sum('valor_total'))['total'] or 0
    
    # Comissão (20% do valor total das vendas)
    percentual_comissao = 0.20
    comissao_total = valor_total_indicacoes * percentual_comissao
    
    # Buscar todas as parcelas das vendas do captador
    parcelas = Parcela.objects.filter(venda__captador=captador).select_related('venda__cliente__lead')
    
    # Estatísticas de boletos
    total_parcelas = parcelas.count()
    parcelas_pagas = parcelas.filter(status='paga').count()
    parcelas_vencidas = parcelas.filter(status='vencida').count()
    parcelas_abertas = parcelas.filter(status='aberta').count()
    
    # Valores
    valor_pago = parcelas.filter(status='paga').aggregate(total=Sum('valor'))['total'] or 0
    valor_pendente = parcelas.exclude(status='paga').aggregate(total=Sum('valor'))['total'] or 0
    
    # Comissão recebida e a receber (20% do valor das parcelas)
    comissao_recebida = valor_pago * percentual_comissao
    comissao_a_receber = valor_pendente * percentual_comissao
    
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
    
    # Materiais de marketing do Google Drive
    media_files = [
        {"name": "Imagem 1", "thumbnail_url": "https://drive.google.com/thumbnail?id=1716U_7jTPofWLpwuJmaByH2VwijVunNH", "download_url": "https://drive.google.com/uc?export=download&id=1716U_7jTPofWLpwuJmaByH2VwijVunNH"},
        {"name": "Imagem 2", "thumbnail_url": "https://drive.google.com/thumbnail?id=1750e8o-1hBc1SU2ZOET77oxhsbTFTqyL", "download_url": "https://drive.google.com/uc?export=download&id=1750e8o-1hBc1SU2ZOET77oxhsbTFTqyL"},
        {"name": "Imagem 3", "thumbnail_url": "https://drive.google.com/thumbnail?id=176LkvMMo_Ca6e4_I9i5hN-AOPyteT3M7", "download_url": "https://drive.google.com/uc?export=download&id=176LkvMMo_Ca6e4_I9i5hN-AOPyteT3M7"},
        {"name": "Imagem 4", "thumbnail_url": "https://drive.google.com/thumbnail?id=16wPB7L6qQFd96blB5vuDnjbgne7x9AhL", "download_url": "https://drive.google.com/uc?export=download&id=16wPB7L6qQFd96blB5vuDnjbgne7x9AhL"},
        {"name": "Imagem 5", "thumbnail_url": "https://drive.google.com/thumbnail?id=16gTLY7Ig6WTagG0ilbVnpAaDEmf7WUaQ", "download_url": "https://drive.google.com/uc?export=download&id=16gTLY7Ig6WTagG0ilbVnpAaDEmf7WUaQ"},
        {"name": "Imagem 6", "thumbnail_url": "https://drive.google.com/thumbnail?id=16lDZO2FzzOfxBPVQ1ot0nNj-PiVIFT42", "download_url": "https://drive.google.com/uc?export=download&id=16lDZO2FzzOfxBPVQ1ot0nNj-PiVIFT42"},
        {"name": "Imagem 7", "thumbnail_url": "https://drive.google.com/thumbnail?id=16RSvRT0jPl9PIwgEzJWxS57Mp3OPJwW6", "download_url": "https://drive.google.com/uc?export=download&id=16RSvRT0jPl9PIwgEzJWxS57Mp3OPJwW6"},
        {"name": "Imagem 8", "thumbnail_url": "https://drive.google.com/thumbnail?id=16YIn8FcWHAcGS-H_FKP-b04BROwyyO4l", "download_url": "https://drive.google.com/uc?export=download&id=16YIn8FcWHAcGS-H_FKP-b04BROwyyO4l"},
        {"name": "Imagem 9", "thumbnail_url": "https://drive.google.com/thumbnail?id=16OAbINiyA50JFpiCDQRFECNT1N7tIGqH", "download_url": "https://drive.google.com/uc?export=download&id=16OAbINiyA50JFpiCDQRFECNT1N7tIGqH"},
        {"name": "Imagem 10", "thumbnail_url": "https://drive.google.com/thumbnail?id=169kVDn6au-iD9jg61mk0O96CitvTEPJM", "download_url": "https://drive.google.com/uc?export=download&id=169kVDn6au-iD9jg61mk0O96CitvTEPJM"},
        {"name": "Imagem 11", "thumbnail_url": "https://drive.google.com/thumbnail?id=16CK84F3LWT92iVoZhwaqobwnFdnt-eag", "download_url": "https://drive.google.com/uc?export=download&id=16CK84F3LWT92iVoZhwaqobwnFdnt-eag"},
        {"name": "Imagem 12", "thumbnail_url": "https://drive.google.com/thumbnail?id=163pywOk7kZk7w5-1QNtRlQWvPoj8bxyU", "download_url": "https://drive.google.com/uc?export=download&id=163pywOk7kZk7w5-1QNtRlQWvPoj8bxyU"},
        {"name": "Imagem 13", "thumbnail_url": "https://drive.google.com/thumbnail?id=167qtWNzJeZe13wcCyxsCNWvtVg_eOw5B", "download_url": "https://drive.google.com/uc?export=download&id=167qtWNzJeZe13wcCyxsCNWvtVg_eOw5B"},
        {"name": "Imagem 14", "thumbnail_url": "https://drive.google.com/thumbnail?id=168HGZAF5189eYaoNmNFgb0V9QwZy-CTB", "download_url": "https://drive.google.com/uc?export=download&id=168HGZAF5189eYaoNmNFgb0V9QwZy-CTB"},
        {"name": "Imagem 15", "thumbnail_url": "https://drive.google.com/thumbnail?id=15ngfDV7QxCLavL827A_kje_EU5KbgZJ8", "download_url": "https://drive.google.com/uc?export=download&id=15ngfDV7QxCLavL827A_kje_EU5KbgZJ8"},
        {"name": "Imagem 16", "thumbnail_url": "https://drive.google.com/thumbnail?id=15tl8U3X2C5tEVcIdwxgOnNxbZnSwdjPl", "download_url": "https://drive.google.com/uc?export=download&id=15tl8U3X2C5tEVcIdwxgOnNxbZnSwdjPl"},
        {"name": "Imagem 17", "thumbnail_url": "https://drive.google.com/thumbnail?id=163MdONKTA5Ghha0wIHg_8FBJc8XYUih8", "download_url": "https://drive.google.com/uc?export=download&id=163MdONKTA5Ghha0wIHg_8FBJc8XYUih8"},
        {"name": "Imagem 18", "thumbnail_url": "https://drive.google.com/thumbnail?id=15e1hdW0_a5FN2nv-vUQdowA4n1y0d1G7", "download_url": "https://drive.google.com/uc?export=download&id=15e1hdW0_a5FN2nv-vUQdowA4n1y0d1G7"},
        {"name": "Imagem 19", "thumbnail_url": "https://drive.google.com/thumbnail?id=15kFyBaLND7OkyGWNd81_yXusPScd0roB", "download_url": "https://drive.google.com/uc?export=download&id=15kFyBaLND7OkyGWNd81_yXusPScd0roB"},
        {"name": "Imagem 20", "thumbnail_url": "https://drive.google.com/thumbnail?id=15c7L4rHP3by4XuN6OSx6S_awsUY21ztB", "download_url": "https://drive.google.com/uc?export=download&id=15c7L4rHP3by4XuN6OSx6S_awsUY21ztB"},
        {"name": "Imagem 21", "thumbnail_url": "https://drive.google.com/thumbnail?id=15YEN0AlfR2EWJijPPqDt0zNo9JpIpcGx", "download_url": "https://drive.google.com/uc?export=download&id=15YEN0AlfR2EWJijPPqDt0zNo9JpIpcGx"},
        {"name": "Imagem 22", "thumbnail_url": "https://drive.google.com/thumbnail?id=15YLwx-_5BJb-DuYdA8stwO7sCeajvKgz", "download_url": "https://drive.google.com/uc?export=download&id=15YLwx-_5BJb-DuYdA8stwO7sCeajvKgz"},
        {"name": "Vídeo 01", "thumbnail_url": "https://drive.google.com/thumbnail?id=17CfFQtmntGfVDgaWuHKsuCtb-IPb5klT", "download_url": "https://drive.google.com/uc?export=download&id=17CfFQtmntGfVDgaWuHKsuCtb-IPb5klT"},
        {"name": "Vídeo 02", "thumbnail_url": "https://drive.google.com/thumbnail?id=16b72Zowj9O6ErWt2hzDIZITJPbrunMZ1", "download_url": "https://drive.google.com/uc?export=download&id=16b72Zowj9O6ErWt2hzDIZITJPbrunMZ1"}
    ]
    
    context = {
        'captador': captador,
        'total_vendas': total_vendas,
        'valor_total_indicacoes': valor_total_indicacoes,
        'comissao_total': comissao_total,
        'comissao_recebida': comissao_recebida,
        'comissao_a_receber': comissao_a_receber,
        'percentual_comissao': int(percentual_comissao * 100),
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
        'media_files': media_files,
        'hoje': hoje,
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

