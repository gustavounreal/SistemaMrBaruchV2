from django import template
from decimal import Decimal, InvalidOperation

register = template.Library()


def _thousands_dot(n: int) -> str:
    s = str(n)
    parts = []
    while s:
        parts.insert(0, s[-3:])
        s = s[:-3]
    return '.'.join(parts)


@register.filter
def currency_brl(value):
    """Format a number as BRL currency (R$ 1.234,56) deterministically.

    Always returns a string like 'R$ 1.234,56' even on environments without pt_BR locale.
    """
    try:
        v = Decimal(value)
    except (InvalidOperation, TypeError, ValueError):
        return value

    sign = '-' if v < 0 else ''
    v = abs(v)
    int_part = int(v)
    dec_part = int((v - int_part) * 100)
    int_str = _thousands_dot(int_part)
    return f"R$ {sign}{int_str},{dec_part:02d}"


@register.filter
def lookup(dictionary, key):
    """Lookup a value in a list of tuples (choices) by key."""
    if not dictionary or not key:
        return key
    for choice_key, choice_label in dictionary:
        if str(choice_key) == str(key):
            return choice_label
    return key
