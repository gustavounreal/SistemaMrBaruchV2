"""
Template tags customizados para formatação de valores
"""
from django import template
from decimal import Decimal, DecimalException

register = template.Library()


@register.filter(name='moeda_br')
def moeda_br(value):
    """
    Formata um valor numérico para o padrão monetário brasileiro
    Uso: {{ valor|moeda_br }}
    Exemplo: 1234.56 -> R$ 1.234,56
    """
    if value is None or value == '':
        return 'R$ 0,00'
    
    try:
        # Converte para Decimal para precisão
        if isinstance(value, str):
            value = value.replace(',', '.')
        valor = Decimal(str(value))
        
        # Formata com separadores brasileiros
        valor_str = f'{valor:,.2f}'
        
        # Troca separadores (1,234.56 -> 1.234,56)
        valor_str = valor_str.replace(',', 'X').replace('.', ',').replace('X', '.')
        
        return f'R$ {valor_str}'
    except (ValueError, TypeError, DecimalException):
        return str(value)


@register.filter(name='inteiro_br')
def inteiro_br(value):
    """
    Formata um número inteiro com separadores de milhares brasileiros
    Uso: {{ numero|inteiro_br }}
    Exemplo: 1234 -> 1.234
    """
    if value is None or value == '':
        return '0'
    
    try:
        valor = int(value)
        return f'{valor:,}'.replace(',', '.')
    except (ValueError, TypeError):
        return str(value)
