import re
from datetime import datetime
from decimal import Decimal
import json

class Validadores:
    """Validações comuns reutilizáveis"""
    
    @staticmethod
    def validar_cnpj(cnpj):
        """Valida CNPJ"""
        cnpj = re.sub(r'[^0-9]', '', cnpj)  # Remove caracteres não numéricos

        if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
            return False

        # Cálculo dos dígitos verificadores
        pesos_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        pesos_2 = [6] + pesos_1

        # Primeiro dígito verificador
        soma = sum(int(cnpj[i]) * pesos_1[i] for i in range(12))
        digito_1 = 11 - (soma % 11)
        if digito_1 >= 10:
            digito_1 = 0

        # Segundo dígito verificador
        soma = sum(int(cnpj[i]) * pesos_2[i] for i in range(13))
        digito_2 = 11 - (soma % 11)
        if digito_2 >= 10:
            digito_2 = 0

        # Verifica os dígitos calculados com os informados
        return cnpj[-2:] == f"{digito_1}{digito_2}"

    @staticmethod
    def validar_cpf(cpf):
        """Valida CPF"""
        cpf = re.sub(r'[^0-9]', '', cpf)
        if len(cpf) != 11 or cpf == cpf[0] * 11:
            return False
        
        # Cálculo dos dígitos verificadores
        for i in range(9, 11):
            soma = sum(int(cpf[num]) * ((i+1) - num) for num in range(0, i))
            digito = (soma * 10) % 11
            if digito == 10:
                digito = 0
            if digito != int(cpf[i]):
                return False
        return True
    
    @staticmethod
    def validar_telefone(telefone):
        """Valida telefone brasileiro"""
        telefone = re.sub(r'[^0-9]', '', telefone)
        return len(telefone) in [10, 11]  # Com ou sem DDD + 9º dígito
    
    @staticmethod
    def formatar_moeda(valor):
        """Formata valor para exibição em Real"""
        if isinstance(valor, (int, float, Decimal)):
            return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        return valor
        
    @staticmethod
    def formatar_telefone(telefone):
        """Formata telefone para exibição"""
        telefone = re.sub(r'[^0-9]', '', telefone)
        
        if len(telefone) == 11:
            return f"({telefone[:2]}) {telefone[2:7]}-{telefone[7:]}"
        elif len(telefone) == 10:
            return f"({telefone[:2]}) {telefone[2:6]}-{telefone[6:]}"
        return telefone

class CalculosFinanceiros:
    """Cálculos financeiros reutilizáveis"""
    
    @staticmethod
    def calcular_comissao(valor, percentual):
        """Calcula valor de comissão"""
        return valor * (percentual / 100)
    
    @staticmethod
    def calcular_valor_parcelas(valor_total, entrada, num_parcelas):
        """Calcula valor das parcelas"""
        if entrada >= valor_total:
            return 0
        return (valor_total - entrada) / num_parcelas


class FormularioUtils:
    """Utilitários para manipulação de formulários"""
    
    @staticmethod
    def validar_etapa_lead(nome, telefone, email=None):
        """Valida dados da primeira etapa do formulário de lead"""
        erros = []
        
        if not nome or len(nome.strip()) < 3:
            erros.append("Nome completo deve ter pelo menos 3 caracteres.")
        
        if not telefone:
            erros.append("Telefone é obrigatório.")
        else:
            telefone_limpo = re.sub(r'[^0-9]', '', telefone)
            if len(telefone_limpo) < 10:
                erros.append("Telefone inválido. Deve ter pelo menos 10 dígitos incluindo DDD.")
        
        if email and not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', email):
            erros.append("Email em formato inválido.")
            
        return {
            "valido": len(erros) == 0,
            "erros": erros
        }
    
    @staticmethod
    def gerar_codigo_pix(valor, descricao=None):
        """
        Simula a geração de um código PIX.
        Em um ambiente real, seria integrado com um PSP (Provedor de Serviços de Pagamento)
        """
        # Este é apenas um código modelo para demonstração
        codigo_base = "00020126580014BR.GOV.BCB.PIX0136"
        chave_pix = "pix-sistema-mrbaruch-12345"
        valor_formatado = f"{float(valor):.2f}"
        descricao = descricao or "Consulta Mr Baruch"
        
        # Em um sistema real, aqui seria gerado o hash e validações adequadas
        return f"{codigo_base}{chave_pix}5204{valor_formatado:0>10}5802BR5925{descricao}6009Sao Paulo62070503***6304ABCD"