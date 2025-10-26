"""
Sistema de Validação e Recuperação Automática de Comissões
==========================================================

Este módulo garante que TODAS as comissões sejam criadas corretamente:
- Atendente: PIX de levantamento pago
- Captador: Entrada paga + Parcelas pagas
- Consultor: Entrada paga + Parcelas pagas

Executa verificações automáticas e cria comissões faltantes.
"""

import logging
from decimal import Decimal
from typing import List, Dict, Tuple
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class CommissionValidator:
    """Validador e recuperador automático de comissões"""
    
    @classmethod
    def validar_e_recuperar_todas_comissoes(cls) -> Dict[str, int]:
        """
        Executa validação completa de todas as comissões do sistema.
        
        Returns:
            dict: Estatísticas de comissões criadas/corrigidas
        """
        logger.info("[CommissionValidator] Iniciando validação completa de comissões...")
        
        stats = {
            'comissoes_atendente_criadas': 0,
            'comissoes_entrada_criadas': 0,
            'comissoes_parcela_criadas': 0,
            'erros': 0
        }
        
        # 1. Validar comissões de atendente (PIX Levantamento)
        try:
            stats['comissoes_atendente_criadas'] = cls._validar_comissoes_atendente()
        except Exception as e:
            logger.error(f"[CommissionValidator] Erro ao validar comissões atendente: {e}")
            stats['erros'] += 1
        
        # 2. Validar comissões de entrada (Captador + Consultor)
        try:
            stats['comissoes_entrada_criadas'] = cls._validar_comissoes_entrada()
        except Exception as e:
            logger.error(f"[CommissionValidator] Erro ao validar comissões entrada: {e}")
            stats['erros'] += 1
        
        # 3. Validar comissões de parcelas (Captador + Consultor)
        try:
            stats['comissoes_parcela_criadas'] = cls._validar_comissoes_parcelas()
        except Exception as e:
            logger.error(f"[CommissionValidator] Erro ao validar comissões parcelas: {e}")
            stats['erros'] += 1
        
        logger.info(f"[CommissionValidator] Validação concluída: {stats}")
        return stats
    
    @classmethod
    def _validar_comissoes_atendente(cls) -> int:
        """
        Valida e cria comissões de atendente para PIX de levantamento pagos.
        
        Returns:
            int: Quantidade de comissões criadas
        """
        from financeiro.models import PixLevantamento
        from comissoes.models import ComissaoLead
        from core.commission_service import CommissionService
        
        logger.info("[CommissionValidator] Validando comissões de atendente...")
        
        # Buscar PIX de levantamento pagos
        pix_pagos = PixLevantamento.objects.filter(
            status_pagamento='pago'
        ).select_related('lead', 'lead__atendente')
        
        comissoes_criadas = 0
        
        for pix in pix_pagos:
            # Verificar se já existe comissão
            if not ComissaoLead.objects.filter(lead=pix.lead).exists():
                try:
                    comissao = CommissionService.criar_comissao_atendente(pix.lead)
                    if comissao:
                        comissoes_criadas += 1
                        logger.info(f"[CommissionValidator] ✅ Comissão atendente criada: Lead #{pix.lead.id}")
                except Exception as e:
                    logger.error(f"[CommissionValidator] ❌ Erro ao criar comissão atendente Lead #{pix.lead.id}: {e}")
        
        logger.info(f"[CommissionValidator] Comissões atendente criadas: {comissoes_criadas}")
        return comissoes_criadas
    
    @classmethod
    def _validar_comissoes_entrada(cls) -> int:
        """
        Valida e cria comissões de entrada (captador + consultor) para entradas pagas.
        
        Returns:
            int: Quantidade de comissões criadas
        """
        from vendas.models import Venda
        from financeiro.models import Comissao
        from core.commission_service import CommissionService
        
        logger.info("[CommissionValidator] Validando comissões de entrada...")
        
        # Buscar vendas com entrada PAGA
        vendas_entrada_paga = Venda.objects.filter(
            status_pagamento_entrada='PAGO',
            valor_entrada__gt=0
        ).exclude(
            status='CANCELADO'
        ).select_related('captador', 'consultor', 'cliente')
        
        comissoes_criadas = 0
        
        for venda in vendas_entrada_paga:
            # Verificar se já existem comissões de entrada
            tem_comissao_captador = Comissao.objects.filter(
                venda=venda,
                tipo_comissao='CAPTADOR_ENTRADA'
            ).exists()
            
            tem_comissao_consultor = Comissao.objects.filter(
                venda=venda,
                tipo_comissao='CONSULTOR_ENTRADA'
            ).exists()
            
            # Se não tem nenhuma das duas, criar
            if not tem_comissao_captador or not tem_comissao_consultor:
                try:
                    comissoes = CommissionService.criar_comissao_entrada_venda(venda)
                    
                    if comissoes.get('captador') and not tem_comissao_captador:
                        comissoes_criadas += 1
                        logger.info(f"[CommissionValidator] ✅ Comissão CAPTADOR_ENTRADA criada: Venda #{venda.id}")
                    
                    if comissoes.get('consultor') and not tem_comissao_consultor:
                        comissoes_criadas += 1
                        logger.info(f"[CommissionValidator] ✅ Comissão CONSULTOR_ENTRADA criada: Venda #{venda.id}")
                    
                except Exception as e:
                    logger.error(f"[CommissionValidator] ❌ Erro ao criar comissões entrada Venda #{venda.id}: {e}")
        
        logger.info(f"[CommissionValidator] Comissões de entrada criadas: {comissoes_criadas}")
        return comissoes_criadas
    
    @classmethod
    def _validar_comissoes_parcelas(cls) -> int:
        """
        Valida e cria comissões de parcelas (captador + consultor) para parcelas pagas.
        
        Returns:
            int: Quantidade de comissões criadas
        """
        from financeiro.models import Parcela, Comissao
        from core.commission_service import CommissionService
        
        logger.info("[CommissionValidator] Validando comissões de parcelas...")
        
        # Buscar parcelas PAGAS (exceto entrada - numero_parcela=0)
        parcelas_pagas = Parcela.objects.filter(
            status='paga',
            numero_parcela__gt=0  # Excluir entradas (já validadas acima)
        ).select_related('venda', 'venda__captador', 'venda__consultor')
        
        comissoes_criadas = 0
        
        for parcela in parcelas_pagas:
            # Verificar se já existem comissões desta parcela
            tem_comissao_captador = Comissao.objects.filter(
                venda=parcela.venda,
                parcela=parcela,
                tipo_comissao='CAPTADOR_PARCELA'
            ).exists()
            
            tem_comissao_consultor = Comissao.objects.filter(
                venda=parcela.venda,
                parcela=parcela,
                tipo_comissao='CONSULTOR_PARCELA'
            ).exists()
            
            # Se não tem nenhuma das duas, criar
            if not tem_comissao_captador or not tem_comissao_consultor:
                try:
                    comissoes = CommissionService.criar_comissao_parcela_paga(parcela)
                    
                    if comissoes.get('captador') and not tem_comissao_captador:
                        comissoes_criadas += 1
                        logger.info(f"[CommissionValidator] ✅ Comissão CAPTADOR_PARCELA criada: Parcela #{parcela.id}")
                    
                    if comissoes.get('consultor') and not tem_comissao_consultor:
                        comissoes_criadas += 1
                        logger.info(f"[CommissionValidator] ✅ Comissão CONSULTOR_PARCELA criada: Parcela #{parcela.id}")
                    
                except Exception as e:
                    logger.error(f"[CommissionValidator] ❌ Erro ao criar comissões parcela #{parcela.id}: {e}")
        
        logger.info(f"[CommissionValidator] Comissões de parcelas criadas: {comissoes_criadas}")
        return comissoes_criadas
    
    @classmethod
    def validar_comissoes_venda_especifica(cls, venda_id: int) -> Dict[str, bool]:
        """
        Valida e cria comissões para uma venda específica.
        
        Args:
            venda_id: ID da venda
        
        Returns:
            dict: Status de criação das comissões
        """
        from vendas.models import Venda
        from financeiro.models import Comissao, Parcela
        from core.commission_service import CommissionService
        
        try:
            venda = Venda.objects.select_related('captador', 'consultor').get(id=venda_id)
        except Venda.DoesNotExist:
            logger.error(f"[CommissionValidator] Venda #{venda_id} não encontrada")
            return {'erro': True}
        
        resultado = {
            'entrada_captador': False,
            'entrada_consultor': False,
            'parcelas_criadas': 0
        }
        
        # 1. Validar comissão de entrada
        if venda.status_pagamento_entrada == 'PAGO' and venda.valor_entrada > 0:
            tem_comissao_captador = Comissao.objects.filter(
                venda=venda, tipo_comissao='CAPTADOR_ENTRADA'
            ).exists()
            
            tem_comissao_consultor = Comissao.objects.filter(
                venda=venda, tipo_comissao='CONSULTOR_ENTRADA'
            ).exists()
            
            if not tem_comissao_captador or not tem_comissao_consultor:
                comissoes = CommissionService.criar_comissao_entrada_venda(venda)
                resultado['entrada_captador'] = bool(comissoes.get('captador'))
                resultado['entrada_consultor'] = bool(comissoes.get('consultor'))
        
        # 2. Validar comissões de parcelas pagas
        parcelas_pagas = Parcela.objects.filter(venda=venda, status='paga', numero_parcela__gt=0)
        
        for parcela in parcelas_pagas:
            tem_comissao = Comissao.objects.filter(
                venda=venda,
                parcela=parcela,
                tipo_comissao__in=['CAPTADOR_PARCELA', 'CONSULTOR_PARCELA']
            ).exists()
            
            if not tem_comissao:
                comissoes = CommissionService.criar_comissao_parcela_paga(parcela)
                if comissoes.get('captador') or comissoes.get('consultor'):
                    resultado['parcelas_criadas'] += 1
        
        return resultado
    
    @classmethod
    def gerar_relatorio_comissoes_faltantes(cls) -> Dict[str, List]:
        """
        Gera relatório de comissões que deveriam existir mas não foram criadas.
        
        Returns:
            dict: Listas de vendas/leads com comissões faltantes
        """
        from vendas.models import Venda
        from financeiro.models import PixLevantamento, Parcela, Comissao
        from comissoes.models import ComissaoLead
        
        relatorio = {
            'pix_levantamento_sem_comissao': [],
            'entradas_pagas_sem_comissao': [],
            'parcelas_pagas_sem_comissao': []
        }
        
        # 1. PIX Levantamento pagos sem comissão
        pix_pagos = PixLevantamento.objects.filter(status_pagamento='pago')
        for pix in pix_pagos:
            if not ComissaoLead.objects.filter(lead=pix.lead).exists():
                relatorio['pix_levantamento_sem_comissao'].append({
                    'lead_id': pix.lead.id,
                    'lead_nome': pix.lead.nome_completo,
                    'valor': float(pix.valor),
                    'data_pagamento': pix.data_criacao
                })
        
        # 2. Entradas pagas sem comissão
        vendas_entrada_paga = Venda.objects.filter(
            status_pagamento_entrada='PAGO',
            valor_entrada__gt=0
        ).exclude(status='CANCELADO')
        
        for venda in vendas_entrada_paga:
            tem_comissao = Comissao.objects.filter(
                venda=venda,
                tipo_comissao__in=['CAPTADOR_ENTRADA', 'CONSULTOR_ENTRADA']
            ).exists()
            
            if not tem_comissao:
                relatorio['entradas_pagas_sem_comissao'].append({
                    'venda_id': venda.id,
                    'valor_entrada': float(venda.valor_entrada),
                    'data_venda': venda.data_venda
                })
        
        # 3. Parcelas pagas sem comissão
        parcelas_pagas = Parcela.objects.filter(
            status='paga',
            numero_parcela__gt=0
        )
        
        for parcela in parcelas_pagas:
            tem_comissao = Comissao.objects.filter(
                parcela=parcela,
                tipo_comissao__in=['CAPTADOR_PARCELA', 'CONSULTOR_PARCELA']
            ).exists()
            
            if not tem_comissao:
                relatorio['parcelas_pagas_sem_comissao'].append({
                    'parcela_id': parcela.id,
                    'venda_id': parcela.venda.id,
                    'numero_parcela': parcela.numero_parcela,
                    'valor': float(parcela.valor),
                    'data_pagamento': parcela.data_pagamento
                })
        
        return relatorio
