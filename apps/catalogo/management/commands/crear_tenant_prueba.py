"""Management command para crear tenant de prueba con datos completos."""

from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.catalogo.models import (
    Compatibilidad,
    Familia,
    Implemento,
    Producto,
    ProductoPropiedad,
    Propiedad,
)
from apps.clientes.models import FormaPago, TipoCliente
from apps.precios.models import ListaPrecio, PrecioProducto
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = 'Crear tenant de prueba con datos completos'

    @transaction.atomic
    def handle(self, *args, **options):
        tenant, created = Tenant.objects.get_or_create(
            slug='test',
            defaults={
                'nombre': 'Metalúrgica Test',
                'moneda': 'ARS',
                'comision_impacto_bonif': Decimal('0.60'),
                'mostrar_comisiones': True,
            },
        )
        if not created:
            self.stdout.write('Tenant ya existe, salteando.')
            return

        self.stdout.write(f'Tenant: {tenant.nombre}')

        # Usuarios
        dueno = User.objects.create_user(
            email='dueno@test.com', password='test123',
            nombre='Carlos Dueño', tenant=tenant, rol='dueno',
            is_staff=True, bonif_max_porcentaje=Decimal('20'),
            comision_porcentaje=Decimal('3'),
        )
        vendedor = User.objects.create_user(
            email='vendedor@test.com', password='test123',
            nombre='María Vendedora', tenant=tenant, rol='vendedor',
            requiere_validacion=True, bonif_max_porcentaje=Decimal('10'),
            comision_porcentaje=Decimal('5'),
        )
        self.stdout.write(f'  Dueno: {dueno.email} / test123')
        self.stdout.write(f'  Vendedor: {vendedor.email} / test123')

        # Propiedades
        prop_long = Propiedad.objects.create(tenant=tenant, nombre='Longitud', unidad='mts', agregacion='SUM')
        prop_peso = Propiedad.objects.create(tenant=tenant, nombre='Peso', unidad='kg', agregacion='SUM')
        prop_alt = Propiedad.objects.create(tenant=tenant, nombre='Altura', unidad='mm', agregacion='MAX')
        prop_llantas = Propiedad.objects.create(tenant=tenant, nombre='Llantas', unidad='u', agregacion='MAX')
        prop_ejes = Propiedad.objects.create(tenant=tenant, nombre='Ejes', unidad='u', agregacion='MAX')
        self.stdout.write('  5 propiedades')

        # Implemento 1: Tolvas
        imp1 = Implemento.objects.create(tenant=tenant, nombre='Tolvas')
        fam1_1 = Familia.objects.create(tenant=tenant, implemento=imp1, nombre='Cuerpo Tolva', orden=1, tipo_seleccion='O', obligatoria='SI')
        fam1_2 = Familia.objects.create(tenant=tenant, implemento=imp1, nombre='Rodado', orden=2, tipo_seleccion='O', obligatoria='SI')
        fam1_3 = Familia.objects.create(tenant=tenant, implemento=imp1, nombre='Accesorios', orden=3, tipo_seleccion='Y', obligatoria='NO')

        tolvas = []
        for i, (nombre, precio, long, peso) in enumerate([
            ('Tolva 18 TN', 15000000, '4.5', '3200'),
            ('Tolva 20 TN', 17500000, '5.0', '3600'),
            ('Tolva 23 TN', 20000000, '5.5', '4100'),
            ('Tolva 26 TN', 23000000, '6.0', '4500'),
            ('Tolva 28 TN', 25500000, '6.5', '5000'),
        ], 1):
            p = Producto.objects.create(tenant=tenant, implemento=imp1, familia=fam1_1, nombre=nombre, orden=i)
            ProductoPropiedad.objects.create(producto=p, propiedad=prop_long, tipo='Exacto', valor=Decimal(long))
            ProductoPropiedad.objects.create(producto=p, propiedad=prop_peso, tipo='Exacto', valor=Decimal(peso))
            tolvas.append((p, precio))

        rodados = []
        for nombre, precio in [('Rodado 22.5"', 950000), ('Rodado 24.5"', 1100000)]:
            p = Producto.objects.create(tenant=tenant, implemento=imp1, familia=fam1_2, nombre=nombre, orden=1)
            rodados.append((p, precio))

        accesorios1 = []
        for nombre, precio in [('Cajon herramientas', 350000), ('Deposito agua 200L', 420000), ('Escalera abatible', 280000)]:
            p = Producto.objects.create(tenant=tenant, implemento=imp1, familia=fam1_3, nombre=nombre, orden=1)
            accesorios1.append((p, precio))

        # Implemento 2: Semilleros
        imp2 = Implemento.objects.create(tenant=tenant, nombre='Semilleros')
        fam2_1 = Familia.objects.create(tenant=tenant, implemento=imp2, nombre='Modelo', orden=1, tipo_seleccion='O', obligatoria='SI')
        fam2_2 = Familia.objects.create(tenant=tenant, implemento=imp2, nombre='Capacidad Extra', orden=2, tipo_seleccion='Y', obligatoria='NO')
        fam2_3 = Familia.objects.create(tenant=tenant, implemento=imp2, nombre='Opcionales', orden=3, tipo_seleccion='Y', obligatoria='NO')

        semilleros = []
        for i, (nombre, precio) in enumerate([
            ('Semillero SM-100', 8000000),
            ('Semillero SM-200', 11500000),
            ('Semillero SM-300', 14000000),
            ('Semillero SM-400', 17500000),
        ], 1):
            p = Producto.objects.create(tenant=tenant, implemento=imp2, familia=fam2_1, nombre=nombre, orden=i)
            semilleros.append((p, precio))

        extras2 = []
        for nombre, precio in [('Tolva extra 500kg', 1200000), ('Tolva extra 1000kg', 1800000)]:
            p = Producto.objects.create(tenant=tenant, implemento=imp2, familia=fam2_2, nombre=nombre, orden=1)
            extras2.append((p, precio))

        opcionales2 = []
        for nombre, precio in [('Lona cobertura', 450000), ('Escalera acceso', 320000), ('Monitor siembra', 2500000)]:
            p = Producto.objects.create(tenant=tenant, implemento=imp2, familia=fam2_3, nombre=nombre, orden=1)
            opcionales2.append((p, precio))

        self.stdout.write(f'  2 implementos, 6 familias, {Producto.objects.filter(tenant=tenant).count()} productos')

        # Lista de precios
        lista = ListaPrecio.objects.create(
            tenant=tenant, numero=1, nombre='Lista Inicial',
            estado='vigente', creada_por=dueno,
        )
        todos_productos = tolvas + rodados + accesorios1 + semilleros + extras2 + opcionales2
        for prod, precio in todos_productos:
            PrecioProducto.objects.create(lista=lista, producto=prod, precio=Decimal(str(precio)))
        self.stdout.write(f'  Lista #1 con {len(todos_productos)} precios')

        # Tipo cliente y formas de pago
        TipoCliente.objects.create(tenant=tenant, nombre='Concesionario', bonificacion_default=Decimal('15'))
        FormaPago.objects.create(tenant=tenant, nombre='Contado', bonificacion_porcentaje=Decimal('10'))
        FormaPago.objects.create(tenant=tenant, nombre='Financiado', bonificacion_porcentaje=Decimal('0'))
        self.stdout.write('  1 tipo cliente, 2 formas pago')

        self.stdout.write(self.style.SUCCESS('Tenant de prueba creado exitosamente.'))
