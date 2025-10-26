from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import HttpResponse
from django.utils import timezone
from django.db.models import Q, Count
from decimal import Decimal
import locale
import os
from io import BytesIO
from datetime import datetime, timedelta
import requests

# ReportLab imports
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Flowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from num2words import num2words
from workalendar.america import Brazil

from .models import Contrato, DocumentoLegal
from vendas.models import Venda
from clientes.models import Cliente
from financeiro.models import Parcela


# Configuração de locale para formatação de datas
try:
    locale.setlocale(locale.LC_TIME, 'pt_BR.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_TIME, 'Portuguese_Brazil')
    except:
        pass


# ===============================================
# PERMISSÕES COMPARTILHADAS COM COMPLIANCE
# ===============================================
def is_compliance_or_juridico(user):
    """
    Permissão compartilhada: Compliance e Jurídico podem acessar contratos
    Integração implementada para unificar fluxo de pós-venda
    """
    if user.is_superuser:
        return True
    return user.groups.filter(
        name__in=['compliance', 'juridico', 'admin']
    ).exists()


class ImageLeft(Flowable):
    """Classe para posicionar imagens no PDF"""
    def __init__(self, path, width, height):
        Flowable.__init__(self)
        self.path = path
        self.width = width
        self.height = height

    def draw(self):
        self.canv.drawImage(self.path, 0, 0, width=self.width, height=self.height, mask='auto')


def add_watermark_and_border(canvas, doc):
    """Adiciona marca d'água, borda e rodapé ao PDF"""
    canvas.saveState()
    
    # Adicionar marca d'água
    try:
        watermark_url = 'https://drive.google.com/uc?export=download&id=1BkvbsJdH62fJGIwqwqB-F4cFt1AgfJ44'
        response = requests.get(watermark_url, timeout=10)
        if response.status_code == 200:
            watermark = ImageReader(BytesIO(response.content))
            img_width, img_height = watermark.getSize()
            aspect = img_height / float(img_width)
            width = 500
            height = width * aspect
            canvas.drawImage(
                watermark, 
                (A4[0] - width) / 2, 
                (A4[1] - height) / 2, 
                width=width, 
                height=height, 
                mask='auto'
            )
    except Exception as e:
        print(f"Erro ao carregar marca d'água: {str(e)}")
    
    # Adicionar borda
    canvas.setStrokeColor(colors.black)
    canvas.setLineWidth(1)
    canvas.rect(20, 20, A4[0] - 40, A4[1] - 40)
    
    # Adicionar rodapé
    footer_text = "Grupo MR Baruch - CNPJ: 31.406.396/0001-03 - Rua Jequirituba, 1666, sobreloja, Jardim Amália II, São Paulo – SP, CEP: 04822-000"
    canvas.setFont('Helvetica', 8)
    canvas.drawCentredString(A4[0]/2, 10, footer_text)
    
    canvas.restoreState()


@login_required
@user_passes_test(is_compliance_or_juridico)
def dashboard_juridico(request):
    """Dashboard principal do módulo jurídico"""
    # Estatísticas
    contratos_aguardando = Contrato.objects.filter(status='AGUARDANDO_GERACAO').count()
    contratos_gerados = Contrato.objects.filter(status='GERADO').count()
    contratos_assinados = Contrato.objects.filter(status='ASSINADO').count()
    total_contratos = Contrato.objects.count()
    
    # Contratos recentes aguardando geração
    contratos_pendentes = Contrato.objects.filter(
        status='AGUARDANDO_GERACAO'
    ).select_related('venda', 'cliente', 'cliente__lead').order_by('-data_criacao')[:10]
    
    # Contratos recentemente gerados
    contratos_recentes = Contrato.objects.filter(
        status__in=['GERADO', 'ENVIADO', 'ASSINADO']
    ).select_related('venda', 'cliente', 'cliente__lead').order_by('-data_atualizacao')[:10]
    
    context = {
        'contratos_aguardando': contratos_aguardando,
        'contratos_gerados': contratos_gerados,
        'contratos_assinados': contratos_assinados,
        'total_contratos': total_contratos,
        'contratos_pendentes': contratos_pendentes,
        'contratos_recentes': contratos_recentes,
    }
    
    return render(request, 'juridico/dashboard.html', context)


@login_required
@user_passes_test(is_compliance_or_juridico)
def lista_contratos(request):
    """Lista todos os contratos com filtros"""
    status_filtro = request.GET.get('status', '')
    busca = request.GET.get('busca', '')
    
    contratos = Contrato.objects.all().select_related('venda', 'cliente', 'cliente__lead', 'usuario_geracao')
    
    if status_filtro:
        contratos = contratos.filter(status=status_filtro)
    
    if busca:
        contratos = contratos.filter(
            Q(numero_contrato__icontains=busca) |
            Q(cliente__lead__nome_completo__icontains=busca) |
            Q(cliente__lead__cpf__icontains=busca)
        )
    
    contratos = contratos.order_by('-data_criacao')
    
    context = {
        'contratos': contratos,
        'status_filtro': status_filtro,
        'busca': busca,
        'status_choices': Contrato.STATUS_CHOICES,
    }
    
    return render(request, 'juridico/lista_contratos.html', context)


@login_required
@user_passes_test(is_compliance_or_juridico)
def detalhes_contrato(request, contrato_id):
    """Exibe detalhes de um contrato específico"""
    contrato = get_object_or_404(
        Contrato.objects.select_related('venda', 'cliente', 'cliente__lead', 'usuario_geracao'),
        id=contrato_id
    )
    
    documentos = contrato.documentos.all().order_by('-data_upload')
    parcelas = Parcela.objects.filter(venda=contrato.venda).order_by('numero_parcela')
    
    # Calcular status dos boletos ASAAS
    total_parcelas = parcelas.count()
    parcelas_enviadas = parcelas.filter(enviado_asaas=True).count()
    parcelas_pendentes = total_parcelas - parcelas_enviadas
    
    # Verifica se TODOS os boletos foram enviados ao ASAAS
    todos_boletos_enviados = (total_parcelas > 0 and parcelas_pendentes == 0)
    
    # Verifica se existe pelo menos uma parcela sem id_asaas (boleto não gerado)
    # Verifica tanto NULL quanto string vazia
    tem_parcelas_sem_boleto = parcelas.filter(
        Q(id_asaas__isnull=True) | Q(id_asaas='') | Q(id_asaas='None')
    ).exists()
    
    context = {
        'contrato': contrato,
        'documentos': documentos,
        'parcelas': parcelas,
        'total_parcelas': total_parcelas,
        'parcelas_enviadas': parcelas_enviadas,
        'parcelas_pendentes': parcelas_pendentes,
        'todos_boletos_enviados': todos_boletos_enviados,
        'tem_parcelas_sem_boleto': tem_parcelas_sem_boleto,
    }
    
    return render(request, 'juridico/detalhes_contrato.html', context)


@login_required
@user_passes_test(is_compliance_or_juridico)
def gerar_contrato(request, venda_id):
    """Gera PDF do contrato para uma venda específica"""
    print("[DEBUG] entrar em gerar_contrato", "venda_id=", venda_id, "method=", request.method, "user=", getattr(request.user, 'username', None))
    try:
        venda = get_object_or_404(Venda.objects.select_related('cliente', 'cliente__lead', 'servico'), id=venda_id)
        cliente = venda.cliente
        lead = cliente.lead
        
        # Verificar se já existe contrato para esta venda
        contrato, created = Contrato.objects.get_or_create(
            venda=venda,
            cliente=cliente,
            defaults={'usuario_geracao': request.user}
        )
        
        if created or not contrato.arquivo_contrato:
            # Gerar número do contrato se ainda não existe
            if not contrato.numero_contrato:
                contrato.gerar_numero_contrato()
            
            # Atualizar status
            contrato.status = 'GERADO'
            contrato.data_geracao = timezone.now()
            contrato.usuario_geracao = request.user
            contrato.save()
        
        # Buscar parcelas
        parcelas = Parcela.objects.filter(venda=venda).order_by('numero_parcela')
        
        # Build PDF in-memory so we can both save it and stream it
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        # Estilos
        styles = getSampleStyleSheet()
        story = []
        
        # Estilos personalizados
        title_style = ParagraphStyle(
            name='Title',
            fontSize=16,
            leading=20,
            alignment=1,
            spaceAfter=16,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#00205B'),
        )
        
        heading_style = ParagraphStyle(
            name='Heading2',
            fontSize=12,
            leading=15,
            spaceAfter=12,
            spaceBefore=12,
            fontName='Helvetica-Bold',
            textColor=colors.HexColor('#00205B'),
        )
        
        normal_style = ParagraphStyle(
            name='Normal',
            fontSize=10,
            leading=14,
            spaceBefore=3,
            spaceAfter=8,
            fontName='Helvetica',
            leftIndent=10,
            rightIndent=10,
            alignment=4,
        )
        
        paragrafos_com_indentacao = ParagraphStyle(
            name='IndentedParagraph',
            fontSize=10,
            leading=14,
            spaceBefore=3,
            spaceAfter=6,
            fontName='Helvetica',
            leftIndent=30,
            rightIndent=10,
            alignment=4,
        )
        
        # Funções auxiliares
        def format_currency(value):
            if value is None:
                return "R$ 0,00"
            return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        
        # Prefer using Lead.get_cpf_cnpj_display() to format CPF/CNPJ centrally
        
        # Cálculo de dias úteis
        cal = Brazil()
        data_venda = venda.data_venda
        dias_uteis = venda.dias_para_conclusao or 180
        
        # Cabeçalho do contrato
        if hasattr(lead, 'get_cpf_cnpj_display'):
            cpf_cnpj = lead.get_cpf_cnpj_display()
        else:
            cpf_cnpj = getattr(lead, 'cpf_cnpj', '') or 'Não Informado'
        
        story.append(Paragraph("CONTRATO DE PRESTAÇÃO DE SERVIÇOS", title_style))
        story.append(Paragraph(f"<b>Número:</b> {contrato.numero_contrato}", normal_style))
        story.append(Spacer(1, 0.2 * inch))
        
        # Campos opcionais com fallback seguro
        lead_nacionalidade = getattr(lead, 'nacionalidade', '') or 'brasileiro(a)'
        # cliente pode ter método get_estado_civil_display (se o campo existir)
        if hasattr(cliente, 'get_estado_civil_display'):
            cliente_estado_civil = cliente.get_estado_civil_display() or 'não informado'
        else:
            cliente_estado_civil = getattr(cliente, 'estado_civil', '') or 'não informado'
        cliente_profissao = getattr(cliente, 'profissao', '') or 'não informado'
        cliente_rg = getattr(cliente, 'rg', '') or 'Não Informado'
        cliente_rua = getattr(cliente, 'rua', '') or ''
        cliente_numero = getattr(cliente, 'numero', '') or ''
        cliente_bairro = getattr(cliente, 'bairro', '') or ''
        cliente_cidade = getattr(cliente, 'cidade', '') or ''
        cliente_estado = getattr(cliente, 'estado', '') or ''
        cliente_cep = getattr(cliente, 'cep', '') or ''

        story.append(Paragraph(
            f"<b>CONTRATANTE: {getattr(lead, 'nome_completo', '')}</b>, {lead_nacionalidade}, "
            f"{cliente_estado_civil}, {cliente_profissao}, portador do RG: {cliente_rg}, "
            f"inscrito no CPF/CNPJ: {cpf_cnpj}, residente e domiciliado(a) na {cliente_rua}, {cliente_numero}, "
            f"{cliente_bairro}, {cliente_cidade} - {cliente_estado}, CEP: {cliente_cep},<br/><br/>"
            f"<b>CONTRATADO: GRUPO MR BARUCH</b>, pessoa jurídica de direito privado, inscrita no CNPJ sob o nº 31.406.396/0001-03, "
            f"com sede na Rua Jequirituba, nº 1.666, sobreloja, Jardim Amália II, São Paulo - SP, CEP 04822-000.<br/>",
            normal_style
        ))
        
        # CLÁUSULA 1ª – DO OBJETO
        story.append(Paragraph("CLÁUSULA 1ª – DO OBJETO", heading_style))
        
        servicos_texto = []
        if venda.limpa_nome:
            servicos_texto.append("• <b>Exclusão de apontamentos</b> nos órgãos de proteção ao crédito (SERASA, SPC, Boa Vista e CEMPROT);")
            servicos_texto.append("• <b>Garantia mínima de 06 (seis) meses</b> contra reincidência de registros, a contar da data de baixa;")
        
        if venda.retirada_travas:
            servicos_texto.append("• <b>Retirada de travas</b> (Atualização nos órgãos de proteção ao crédito);")
        
        if venda.recuperacao_score:
            servicos_texto.append("• <b>Restauração do Score</b> (observada a possível variação conforme critérios técnicos dos órgãos de proteção ao crédito);")
        
        servicos_texto.append(f"• <b>Entrega do resultado</b> em até <b>{dias_uteis} dias úteis</b>, a partir da assinatura do contrato e do pagamento da entrada.")
        
        story.append(Paragraph(
            f"1.1. O presente contrato tem por objeto a prestação de serviços especializados pelo <b>CONTRATADO</b> ao <b>CONTRATANTE</b>, visando:<br/><br/>" +
            "<br/><br/>".join(servicos_texto) + "<br/><br/>",
            paragrafos_com_indentacao
        ))
        
        story.append(Paragraph(
            f"1.2. <b>Não se inclui no escopo:</b><br/><br/>"
            f"• Negociação ou pagamento de débitos;<br/><br/>"
            f"• Exclusão de restrições internas de bancos ou do Banco Central.<br/><br/>",
            paragrafos_com_indentacao
        ))
        
        # CLÁUSULA 2ª – DAS OBRIGAÇÕES DO CONTRATADO
        story.append(Paragraph("CLÁUSULA 2ª – DAS OBRIGAÇÕES DO CONTRATADO", heading_style))
        story.append(Paragraph(
            f"2.1. O CONTRATADO obriga-se a:<br/><br/>"
            f"• Realizar a <b>exclusão das restrições</b> em até <b>{dias_uteis} dias úteis</b> após assinatura e pagamento da entrada;<br/><br/>"
            f"• Reexcluir, sem custos, quaisquer registros que retornem durante o período de garantia;<br/><br/>"
            f"• Zelar pela <b>confidencialidade dos dados</b>, em conformidade com a <b>LGPD (Lei 13.709/2018)</b>.<br/><br/>",
            paragrafos_com_indentacao
        ))
        
        # CLÁUSULA 3ª – DAS OBRIGAÇÕES DO CONTRATANTE
        story.append(Paragraph("CLÁUSULA 3ª – DAS OBRIGAÇÕES DO CONTRATANTE", heading_style))
        story.append(Paragraph(
            f"3.1. O CONTRATANTE deverá:<br/><br/>"
            f"• Pagar o valor total de {format_currency(venda.valor_total)} conforme:<br/>",
            paragrafos_com_indentacao
        ))
        
        story.append(Spacer(1, 0.2 * inch))
        
        # Tabela de pagamentos
        data = [["Valor", "Valor por Extenso", "Vencimento"]]
        
        # Adicionar entrada se for PIX ou dinheiro
        if venda.forma_entrada in ["PIX", "DINHEIRO"] and venda.valor_entrada > 0:
            valor_entrada_extenso = num2words(float(venda.valor_entrada), lang='pt_BR', to='currency').upper()
            data.append([
                format_currency(venda.valor_entrada),
                Paragraph(valor_entrada_extenso, normal_style),
                "Valor de Entrada"
            ])
        
        # Adicionar parcelas
        for parcela in parcelas:
            valor_extenso = num2words(float(parcela.valor), lang='pt_BR', to='currency').upper()
            data.append([
                format_currency(parcela.valor),
                Paragraph(valor_extenso, normal_style),
                parcela.data_vencimento.strftime('%d/%m/%Y') if parcela.data_vencimento else 'A definir'
            ])
        
        # Criar tabela
        table = Table(data, colWidths=[doc.width * 0.2, doc.width * 0.6, doc.width * 0.2])
        table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 4),
            ('TOPPADDING', (0, 0), (-1, 0), 4),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F8F9FA')),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#333333')),
            ('ALIGN', (0, 1), (0, -1), 'CENTER'),
            ('ALIGN', (2, 1), (2, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.HexColor('#CCCCCC')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#2C3E50')),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 1), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 2),
        ])
        
        table.setStyle(table_style)
        story.append(table)
        story.append(Spacer(1, 0.2 * inch))
        
        story.append(Paragraph(
            "• Fornecer <b>documentação completa</b> (RG, CPF, comprovantes);<br/><br/>"
            "• Assinar <b>requerimento específico</b> para a execução dos trabalhos;<br/><br/>"
            "• <b>Abster-se de solicitar crédito</b> durante a execução do serviço.<br/><br/>",
            paragrafos_com_indentacao
        ))
        
        story.append(Paragraph(
            "3.2. <b>Penalidades por inadimplemento:</b><br/><br/>"
            "• Multa de <b>10%</b> sobre o valor das parcelas em atraso, mais <b>1%</b> ao mês de mora e correção monetária.<br/><br/>",
            paragrafos_com_indentacao
        ))
        
        # CLÁUSULA 4ª – DO TÍTULO EXECUTIVO EXTRAJUDICIAL
        story.append(Paragraph("CLÁUSULA 4ª – DO TÍTULO EXECUTIVO EXTRAJUDICIAL", heading_style))
        story.append(Paragraph(
            "4.1. <b>As partes reconhecem</b> que este instrumento constitui <b>título executivo extrajudicial</b>, "
            "nos termos do Art. 784, III, do CPC, dispensando notificação prévia para execução.<br/><br/>",
            normal_style
        ))
        
        # CLÁUSULA 5ª – DA RESCISÃO E MULTAS
        story.append(Paragraph("CLÁUSULA 5ª – DA RESCISÃO E MULTAS", heading_style))
        story.append(Paragraph(
            "<b>5.1. Em caso de desistência:</b><br/><br/>"
            "• Não haverá devolução dos valores já pagos pelo CONTRATANTE por motivos o qual deu causa, "
            "em razão dos custos operacionais e administrativos já incorridos.<br/><br/>"
            "5.2. Em caso de rescisão contratual por inadimplemento ou por qualquer outra motivação por parte do CONTRATANTE, "
            "será devida multa rescisória correspondente a 25% (vinte e cinco por cento) sobre o valor total do contrato.<br/><br/>",
            paragrafos_com_indentacao
        ))
        
        # CLÁUSULA 6ª – DO FORO E LEGISLAÇÃO APLICÁVEL
        story.append(Paragraph("CLÁUSULA 6ª – DO FORO E LEGISLAÇÃO APLICÁVEL", heading_style))
        story.append(Paragraph(
            "6.1. Fica eleito o <b>foro da Comarca de São Paulo/SP</b> para dirimir eventuais litígios, "
            "renunciando-se a qualquer outro por mais privilégio que o tenha.<br/><br/>",
            normal_style
        ))
        
        story.append(PageBreak())
        
        # TERMO DE CIÊNCIA E ACEITAÇÃO
        story.append(Paragraph("TERMO DE CIÊNCIA E ACEITAÇÃO", heading_style))
        story.append(Paragraph(
            "Ao assinar este contrato, o Contratante declara estar ciente e de acordo com todas as cláusulas e condições aqui estabelecidas, "
            "bem como reconhece que este contrato é <b>título executivo extrajudicial.</b><br/><br/>",
            normal_style
        ))
        
        # Local e data
        data_formatada = timezone.now().strftime("%d de %B de %Y")
        story.append(Paragraph(f"<b>São Paulo, {data_formatada}.</b>", normal_style))
        story.append(Spacer(1, 0.5 * inch))
        
        # Assinaturas
        col1_data = [
            Paragraph("<b>CONTRATANTE:</b>", normal_style),
            Spacer(1, 0.5 * inch),
            Spacer(1, 0.5 * inch),
            Paragraph("________________________________________________________", normal_style),
            Paragraph(lead.nome_completo, normal_style),
            Paragraph(f"CPF/CNPJ: {cpf_cnpj}", normal_style),
        ]
        
        col2_data = [
            Paragraph("<b>CONTRATADO:</b>", normal_style),
            Spacer(1, 1 * inch),
            Paragraph("________________________________________________________", normal_style),
            Paragraph("Grupo MR Baruch", normal_style),
            Paragraph("CNPJ: 31.406.396/0001-03", normal_style),
        ]
        
        assinatura_table = Table([[col1_data, col2_data]], colWidths=[doc.width/2-15, doc.width/2-15])
        assinatura_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        
        story.append(assinatura_table)
        
        # Construir PDF
        # Construir PDF (escreve em pdf_buffer)
        doc.build(story, onFirstPage=add_watermark_and_border, onLaterPages=add_watermark_and_border)

        # Recuperar bytes do PDF
        pdf_buffer.seek(0)
        pdf_bytes = pdf_buffer.getvalue()

        # Salvar no FileField do contrato (arquivo_contrato)
        try:
            from django.core.files.base import ContentFile
            # Filename seguro
            safe_name = f"Contrato_{contrato.numero_contrato}_{lead.nome_completo}.pdf"
            # Salva apenas se não existir arquivo ou se quisermos sobrescrever
            if not contrato.arquivo_contrato:
                contrato.arquivo_contrato.save(safe_name, ContentFile(pdf_bytes))
                contrato.save(update_fields=['arquivo_contrato', 'data_geracao', 'status', 'usuario_geracao'])
            else:
                # Atualizar metadados caso já exista (não sobrescrever arquivo existente por enquanto)
                contrato.data_geracao = contrato.data_geracao or timezone.now()
                contrato.status = contrato.status or 'GERADO'
                contrato.save(update_fields=['data_geracao', 'status'])
        except Exception as e:
            # Não falhar o streaming por conta de problema ao salvar o arquivo; apenas logar
            print(f"Falha ao salvar arquivo do contrato: {e}")

        # Preparar resposta HTTP para streaming do PDF gerado
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        inline = request.GET.get('inline') == '1'
        disposition = 'inline' if inline else 'attachment'
        response['Content-Disposition'] = f'{disposition}; filename="Contrato_{contrato.numero_contrato}_{lead.nome_completo}.pdf"'

        messages.success(request, f'Contrato {contrato.numero_contrato} gerado com sucesso!')
        return response
        
    except Exception as e:
        # Log full traceback for debugging
        import traceback
        tb = traceback.format_exc()
        print(f"Erro ao gerar contrato: {str(e)}")
        print(tb)
        # Show error details in response (temporary for debugging)
        return HttpResponse(f"Erro ao gerar contrato: {str(e)}\n\n{tb}", status=500, content_type='text/plain')


@login_required
@user_passes_test(is_compliance_or_juridico)
def atualizar_status_contrato(request, contrato_id):
    """
    Atualiza o status de um contrato.
    Quando marcado como ASSINADO, envia parcelas ao ASAAS automaticamente.
    """
    if request.method == 'POST':
        contrato = get_object_or_404(Contrato, id=contrato_id)
        novo_status = request.POST.get('status')
        
        if novo_status in dict(Contrato.STATUS_CHOICES):
            status_anterior = contrato.status
            contrato.status = novo_status
            
            # Atualizar datas conforme status
            if novo_status == 'ASSINADO' and not contrato.data_assinatura:
                contrato.data_assinatura = timezone.now()
                
                # 🔥 TRIGGER: Enviar parcelas ao ASAAS
                try:
                    resultado = enviar_parcelas_asaas(contrato.venda)
                    if resultado['sucesso']:
                        messages.success(
                            request, 
                            f'✅ Contrato assinado! {resultado["total_enviadas"]} parcelas enviadas ao ASAAS com sucesso.'
                        )
                    else:
                        messages.warning(
                            request,
                            f'⚠️ Contrato assinado, mas houve erro ao enviar {resultado["total_erros"]} parcela(s) ao ASAAS.'
                        )
                except Exception as e:
                    messages.error(request, f'❌ Erro ao enviar parcelas ao ASAAS: {str(e)}')
                
            elif novo_status == 'ENVIADO' and not contrato.data_envio:
                contrato.data_envio = timezone.now()
            
            contrato.save()
            
            if novo_status != 'ASSINADO':
                messages.success(request, f'Status do contrato atualizado para {contrato.get_status_display()}')
        else:
            messages.error(request, 'Status inválido')
    
    return redirect('juridico:detalhes_contrato', contrato_id=contrato_id)


def enviar_parcelas_asaas(venda):
    """
    Envia todas as parcelas pendentes de uma venda para o ASAAS.
    Retorna dict com estatísticas do envio.
    """
    from core.asaas_service import AsaasService
    from core.services import LogService
    
    print(f"\n=== INICIANDO ENVIO DE PARCELAS PARA ASAAS ===")
    print(f"Venda ID: {venda.id}")
    
    asaas = AsaasService()
    resultado = {
        'sucesso': True,
        'total_enviadas': 0,
        'total_erros': 0,
        'erros': []
    }
    
    # Buscar parcelas que ainda não foram enviadas ao ASAAS (verificando id_asaas)
    parcelas_pendentes = Parcela.objects.filter(
        venda=venda
    ).filter(
        Q(id_asaas__isnull=True) | Q(id_asaas='') | Q(id_asaas='None')
    ).order_by('numero_parcela')
    
    print(f"Parcelas pendentes encontradas: {parcelas_pendentes.count()}")
    
    if not parcelas_pendentes.exists():
        resultado['mensagem'] = 'Nenhuma parcela pendente para enviar'
        print("❌ Nenhuma parcela pendente!")
        return resultado
    
    # Buscar/criar cliente no ASAAS
    try:
        cliente = venda.cliente
        lead = cliente.lead
        
        print(f"\n  Criando/Buscando cliente no ASAAS...")
        print(f"  - Nome: {lead.nome_completo}")
        print(f"  - CPF/CNPJ: {getattr(lead, 'cpf_cnpj', None) or 'Não informado'}")
        print(f"  - Email: {lead.email}")
        print(f"  - Telefone: {lead.telefone}")
        
        asaas_customer = asaas.criar_cliente({
            'nome': lead.nome_completo,
            'cpf_cnpj': getattr(lead, 'cpf_cnpj', None) or '',
            'email': lead.email,
            'telefone': lead.telefone,
            'cep': cliente.cep or '',
            'endereco': cliente.rua or '',
            'numero': cliente.numero or '',
            'bairro': cliente.bairro or '',
            'id_cliente': str(cliente.id),
        })
        
        customer_id = asaas_customer.get('id')
        print(f"  ✅ Cliente ASAAS criado/encontrado: {customer_id}")
        
        if not customer_id:
            raise Exception("ASAAS não retornou ID do cliente")
        
    except Exception as e:
        resultado['sucesso'] = False
        resultado['erros'].append(f'Erro ao criar/buscar cliente no ASAAS: {str(e)}')
        try:
            LogService.log_error(
                'ASAAS_ERRO_CLIENTE',
                f'Erro ao criar cliente no ASAAS para venda #{venda.id}: {str(e)}'
            )
        except:
            pass
        return resultado
    
    # Enviar cada parcela
    for parcela in parcelas_pendentes:
        try:
            print(f"\n  Enviando parcela {parcela.numero_parcela}...")
            print(f"  - Valor: R$ {parcela.valor}")
            print(f"  - Vencimento: {parcela.data_vencimento}")
            
            cobranca = asaas.criar_cobranca({
                'customer_id': customer_id,  # Corrigido: era 'customer', deve ser 'customer_id'
                'billing_type': venda.forma_pagamento,  # Corrigido: era 'billingType'
                'value': float(parcela.valor),
                'due_date': parcela.data_vencimento.isoformat(),  # Corrigido: era 'dueDate'
                'description': f'Parcela {parcela.numero_parcela}/{parcelas_pendentes.count()} - Venda #{venda.id} - {venda.servico.nome}',
                'external_reference': f'venda_{venda.id}_parcela_{parcela.numero_parcela}',  # Corrigido: era 'externalReference'
            })
            
            print(f"  ✅ Cobrança criada no ASAAS: {cobranca.get('id', '')}")
            
            # Atualizar parcela com dados do ASAAS
            parcela.id_asaas = cobranca.get('id', '')
            parcela.url_boleto = cobranca.get('bankSlipUrl', '')
            parcela.codigo_barras = cobranca.get('identificationField', '')
            parcela.enviado_asaas = True
            parcela.data_envio_asaas = timezone.now()
            parcela.status = 'aberta'  # Garantir que status seja 'aberta' (pendente)
            parcela.save()
            
            resultado['total_enviadas'] += 1
            
            # Log de sucesso
            try:
                LogService.log_info(
                    'PARCELA_ENVIADA_ASAAS',
                    f'Parcela {parcela.numero_parcela} da venda #{venda.id} enviada ao ASAAS (ID: {parcela.id_asaas})'
                )
            except:
                pass
            
        except Exception as e:
            resultado['sucesso'] = False
            resultado['total_erros'] += 1
            erro_msg = f'Parcela {parcela.numero_parcela}: {str(e)}'
            resultado['erros'].append(erro_msg)
            
            # Log de erro
            try:
                LogService.log_error(
                    'ASAAS_ERRO_PARCELA',
                    f'Erro ao enviar parcela {parcela.numero_parcela} da venda #{venda.id} ao ASAAS: {str(e)}'
                )
            except:
                pass
    
    # Ajustar o retorno para ser compatível
    resultado['sucesso'] = resultado['total_enviadas']
    return resultado


@login_required
@user_passes_test(is_compliance_or_juridico)
def painel_contratos_enviados(request):
    """Painel para acompanhar contratos enviados aguardando assinatura"""
    contratos_enviados = Contrato.objects.filter(
        status='ENVIADO'
    ).select_related('venda', 'cliente', 'cliente__lead').order_by('data_envio')
    
    # Adicionar informações de tempo para cada contrato
    for contrato in contratos_enviados:
        contrato.dias_cliente = contrato.dias_com_cliente
    
    context = {
        'contratos_enviados': contratos_enviados,
    }
    
    return render(request, 'juridico/painel_contratos_enviados.html', context)


@login_required
@user_passes_test(is_compliance_or_juridico)
def marcar_contrato_enviado(request, contrato_id):
    """
    Marca contrato como ENVIADO ao cliente
    Consultor usa essa ação após baixar o contrato e enviar para o cliente
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    if request.method == 'POST':
        observacao = request.POST.get('observacao', '')
        meio_envio = request.POST.get('meio_envio', 'outro')
        
        # Construir observação completa
        obs_completa = f"Enviado via {meio_envio}"
        if observacao:
            obs_completa += f" - {observacao}"
        
        # Mudar status para ENVIADO
        contrato.mudar_status('ENVIADO', request.user, obs_completa)
        
        messages.success(request, f'Contrato {contrato.numero_contrato} marcado como ENVIADO ao cliente!')
        
        # Log
        from core.services import LogService
        LogService.registrar(
            nivel='INFO',
            mensagem=f'Contrato {contrato.numero_contrato} marcado como enviado por {request.user.get_full_name()} via {meio_envio}',
            modulo='juridico',
            acao='contrato_marcado_enviado',
            usuario=request.user
        )
        
        # REDIRECT INTELIGENTE: Volta para Compliance se veio de lá
        referer = request.META.get('HTTP_REFERER', '')
        if 'compliance' in referer:
            return redirect('compliance:gestao_pos_venda', venda_id=contrato.venda.id)
        
        return redirect('juridico:detalhes_contrato', contrato_id=contrato.id)
    
    context = {
        'contrato': contrato,
    }
    
    return render(request, 'juridico/marcar_enviado.html', context)


@login_required
@user_passes_test(is_compliance_or_juridico)
def marcar_contrato_assinado(request, contrato_id):
    """
    Marca contrato como ASSINADO pelo cliente
    Consultor usa essa ação após cliente devolver o contrato assinado
    Ao assinar, envia automaticamente todas as parcelas para o ASAAS
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    if request.method == 'POST':
        observacao = request.POST.get('observacao', '')
        arquivo_assinado = request.FILES.get('arquivo_assinado')
        tipo_assinatura = request.POST.get('tipo_assinatura', 'MANUAL')
        data_assinatura = request.POST.get('data_assinatura')
        
        # Upload do arquivo assinado (opcional agora)
        if arquivo_assinado:
            contrato.arquivo_assinado = arquivo_assinado
            contrato.save(update_fields=['arquivo_assinado'])
        
        # Atualizar flags de assinatura
        if tipo_assinatura == 'gov':
            contrato.assinatura_gov = True
            contrato.assinatura_manual = False
        else:
            contrato.assinatura_manual = True
            contrato.assinatura_gov = False
        
        # Atualizar data de assinatura se fornecida
        if data_assinatura:
            from datetime import datetime
            try:
                contrato.data_assinatura = datetime.strptime(data_assinatura, '%Y-%m-%d')
            except ValueError:
                pass
        
        contrato.save(update_fields=['assinatura_gov', 'assinatura_manual', 'data_assinatura'])
        
        # ===== ENVIAR PARCELAS AO ASAAS PRIMEIRO (ANTES DE MARCAR COMO ASSINADO) =====
        venda = contrato.venda
        resultado_parcelas = enviar_parcelas_asaas(venda)
        
        # Verificar se TODAS as parcelas foram enviadas com sucesso
        from financeiro.models import Parcela
        total_parcelas = Parcela.objects.filter(venda=venda).count()
        parcelas_enviadas = Parcela.objects.filter(venda=venda, enviado_asaas=True).count()
        
        print(f"\n=== VALIDAÇÃO DE BOLETOS ===")
        print(f"Total de parcelas: {total_parcelas}")
        print(f"Parcelas enviadas ao ASAAS: {parcelas_enviadas}")
        print(f"Resultado envio - Sucesso: {resultado_parcelas.get('total_enviadas', 0)}")
        print(f"Resultado envio - Erros: {resultado_parcelas.get('total_erros', 0)}")
        
        # SE TODAS AS PARCELAS FORAM ENVIADAS COM SUCESSO → Marcar como ASSINADO
        if parcelas_enviadas == total_parcelas and total_parcelas > 0:
            # Construir observação
            tipo_desc = 'Gov.br' if tipo_assinatura == 'gov' else 'Manual'
            obs_completa = f"Contrato assinado - Tipo: {tipo_desc}"
            if observacao:
                obs_completa += f" - {observacao}"
            
            # Mudar status para ASSINADO
            contrato.mudar_status('ASSINADO', request.user, obs_completa)
            
            messages.success(
                request, 
                f'✅ Contrato {contrato.numero_contrato} marcado como ASSINADO! Todos os {total_parcelas} boletos foram gerados no ASAAS com sucesso.'
            )
            
            # Log
            from core.services import LogService
            LogService.registrar(
                nivel='INFO',
                mensagem=f'Contrato {contrato.numero_contrato} marcado como assinado ({tipo_desc}) por {request.user.get_full_name()} - {total_parcelas} boletos gerados',
                modulo='juridico',
                acao='contrato_marcado_assinado',
                usuario=request.user
            )
            
            # Atualizar status da venda
            venda.status = 'EM_ANDAMENTO'
            venda.save(update_fields=['status'])
            
        # SE HOUVE FALHA NO ENVIO → NÃO marca como assinado e mostra erro
        else:
            falhas = total_parcelas - parcelas_enviadas
            
            messages.error(
                request,
                f'❌ FALHA ao gerar boletos no ASAAS! {parcelas_enviadas}/{total_parcelas} boletos criados. '
                f'{falhas} boleto(s) com erro. O contrato NÃO foi marcado como assinado.'
            )
            
            # Mostrar detalhes dos erros
            if resultado_parcelas.get('erros'):
                for erro in resultado_parcelas['erros'][:5]:  # Mostra até 5 erros
                    messages.warning(request, f'⚠️ {erro}')
            
            # Log de falha
            from core.services import LogService
            LogService.registrar(
                nivel='ERROR',
                mensagem=f'FALHA ao enviar boletos para ASAAS - Contrato {contrato.numero_contrato} - {parcelas_enviadas}/{total_parcelas} enviados',
                modulo='juridico',
                acao='erro_envio_boletos_asaas',
                usuario=request.user
            )
        
        # REDIRECT INTELIGENTE: Volta para Compliance se veio de lá
        referer = request.META.get('HTTP_REFERER', '')
        if 'compliance' in referer:
            return redirect('compliance:gestao_pos_venda', venda_id=contrato.venda.id)
        
        return redirect('juridico:detalhes_contrato', contrato_id=contrato.id)
    
    context = {
        'contrato': contrato,
    }
    
    return render(request, 'juridico/marcar_assinado.html', context)


@login_required
@user_passes_test(is_compliance_or_juridico)
def reenviar_boletos_asaas(request, contrato_id):
    """
    Tenta reenviar boletos que falharam no ASAAS
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)
    venda = contrato.venda
    
    from financeiro.models import Parcela
    
    # Verificar quantas parcelas faltam enviar (verificando id_asaas ao invés de enviado_asaas)
    total_parcelas = Parcela.objects.filter(venda=venda).count()
    parcelas_pendentes = Parcela.objects.filter(
        venda=venda
    ).filter(
        Q(id_asaas__isnull=True) | Q(id_asaas='') | Q(id_asaas='None')
    ).count()
    
    if parcelas_pendentes == 0:
        messages.info(request, f'✅ Todos os {total_parcelas} boletos já foram enviados ao ASAAS.')
        return redirect('juridico:detalhes_contrato', contrato_id=contrato.id)
    
    messages.info(request, f'🔄 Tentando gerar {parcelas_pendentes} boleto(s) no ASAAS...')
    
    # Reenviar parcelas pendentes
    resultado = enviar_parcelas_asaas(venda)
    
    # Verificar resultado (verificando id_asaas)
    parcelas_enviadas_agora = Parcela.objects.filter(venda=venda).exclude(
        Q(id_asaas__isnull=True) | Q(id_asaas='') | Q(id_asaas='None')
    ).count()
    
    if parcelas_enviadas_agora == total_parcelas:
        messages.success(
            request,
            f'✅ SUCESSO! Todos os {total_parcelas} boletos foram gerados no ASAAS.'
        )
        
        # Log
        from core.services import LogService
        LogService.registrar(
            nivel='INFO',
            mensagem=f'Geração de boletos bem-sucedida - Contrato {contrato.numero_contrato} - {total_parcelas} boletos',
            modulo='juridico',
            acao='geracao_boletos_sucesso',
            usuario=request.user
        )
    else:
        falhas = total_parcelas - parcelas_enviadas_agora
        messages.error(
            request,
            f'⚠️ Ainda há {falhas} boleto(s) com erro. {parcelas_enviadas_agora}/{total_parcelas} gerados.'
        )
        
        if resultado.get('erros'):
            for erro in resultado['erros'][:3]:
                messages.warning(request, f'❌ {erro}')
    
    # REDIRECT INTELIGENTE
    referer = request.META.get('HTTP_REFERER', '')
    if 'compliance' in referer:
        return redirect('compliance:gestao_pos_venda', venda_id=venda.id)
    
    return redirect('juridico:detalhes_contrato', contrato_id=contrato.id)


@login_required
@user_passes_test(is_compliance_or_juridico)
def download_contrato(request, contrato_id):
    """
    Faz download do PDF do contrato salvo
    """
    contrato = get_object_or_404(Contrato, id=contrato_id)
    
    if not contrato.arquivo_contrato:
        messages.error(request, 'Contrato não possui arquivo PDF gerado.')
        return redirect('juridico:detalhes_contrato', contrato_id=contrato.id)
    
    try:
        # Abrir o arquivo
        arquivo = contrato.arquivo_contrato.open('rb')
        response = HttpResponse(arquivo.read(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Contrato_{contrato.numero_contrato}.pdf"'
        arquivo.close()
        return response
    except Exception as e:
        messages.error(request, f'Erro ao baixar contrato: {str(e)}')
        return redirect('juridico:detalhes_contrato', contrato_id=contrato.id)
