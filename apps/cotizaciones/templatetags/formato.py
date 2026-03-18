"""
Template filters para formateo argentino de números.

Uso:
    {% load formato %}
    {{ precio|precio_ar }}       → $2.480.000
    {{ dimension|dimension_ar }} → 3,95
    {{ cantidad|cantidad_ar }}   → 4
"""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


def _to_decimal(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal('0')


@register.filter
def precio_ar(value):
    """Formato precio argentino: $2.480.000 (sin decimales, punto de miles)."""
    d = _to_decimal(value)
    entero = int(d)
    # Formato con punto de miles
    s = f'{entero:,}'.replace(',', '.')
    return f'${s}'


@register.filter
def dimension_ar(value):
    """Formato dimensión: 3,95 (coma decimal, max 2 decimales, sin trailing zeros)."""
    d = _to_decimal(value)
    # Si es entero, mostrar sin decimales
    if d == d.to_integral_value():
        entero = int(d)
        s = f'{entero:,}'.replace(',', '.')
        return s
    # Max 2 decimales, quitar trailing zeros
    s = f'{float(d):.2f}'.rstrip('0').rstrip('.')
    # Reemplazar punto decimal por coma, agregar punto de miles a parte entera
    partes = s.split('.')
    entero = int(partes[0])
    parte_entera = f'{entero:,}'.replace(',', '.')
    if len(partes) > 1:
        return f'{parte_entera},{partes[1]}'
    return parte_entera


@register.filter
def cantidad_ar(value):
    """Formato cantidad entera: 4 (sin decimales, punto de miles si > 999)."""
    d = _to_decimal(value)
    entero = int(d)
    return f'{entero:,}'.replace(',', '.')
