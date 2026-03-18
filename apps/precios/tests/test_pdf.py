"""Tests de generación de PDF."""

import pytest
from decimal import Decimal

try:
    from weasyprint import HTML  # noqa: F401
    HAS_WEASYPRINT = True
except (ImportError, OSError):
    HAS_WEASYPRINT = False

pytestmark = pytest.mark.skipif(not HAS_WEASYPRINT, reason='WeasyPrint no disponible (falta GTK/GLib)')

from django.test import Client as TestClient

from apps.accounts.tests.factories import UserFactory
from apps.catalogo.tests.factories import (
    FamiliaFactory,
    ImplementoFactory,
    ProductoFactory,
)
from apps.clientes.tests.factories import ClienteFactory, FormaPagoFactory, TipoClienteFactory
from apps.cotizaciones.models import Cotizacion, CotizacionItem
from apps.precios.tests.factories import ListaPrecioFactory, PrecioProductoFactory
from apps.tenants.tests.factories import TenantFactory


@pytest.fixture
def pdf_setup():
    tenant = TenantFactory()
    user = UserFactory(tenant=tenant, is_staff=True)
    tipo = TipoClienteFactory(tenant=tenant)
    cliente = ClienteFactory(tenant=tenant, tipo_cliente=tipo)
    imp = ImplementoFactory(tenant=tenant)
    fam = FamiliaFactory(tenant=tenant, implemento=imp, orden=1)
    prod = ProductoFactory(tenant=tenant, implemento=imp, familia=fam)
    lista = ListaPrecioFactory(tenant=tenant, estado='vigente', creada_por=user)
    PrecioProductoFactory(lista=lista, producto=prod, precio=Decimal('10000'))
    forma_pago = FormaPagoFactory(tenant=tenant)

    cot = Cotizacion.objects.create(
        tenant=tenant, implemento=imp, vendedor=user,
        cliente=cliente, lista=lista, forma_pago=forma_pago,
        numero='COT-TEST-PDF', subtotal_bruto=Decimal('10000'),
        precio_total=Decimal('12100'),
    )
    CotizacionItem.objects.create(
        cotizacion=cot, producto=prod, familia=fam,
        cantidad=1, precio_unitario=Decimal('10000'),
        precio_linea=Decimal('10000'), iva_porcentaje=Decimal('21'),
    )

    client = TestClient()
    client.force_login(user)
    return {'cot': cot, 'client': client}


@pytest.mark.django_db
class TestPDFCotizacion:
    def test_pdf_se_genera(self, pdf_setup):
        s = pdf_setup
        response = s['client'].get(f'/{s["cot"].id}/pdf/')
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/pdf'
        assert len(response.content) > 100

    def test_pdf_tiene_numero_cotizacion(self, pdf_setup):
        s = pdf_setup
        response = s['client'].get(f'/{s["cot"].id}/pdf/')
        assert response['Content-Disposition'] == 'inline; filename="COT-TEST-PDF.pdf"'


@pytest.mark.django_db
class TestPanelListas:
    def test_panel_listas_accesible(self, pdf_setup):
        response = pdf_setup['client'].get('/precios/listas/')
        assert response.status_code == 200

    def test_crear_lista_post(self, pdf_setup):
        response = pdf_setup['client'].post('/precios/listas/crear/', {
            'ajuste_pct': '5',
            'nombre': 'Test Lista',
        })
        assert response.status_code == 302
