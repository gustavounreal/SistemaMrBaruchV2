"""
Sistema Profissional de Comissões - Mr. Baruch
================================================

Este serviço centraliza TODA a lógica de cálculo de comissões do sistema.

REGRAS DE NEGÓCIO (Outubro 2025):
=================================

1. ATENDENTE (Levantamento PIX):
   - Valor fixo: R$ 0,50 por levantamento com pagamento PIX confirmado
   - Gerado automaticamente via webhook ASAAS

2. CAPTADOR (Vendas):
   - Fixo: 3% sobre valor recebido (Entrada + Boletos pagos)
   - Cálculo progressivo conforme parcelas são pagas

3. CONSULTOR (Vendas - Escala Progressiva por Faturamento):
   - Faturamento >= R$ 20.000 = 2%
   - Faturamento >= R$ 30.000 = 3%
   - Faturamento >= R$ 40.000 = 4%
   - Faturamento >= R$ 50.000 = 5%
   - Faturamento >= R$ 60.000 = 6%
   - Faturamento >= R$ 80.000 = 10%
   
   Base de cálculo: Faturamento MENSAL do consultor (soma de entradas + boletos pagos)
   Percentual aplicado: Escalonado retroativo (todo faturamento do mês recebe o % da faixa atingida)

ARQUITETURA:
============
- CommissionService: Classe principal com métodos estáticos
- CommissionCalculator: Calculadora de percentuais (escala progressiva)
- CommissionValidator: Validação de regras de negócio
- CommissionAuditor: Logs e auditoria de cálculos
"""

import logging
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Tuple, List, Optional
from datetime import datetime, date
from django.db import transaction
from django.db.models import Sum, Q, F
from django.utils import timezone
from django.conf import settings

from comissoes.models import ComissaoLead
from financeiro.models import Comissao

logger = logging.getLogger(__name__)


class CommissionCalculator:
    """Calculadora de percentuais de comissão (lógica de escalonamento)"""
    
    # Tabela de escalonamento para CONSULTORES (faturamento mensal)
    CONSULTOR_ESCALAS = [
        (Decimal('80000.00'), Decimal('10.00')),  # >= R$ 80.000 = 10%
        (Decimal('60000.00'), Decimal('6.00')),   # >= R$ 60.000 = 6%
        (Decimal('50000.00'), Decimal('5.00')),   # >= R$ 50.000 = 5%
        (Decimal('40000.00'), Decimal('4.00')),   # >= R$ 40.000 = 4%
        (Decimal('30000.00'), Decimal('3.00')),   # >= R$ 30.000 = 3%
        (Decimal('20000.00'), Decimal('2.00')),   # >= R$ 20.000 = 2%
        (Decimal('0.00'), Decimal('0.00')),       # < R$ 20.000 = 0% (não ganha comissão ainda)
    ]
    
    @classmethod
    def calcular_percentual_consultor(cls, faturamento_mensal: Decimal) -> Decimal:
        """
        Calcula percentual de comissão do consultor baseado no faturamento mensal.
        
        Regra: Escala progressiva RETROATIVA
        - Se atingir R$ 30.000, TODOS os R$ 30.000 ganham 3%
        - Não é progressivo incremental (ex: primeiros 20k a 2%, próximos 10k a 3%)
        
        Args:
            faturamento_mensal: Valor total faturado no mês (entrada + boletos pagos)
        
        Returns:
            Percentual de comissão (ex: 3.00 para 3%)
        """
        for limite, percentual in cls.CONSULTOR_ESCALAS:
            if faturamento_mensal >= limite:
                logger.debug(
                    f"[CommissionCalculator] Faturamento R$ {faturamento_mensal:.2f} "
                    f"→ Faixa >= R$ {limite:.2f} → {percentual}%"
                )
                return percentual
        
        return Decimal('0.00')
    
    @classmethod
    def calcular_valor_comissao(cls, base_calculo: Decimal, percentual: Decimal) -> Decimal:
        """
        Calcula valor monetário da comissão.
        
        Args:
            base_calculo: Valor sobre o qual aplicar o percentual
            percentual: Percentual (ex: 3.00 para 3%)
        
        Returns:
            Valor da comissão arredondado para 2 casas decimais
        """
        valor = (base_calculo * percentual / Decimal('100')).quantize(
            Decimal('0.01'), 
            rounding=ROUND_HALF_UP
        )
        return valor


class CommissionValidator:
    """Validador de regras de negócio para comissões"""
    
    @staticmethod
    def pode_gerar_comissao_atendente(lead) -> Tuple[bool, str]:
        """
        Valida se pode gerar comissão de atendente.
        
        Args:
            lead: Objeto Lead
        
        Returns:
            (pode_gerar: bool, motivo: str)
        """
        if not lead.atendente:
            return False, "Lead não possui atendente associado"
        
        if not hasattr(lead, 'pix_levantamentos') or not lead.pix_levantamentos.filter(status_pagamento='pago').exists():
            return False, "Lead não possui PIX de levantamento pago"
        
        return True, "OK"
    
    @staticmethod
    def pode_gerar_comissao_venda(venda) -> Tuple[bool, str]:
        """
        Valida se pode gerar comissão de venda.
        
        Args:
            venda: Objeto Venda
        
        Returns:
            (pode_gerar: bool, motivo: str)
        """
        if not venda.captador:
            return False, "Venda não possui captador associado"
        
        if not venda.consultor:
            return False, "Venda não possui consultor associado"
        
        if venda.valor_total <= 0:
            return False, "Venda com valor total zerado"
        
        return True, "OK"


class CommissionAuditor:
    """Auditoria e logging de comissões"""
    
    @staticmethod
    def log_criacao_comissao(tipo: str, usuario, venda=None, parcela=None, 
                            valor: Decimal = None, percentual: Decimal = None,
                            motivo: str = ""):
        """Registra criação de comissão nos logs"""
        from core.services import LogService
        
        detalhes = f"Tipo: {tipo} | Usuário: {usuario.get_full_name() or usuario.email}"
        if venda:
            detalhes += f" | Venda: #{venda.id}"
        if parcela:
            detalhes += f" | Parcela: {parcela.numero_parcela}"
        if valor:
            detalhes += f" | Valor: R$ {valor:.2f}"
        if percentual:
            detalhes += f" | Percentual: {percentual}%"
        if motivo:
            detalhes += f" | Motivo: {motivo}"
        
        LogService.registrar(
            usuario=usuario,
            nivel='INFO',
            mensagem=f"Comissão criada: {detalhes}",
            modulo='financeiro',
            acao='criar_comissao'
        )
    
    @staticmethod
    def log_recalculo_mensal(captador, mes: date, faturamento_anterior: Decimal, 
                            faturamento_novo: Decimal, percentual_anterior: Decimal, 
                            percentual_novo: Decimal):
        """Registra recálculo mensal de comissões"""
        from core.services import LogService
        
        if percentual_anterior != percentual_novo:
            mensagem = (
                f"Recálculo mensal de comissões - {mes.strftime('%m/%Y')} | "
                f"Captador: {captador.get_full_name() or captador.email} | "
                f"Faturamento: R$ {faturamento_anterior:.2f} → R$ {faturamento_novo:.2f} | "
                f"Percentual: {percentual_anterior}% → {percentual_novo}%"
            )
            
            LogService.registrar(
                usuario=captador,
                nivel='WARNING',
                mensagem=mensagem,
                modulo='financeiro',
                acao='recalcular_comissoes_mensais'
            )


class CommissionService:
    """
    Serviço principal de gerenciamento de comissões.
    
    Este serviço deve ser usado em:
    - Webhooks ASAAS (pagamento confirmado)
    - Cadastro de vendas (entrada)
    - Jobs agendados (recálculo mensal)
    - Interface administrativa (ajustes manuais)
    """
    
    @staticmethod
    def obter_configuracoes() -> Dict[str, Decimal]:
        """
        Obtém configurações de comissão do sistema.
        
        Returns:
            dict com: atendente_valor_fixo, consultor_percentual
        """
        from core.models import ConfiguracaoSistema
        
        try:
            valor_atendente = ConfiguracaoSistema.objects.get(
                chave='COMISSAO_ATENDENTE_VALOR_FIXO'
            ).valor
        except ConfiguracaoSistema.DoesNotExist:
            valor_atendente = '0.50'
        
        try:
            percentual_captador = ConfiguracaoSistema.objects.get(
                chave='COMISSAO_CAPTADOR_PERCENTUAL'
            ).valor
        except ConfiguracaoSistema.DoesNotExist:
            percentual_captador = '3.00'
        
        return {
            'atendente_valor_fixo': Decimal(valor_atendente),
            'captador_percentual': Decimal(percentual_captador),
        }
    
    @classmethod
    @transaction.atomic
    def criar_comissao_atendente(cls, lead) -> Optional['ComissaoLead']:
        """
        Cria comissão para atendente (levantamento PIX pago).
        
        Args:
            lead: Objeto Lead com PIX pago
        
        Returns:
            Objeto ComissaoLead criado ou None se já existe
        """
        from comissoes.models import ComissaoLead
        
        # Validar
        pode_gerar, motivo = CommissionValidator.pode_gerar_comissao_atendente(lead)
        if not pode_gerar:
            logger.warning(f"[CommissionService] Não pode gerar comissão atendente: {motivo}")
            return None
        
        # Obter configuração
        config = cls.obter_configuracoes()
        valor_comissao = config['atendente_valor_fixo']
        
        # Criar (ou buscar se já existe)
        comissao, created = ComissaoLead.objects.get_or_create(
            lead=lead,
            atendente=lead.atendente,
            defaults={'valor': valor_comissao}
        )
        
        if created:
            logger.info(
                f"[CommissionService] Comissão atendente criada: "
                f"Lead #{lead.id} | Atendente: {lead.atendente.email} | "
                f"Valor: R$ {valor_comissao:.2f}"
            )
            
            CommissionAuditor.log_criacao_comissao(
                tipo='ATENDENTE_PIX',
                usuario=lead.atendente,
                valor=valor_comissao,
                motivo=f"Levantamento PIX confirmado - Lead #{lead.id}"
            )
        else:
            logger.debug(f"[CommissionService] Comissão atendente já existe para Lead #{lead.id}")
        
        return comissao
    
    @classmethod
    @transaction.atomic
    def criar_comissao_entrada_venda(cls, venda) -> Dict[str, Optional['Comissao']]:
        """
        Cria comissões sobre ENTRADA da venda (captador + consultor).
        
        Chamado após Venda.objects.create() em vendas/views.py
        
        Args:
            venda: Objeto Venda recém-criado
        
        Returns:
            dict: {'captador': Comissao, 'consultor': Comissao}
        """
        from financeiro.models import Comissao
        
        # Validar
        pode_gerar, motivo = CommissionValidator.pode_gerar_comissao_venda(venda)
        if not pode_gerar:
            logger.warning(f"[CommissionService] Não pode gerar comissão entrada: {motivo}")
            return {'captador': None, 'consultor': None}
        
        if venda.valor_entrada <= 0:
            logger.debug(f"[CommissionService] Venda #{venda.id} sem entrada, comissões não criadas")
            return {'captador': None, 'consultor': None}
        
        # Obter configurações
        config = cls.obter_configuracoes()
        percentual_captador = config['captador_percentual']
        
        # Calcular faturamento mensal do consultor (para escala)
        mes_atual = venda.data_venda or timezone.now().date()
        primeiro_dia = mes_atual.replace(day=1)
        
        faturamento_mensal = cls._calcular_faturamento_mensal_consultor(
            consultor=venda.consultor,
            mes=primeiro_dia,
            incluir_venda_atual=venda
        )
        
        percentual_consultor = CommissionCalculator.calcular_percentual_consultor(faturamento_mensal)
        
        # Criar comissões
        comissoes_criadas = {}
        
        # CAPTADOR (fixo 3%)
        valor_captador = CommissionCalculator.calcular_valor_comissao(
            venda.valor_entrada,
            percentual_captador
        )
        
        comissao_captador, created = Comissao.objects.get_or_create(
            usuario=venda.captador,
            venda=venda,
            parcela=None,
            tipo_comissao='CAPTADOR_ENTRADA',
            defaults={
                'valor_comissao': valor_captador,
                'percentual_comissao': percentual_captador,
                'status': 'pendente'
            }
        )
        
        if created:
            logger.info(
                f"[CommissionService] Comissão captador entrada criada: "
                f"Venda #{venda.id} | Captador: {venda.captador.email} | "
                f"Percentual: {percentual_captador}% | Valor: R$ {valor_captador:.2f}"
            )
            
            CommissionAuditor.log_criacao_comissao(
                tipo='CAPTADOR_ENTRADA',
                usuario=venda.captador,
                venda=venda,
                valor=valor_captador,
                percentual=percentual_captador,
                motivo="Entrada paga"
            )
        
        comissoes_criadas['captador'] = comissao_captador
        
        # CONSULTOR (escala progressiva)
        if percentual_consultor > 0:
            valor_consultor = CommissionCalculator.calcular_valor_comissao(
                venda.valor_entrada, 
                percentual_consultor
            )
            
            comissao_consultor, created = Comissao.objects.get_or_create(
                usuario=venda.consultor,
                venda=venda,
                parcela=None,  # Comissão sobre entrada (não vinculada a parcela)
                tipo_comissao='CONSULTOR_ENTRADA',
                defaults={
                    'valor_comissao': valor_consultor,
                    'percentual_comissao': percentual_consultor,
                    'status': 'pendente',
                    'observacoes': f'Escala: R$ {faturamento_mensal:.2f} faturado no mês → {percentual_consultor}%'
                }
            )
            
            if created:
                logger.info(
                    f"[CommissionService] Comissão consultor entrada criada: "
                    f"Venda #{venda.id} | Consultor: {venda.consultor.email} | "
                    f"Faturamento mensal: R$ {faturamento_mensal:.2f} | "
                    f"Percentual: {percentual_consultor}% | Valor: R$ {valor_consultor:.2f}"
                )
                
                CommissionAuditor.log_criacao_comissao(
                    tipo='CONSULTOR_ENTRADA',
                    usuario=venda.consultor,
                    venda=venda,
                    valor=valor_consultor,
                    percentual=percentual_consultor,
                    motivo=f"Entrada paga - Faturamento mensal R$ {faturamento_mensal:.2f}"
                )
            
            comissoes_criadas['consultor'] = comissao_consultor
        else:
            logger.debug(
                f"[CommissionService] Consultor não atingiu faturamento mínimo (R$ 20.000) - "
                f"Faturamento atual: R$ {faturamento_mensal:.2f}"
            )
            comissoes_criadas['consultor'] = None
        
        return comissoes_criadas
    
    @classmethod
    @transaction.atomic
    def criar_comissao_parcela_paga(cls, parcela) -> Dict[str, Optional['Comissao']]:
        """
        Cria comissões quando uma PARCELA é paga (captador + consultor).
        
        Chamado via webhook ASAAS ou signal post_save em Parcela.
        
        Args:
            parcela: Objeto Parcela com status='paga'
        
        Returns:
            dict: {'captador': Comissao, 'consultor': Comissao}
        """
        from financeiro.models import Comissao
        
        venda = parcela.venda
        
        # Validar
        pode_gerar, motivo = CommissionValidator.pode_gerar_comissao_venda(venda)
        if not pode_gerar:
            logger.warning(f"[CommissionService] Não pode gerar comissão parcela: {motivo}")
            return {'captador': None, 'consultor': None}
        
        if parcela.status != 'paga':
            logger.debug(f"[CommissionService] Parcela #{parcela.id} não está paga, comissões não criadas")
            return {'captador': None, 'consultor': None}
        
        # Obter configurações
        config = cls.obter_configuracoes()
        percentual_captador = config['captador_percentual']
        
        # Calcular faturamento mensal do consultor
        mes_pagamento = parcela.data_pagamento or timezone.now().date()
        primeiro_dia = mes_pagamento.replace(day=1)
        
        faturamento_mensal = cls._calcular_faturamento_mensal_consultor(
            consultor=venda.consultor,
            mes=primeiro_dia,
            incluir_parcela_atual=parcela
        )
        
        percentual_consultor = CommissionCalculator.calcular_percentual_consultor(faturamento_mensal)
        
        # Criar comissões
        comissoes_criadas = {}
        
        # CAPTADOR (fixo 3%)
        valor_captador = CommissionCalculator.calcular_valor_comissao(
            parcela.valor,
            percentual_captador
        )
        
        comissao_captador, created = Comissao.objects.get_or_create(
            usuario=venda.captador,
            venda=venda,
            parcela=parcela,
            tipo_comissao='CAPTADOR_PARCELA',
            defaults={
                'valor_comissao': valor_captador,
                'percentual_comissao': percentual_captador,
                'status': 'pendente'
            }
        )
        
        if created:
            logger.info(
                f"[CommissionService] Comissão captador parcela criada: "
                f"Parcela #{parcela.id} | Captador: {venda.captador.email} | "
                f"Valor: R$ {valor_captador:.2f}"
            )
            
            CommissionAuditor.log_criacao_comissao(
                tipo='CAPTADOR_PARCELA',
                usuario=venda.captador,
                venda=venda,
                parcela=parcela,
                valor=valor_captador,
                percentual=percentual_captador,
                motivo="Parcela paga"
            )
        
        comissoes_criadas['captador'] = comissao_captador
        
        # CONSULTOR (escala progressiva)
        if percentual_consultor > 0:
            valor_consultor = CommissionCalculator.calcular_valor_comissao(
                parcela.valor,
                percentual_consultor
            )
            
            comissao_consultor, created = Comissao.objects.get_or_create(
                usuario=venda.consultor,
                venda=venda,
                parcela=parcela,
                tipo_comissao='CONSULTOR_PARCELA',
                defaults={
                    'valor_comissao': valor_consultor,
                    'percentual_comissao': percentual_consultor,
                    'status': 'pendente',
                    'observacoes': f'Escala: R$ {faturamento_mensal:.2f} faturado no mês → {percentual_consultor}%'
                }
            )
            
            if created:
                logger.info(
                    f"[CommissionService] Comissão consultor parcela criada: "
                    f"Parcela #{parcela.id} (Venda #{venda.id}) | "
                    f"Consultor: {venda.consultor.email} | "
                    f"Faturamento mensal: R$ {faturamento_mensal:.2f} | "
                    f"Percentual: {percentual_consultor}% | Valor: R$ {valor_consultor:.2f}"
                )
                
                CommissionAuditor.log_criacao_comissao(
                    tipo='CONSULTOR_PARCELA',
                    usuario=venda.consultor,
                    venda=venda,
                    parcela=parcela,
                    valor=valor_consultor,
                    percentual=percentual_consultor,
                    motivo=f"Parcela paga - Faturamento mensal R$ {faturamento_mensal:.2f}"
                )
            
            comissoes_criadas['consultor'] = comissao_consultor
        else:
            logger.debug(
                f"[CommissionService] Consultor não atingiu faturamento mínimo - "
                f"Faturamento: R$ {faturamento_mensal:.2f}"
            )
            comissoes_criadas['consultor'] = None
        
        return comissoes_criadas
    
    @classmethod
    def _calcular_faturamento_mensal_consultor(cls, consultor, mes: date, 
                                             incluir_venda_atual=None,
                                             incluir_parcela_atual=None) -> Decimal:
        """
        Calcula faturamento total do consultor em um mês específico.
        
        Faturamento = Entradas pagas + Parcelas pagas
        
        Args:
            consultor: Objeto User (consultor)
            mes: Data (primeiro dia do mês para cálculo)
            incluir_venda_atual: Venda sendo criada agora (entrada)
            incluir_parcela_atual: Parcela sendo paga agora
        
        Returns:
            Decimal: Faturamento total do mês
        """
        from vendas.models import Venda
        from financeiro.models import Parcela
        
        primeiro_dia = mes.replace(day=1)
        if mes.month == 12:
            ultimo_dia = mes.replace(year=mes.year + 1, month=1, day=1)
        else:
            ultimo_dia = mes.replace(month=mes.month + 1, day=1)
        
        # Entradas pagas no mês
        vendas_mes = Venda.objects.filter(
            consultor=consultor,
            data_venda__gte=primeiro_dia,
            data_venda__lt=ultimo_dia,
            valor_entrada__gt=0
        )
        
        total_entradas = vendas_mes.aggregate(total=Sum('valor_entrada'))['total'] or Decimal('0.00')
        
        # Parcelas pagas no mês
        parcelas_pagas_mes = Parcela.objects.filter(
            venda__consultor=consultor,
            status='paga',
            data_pagamento__gte=primeiro_dia,
            data_pagamento__lt=ultimo_dia
        )
        
        total_parcelas = parcelas_pagas_mes.aggregate(total=Sum('valor'))['total'] or Decimal('0.00')
        
        # Incluir venda atual (se fornecida)
        if incluir_venda_atual and incluir_venda_atual.valor_entrada > 0:
            total_entradas += incluir_venda_atual.valor_entrada
        
        # Incluir parcela atual (se fornecida)
        if incluir_parcela_atual:
            total_parcelas += incluir_parcela_atual.valor
        
        faturamento_total = total_entradas + total_parcelas
        
        logger.debug(
            f"[CommissionService] Faturamento mensal consultor {consultor.email} | "
            f"Mês: {mes.strftime('%m/%Y')} | "
            f"Entradas: R$ {total_entradas:.2f} | "
            f"Parcelas: R$ {total_parcelas:.2f} | "
            f"Total: R$ {faturamento_total:.2f}"
        )
        
        return faturamento_total
    
    @classmethod
    def recalcular_comissoes_consultor_mes(cls, consultor, mes: date) -> Dict[str, any]:
        """
        Recalcula TODAS as comissões do consultor em um mês específico.
        
        Usado quando:
        - Fim do mês (job agendado)
        - Pagamento atrasado que muda a faixa de comissão
        - Ajuste manual
        
        CUIDADO: Pode alterar percentuais de comissões já geradas!
        
        Args:
            consultor: Objeto User
            mes: Data (primeiro dia do mês)
        
        Returns:
            dict: {'recalculadas': int, 'valor_anterior': Decimal, 'valor_novo': Decimal}
        """
        from financeiro.models import Comissao
        
        # Calcular faturamento mensal ATUAL
        faturamento_mensal = cls._calcular_faturamento_mensal_consultor(consultor, mes)
        percentual_novo = CommissionCalculator.calcular_percentual_consultor(faturamento_mensal)
        
        # Buscar todas as comissões do consultor neste mês
        primeiro_dia = mes.replace(day=1)
        if mes.month == 12:
            ultimo_dia = mes.replace(year=mes.year + 1, month=1, day=1)
        else:
            ultimo_dia = mes.replace(month=mes.month + 1, day=1)
        
        comissoes_mes = Comissao.objects.filter(
            usuario=consultor,
            data_calculada__gte=primeiro_dia,
            data_calculada__lt=ultimo_dia,
            tipo_comissao__in=['CONSULTOR_ENTRADA', 'CONSULTOR_PARCELA']
        )
        
        valor_anterior_total = comissoes_mes.aggregate(total=Sum('valor_comissao'))['total'] or Decimal('0.00')
        recalculadas = 0
        
        # Recalcular cada comissão
        with transaction.atomic():
            for comissao in comissoes_mes:
                percentual_anterior = comissao.percentual_comissao
                
                if percentual_anterior != percentual_novo:
                    # Recalcular valor
                    if comissao.parcela:
                        base_calculo = comissao.parcela.valor
                    else:
                        base_calculo = comissao.venda.valor_entrada
                    
                    valor_novo = CommissionCalculator.calcular_valor_comissao(
                        base_calculo,
                        percentual_novo
                    )
                    
                    comissao.valor_comissao = valor_novo
                    comissao.percentual_comissao = percentual_novo
                    comissao.observacoes = (
                        f"Recalculado em {timezone.now().date().isoformat()} | "
                        f"Percentual anterior: {percentual_anterior}% | "
                        f"Faturamento mensal: R$ {faturamento_mensal:.2f} → {percentual_novo}%"
                    )
                    comissao.save()
                    
                    recalculadas += 1
                    
                    logger.info(
                        f"[CommissionService] Comissão recalculada: ID #{comissao.id} | "
                        f"Percentual: {percentual_anterior}% → {percentual_novo}% | "
                        f"Valor: R$ {comissao.valor_comissao:.2f}"
                    )
        
        valor_novo_total = comissoes_mes.aggregate(total=Sum('valor_comissao'))['total'] or Decimal('0.00')
        
        if recalculadas > 0:
            CommissionAuditor.log_recalculo_mensal(
                captador=consultor,
                mes=mes,
                faturamento_anterior=Decimal('0.00'),  # Não temos histórico
                faturamento_novo=faturamento_mensal,
                percentual_anterior=Decimal('0.00'),
                percentual_novo=percentual_novo
            )
        
        return {
            'recalculadas': recalculadas,
            'valor_anterior': valor_anterior_total,
            'valor_novo': valor_novo_total,
            'faturamento_mensal': faturamento_mensal,
            'percentual_aplicado': percentual_novo
        }
