"""
Motor de cotización — servicios de negocio.

Contiene la lógica de:
- Dimensiones acumuladas (SUM/MAX)
- Check de compatibilidad (Vetado/Forzado)
- Check de propiedades (Min/Max vs acumulado)
- Productos disponibles por paso (filtrado completo)
- Rodados automáticos
- Bonificaciones en cascada
- IVA por alícuota
- Cálculo de totales
"""

from collections import defaultdict
from decimal import Decimal

from apps.catalogo.models import (
    Compatibilidad,
    Familia,
    Implemento,
    Producto,
    ProductoPropiedad,
    Propiedad,
)


def calcular_dimensiones(items_seleccionados):
    """
    Dado un listado de (producto_id, cantidad), calcula las dimensiones
    acumuladas según la agregación de cada propiedad (SUM o MAX).

    Args:
        items_seleccionados: lista de tuplas (producto_id, cantidad)
            o lista de producto_ids (cantidad=1 implícita)

    Returns:
        dict {propiedad_id: valor_acumulado}
    """
    if not items_seleccionados:
        return {}

    # Normalizar input
    items = []
    for item in items_seleccionados:
        if isinstance(item, (list, tuple)):
            items.append((item[0], item[1]))
        else:
            items.append((item, 1))

    producto_ids = [pid for pid, _ in items]
    cantidades = {pid: cant for pid, cant in items}

    prod_props = ProductoPropiedad.objects.filter(
        producto_id__in=producto_ids,
        tipo='Exacto',
    ).select_related('propiedad')

    # Agrupar valores por propiedad
    valores_por_propiedad = defaultdict(list)
    for pp in prod_props:
        cant = cantidades.get(pp.producto_id, 1)
        valores_por_propiedad[pp.propiedad].append(pp.valor * cant)

    # Aplicar agregación
    acumulado = {}
    for propiedad, valores in valores_por_propiedad.items():
        if propiedad.agregacion == 'SUM':
            acumulado[propiedad.id] = sum(valores)
        else:  # MAX
            acumulado[propiedad.id] = max(valores)

    return acumulado


def check_compatibilidad(candidato_id, seleccionados_ids):
    """
    Verifica si un producto candidato es compatible con los ya seleccionados.

    Args:
        candidato_id: ID del producto candidato
        seleccionados_ids: lista de IDs de productos ya seleccionados

    Returns:
        'SI' si es forzado (debe mostrarse)
        'NO' si es vetado o ya seleccionado
        None si no hay regla
    """
    if candidato_id in seleccionados_ids:
        return 'NO'

    if not seleccionados_ids:
        return None

    reglas = Compatibilidad.objects.filter(
        producto_padre_id__in=seleccionados_ids,
        producto_hijo_id=candidato_id,
    )

    for regla in reglas:
        if regla.tipo == 'Forzado':
            return 'SI'
        if regla.tipo == 'Vetado':
            return 'NO'

    return None


def check_propiedades(candidato_id, acumulado):
    """
    Verifica si un producto candidato cumple con las restricciones
    Min/Max contra las dimensiones acumuladas.

    Args:
        candidato_id: ID del producto candidato
        acumulado: dict {propiedad_id: valor_acumulado}

    Returns:
        True si pasa todas las validaciones, False si no
    """
    restricciones = ProductoPropiedad.objects.filter(
        producto_id=candidato_id,
        tipo__in=['Minimo', 'Maximo'],
    )

    for pp in restricciones:
        dim_actual = acumulado.get(pp.propiedad_id, Decimal('0'))
        if pp.tipo == 'Minimo' and dim_actual < pp.valor:
            return False
        if pp.tipo == 'Maximo' and dim_actual > pp.valor:
            return False

    return True


def get_productos_disponibles(implemento_id, orden_actual, seleccionados_ids,
                               acumulado=None):
    """
    Retorna los productos disponibles para un paso dado, aplicando
    filtros de compatibilidad y propiedades.

    Args:
        implemento_id: ID del implemento
        orden_actual: número de orden del paso actual
        seleccionados_ids: lista de IDs de productos ya seleccionados
        acumulado: dict de dimensiones acumuladas (se calcula si no se pasa)

    Returns:
        QuerySet de Producto filtrado
    """
    if acumulado is None:
        acumulado = calcular_dimensiones(seleccionados_ids)

    # Productos de familias con el orden actual
    familias = Familia.objects.filter(
        implemento_id=implemento_id,
        orden=orden_actual,
    )
    candidatos = Producto.objects.filter(
        implemento_id=implemento_id,
        familia__in=familias,
    )

    disponibles = []
    for producto in candidatos:
        compat = check_compatibilidad(producto.id, seleccionados_ids)
        if compat == 'NO':
            continue
        if compat == 'SI':
            disponibles.append(producto)
            continue
        # Sin regla → verificar propiedades
        if check_propiedades(producto.id, acumulado):
            disponibles.append(producto)

    return disponibles


def get_rodados_para_implemento(implemento, seleccionados_ids, acumulado=None):
    """
    Determina qué pasos de rodados mostrar basándose en las dimensiones
    acumuladas. Si Llantas > 0, muestra Llantas. Si Ejes > 0, muestra Ejes.
    Si Elásticos > 0, muestra Elásticos. Si alguno es 0, lo saltea.

    Args:
        implemento: instancia de Implemento
        seleccionados_ids: lista de IDs de productos ya seleccionados
        acumulado: dict de dimensiones acumuladas

    Returns:
        lista de dicts con info de cada familia de rodados y sus productos,
        o lista vacía si no aplica
    """
    if implemento.accesorios_tipo != 'Rodados':
        return []

    if acumulado is None:
        acumulado = calcular_dimensiones(seleccionados_ids)

    # Buscar implemento "Rodados"
    try:
        imp_rodados = Implemento.objects.get(
            tenant=implemento.tenant,
            nombre='Rodados',
        )
    except Implemento.DoesNotExist:
        return []

    # Obtener cantidades del acumulado
    propiedades = {p.nombre: p for p in Propiedad.objects.filter(tenant=implemento.tenant)}
    props = {
        nombre: acumulado.get(p.id, Decimal('0'))
        for nombre, p in propiedades.items()
    }

    cant_llantas = int(props.get('Llantas', 0))
    cant_ejes = int(props.get('Ejes', 0))
    cant_elasticos = int(props.get('Elásticos', 0))

    # Peso por llanta para filtrar propiedades de rodados
    acumulado_rodados = dict(acumulado)
    if cant_llantas > 0 and 'Peso' in propiedades:
        peso_id = propiedades['Peso'].id
        peso_total = acumulado.get(peso_id, Decimal('0'))
        acumulado_rodados[peso_id] = peso_total / cant_llantas

    familias_rodados = Familia.objects.filter(
        implemento=imp_rodados,
    ).order_by('orden')

    resultado = []
    for familia in familias_rodados:
        nombre_lower = familia.nombre.lower()
        if 'llanta' in nombre_lower:
            cantidad = cant_llantas
        elif 'eje' in nombre_lower:
            cantidad = cant_ejes
        elif 'elástico' in nombre_lower or 'elastico' in nombre_lower:
            cantidad = cant_elasticos
        else:
            cantidad = 0

        # Saltear si la cantidad acumulada es 0
        if cantidad <= 0:
            continue

        productos = []
        for prod in Producto.objects.filter(familia=familia):
            compat = check_compatibilidad(prod.id, seleccionados_ids)
            if compat == 'NO':
                continue
            if check_propiedades(prod.id, acumulado_rodados):
                productos.append(prod)

        resultado.append({
            'familia': familia,
            'cantidad': cantidad,
            'productos': productos,
        })

    return resultado


def calcular_bonificaciones(subtotal_bruto, bonif_cliente_pct, bonif_pago_pct):
    """
    Calcula bonificaciones en cascada: primero tipo cliente sobre el bruto,
    luego forma de pago sobre el resultado.
    """
    subtotal_bruto = Decimal(str(subtotal_bruto))
    bonif_cliente_pct = Decimal(str(bonif_cliente_pct))
    bonif_pago_pct = Decimal(str(bonif_pago_pct))

    # Cascada: cliente primero
    bonif_cliente_monto = (subtotal_bruto * bonif_cliente_pct / 100).quantize(Decimal('0.01'))
    subtotal_post_cliente = subtotal_bruto - bonif_cliente_monto

    # Luego forma de pago sobre el resultado
    bonif_pago_monto = (subtotal_post_cliente * bonif_pago_pct / 100).quantize(Decimal('0.01'))
    subtotal_neto = subtotal_post_cliente - bonif_pago_monto

    return {
        'bonif_cliente_pct': bonif_cliente_pct,
        'bonif_cliente_monto': bonif_cliente_monto,
        'bonif_pago_pct': bonif_pago_pct,
        'bonif_pago_monto': bonif_pago_monto,
        'subtotal_neto': subtotal_neto,
    }


def calcular_iva(items, subtotal_bruto, subtotal_neto):
    """
    Calcula IVA desglosado por alícuota, aplicando la proporción de
    bonificaciones a cada grupo.

    Args:
        items: lista de dicts con 'precio_linea' y 'iva_porcentaje'
        subtotal_bruto: Decimal
        subtotal_neto: Decimal (post bonificaciones)

    Returns:
        dict con desglose por alícuota e iva_total
    """
    subtotal_bruto = Decimal(str(subtotal_bruto))
    subtotal_neto = Decimal(str(subtotal_neto))

    if subtotal_bruto == 0:
        return {
            'desglose': {},
            'iva_total': Decimal('0'),
        }

    # Proporción de descuento aplicada
    proporcion = subtotal_neto / subtotal_bruto

    # Agrupar por alícuota
    por_alicuota = defaultdict(Decimal)
    for item in items:
        alicuota = Decimal(str(item['iva_porcentaje']))
        precio_linea = Decimal(str(item['precio_linea']))
        por_alicuota[alicuota] += precio_linea

    desglose = {}
    iva_total = Decimal('0')

    for alicuota, base_bruta in por_alicuota.items():
        base_gravada = (base_bruta * proporcion).quantize(Decimal('0.01'))
        iva_monto = (base_gravada * alicuota / 100).quantize(Decimal('0.01'))
        desglose[alicuota] = {
            'base': base_gravada,
            'monto': iva_monto,
        }
        iva_total += iva_monto

    return {
        'desglose': desglose,
        'iva_total': iva_total,
    }


def calcular_comision(subtotal_neto, bonif_cliente_real, bonif_pago_real,
                       bonif_cliente_default, bonif_pago_default,
                       usuario_bonif_max, usuario_comision_pct,
                       comision_impacto_bonif):
    """
    Calcula la comisión del vendedor ajustada por bonificación extra.

    bonif_extra_usada = (real - default) para cada barra
    porcentaje_uso = extra_usada / usuario_bonif_max
    reduccion = porcentaje_uso × comision_impacto_bonif
    comision_efectiva = usuario_comision_pct × (1 - reduccion)
    """
    usuario_bonif_max = Decimal(str(usuario_bonif_max))
    usuario_comision_pct = Decimal(str(usuario_comision_pct))
    comision_impacto_bonif = Decimal(str(comision_impacto_bonif))

    bonif_extra_cliente = max(Decimal('0'), Decimal(str(bonif_cliente_real)) - Decimal(str(bonif_cliente_default)))
    bonif_extra_pago = max(Decimal('0'), Decimal(str(bonif_pago_real)) - Decimal(str(bonif_pago_default)))
    bonif_extra_usada = bonif_extra_cliente + bonif_extra_pago

    if usuario_bonif_max > 0:
        porcentaje_uso = min(bonif_extra_usada / usuario_bonif_max, Decimal('1'))
    else:
        porcentaje_uso = Decimal('0')

    reduccion = porcentaje_uso * comision_impacto_bonif
    comision_efectiva = (usuario_comision_pct * (1 - reduccion)).quantize(Decimal('0.01'))
    comision_monto = (Decimal(str(subtotal_neto)) * comision_efectiva / 100).quantize(Decimal('0.01'))

    return {
        'comision_porcentaje_efectivo': comision_efectiva,
        'comision_monto': comision_monto,
        'bonif_extra_usada': bonif_extra_usada,
    }


def calcular_totales(items, bonif_cliente_pct, bonif_pago_pct,
                      bonif_cliente_default=None, bonif_pago_default=None,
                      usuario_bonif_max=None, usuario_comision_pct=None,
                      comision_impacto_bonif=None):
    """
    Orquesta el cálculo completo: subtotal bruto, bonificaciones en cascada,
    IVA desglosado por alícuota, precio total, y comisión.
    """
    subtotal_bruto = sum(
        Decimal(str(item['precio_linea'])) for item in items
    )

    bonif = calcular_bonificaciones(
        subtotal_bruto, bonif_cliente_pct, bonif_pago_pct,
    )

    iva = calcular_iva(items, subtotal_bruto, bonif['subtotal_neto'])

    iva_105 = iva['desglose'].get(Decimal('10.50'), {'base': Decimal('0'), 'monto': Decimal('0')})
    iva_21 = iva['desglose'].get(Decimal('21.00'), {'base': Decimal('0'), 'monto': Decimal('0')})

    precio_total = bonif['subtotal_neto'] + iva['iva_total']

    # Comisión
    comision = {'comision_porcentaje_efectivo': Decimal('0'), 'comision_monto': Decimal('0')}
    if usuario_comision_pct and usuario_comision_pct > 0:
        comision = calcular_comision(
            bonif['subtotal_neto'],
            bonif['bonif_cliente_pct'], bonif['bonif_pago_pct'],
            bonif_cliente_default or Decimal('0'),
            bonif_pago_default or Decimal('0'),
            usuario_bonif_max or Decimal('0'),
            usuario_comision_pct,
            comision_impacto_bonif or Decimal('0.60'),
        )

    return {
        'subtotal_bruto': subtotal_bruto,
        'bonif_cliente_pct': bonif['bonif_cliente_pct'],
        'bonif_cliente_monto': bonif['bonif_cliente_monto'],
        'bonif_pago_pct': bonif['bonif_pago_pct'],
        'bonif_pago_monto': bonif['bonif_pago_monto'],
        'subtotal_neto': bonif['subtotal_neto'],
        'iva_105_base': iva_105['base'],
        'iva_105_monto': iva_105['monto'],
        'iva_21_base': iva_21['base'],
        'iva_21_monto': iva_21['monto'],
        'iva_total': iva['iva_total'],
        'precio_total': precio_total,
        'comision_porcentaje_efectivo': comision['comision_porcentaje_efectivo'],
        'comision_monto': comision['comision_monto'],
    }
