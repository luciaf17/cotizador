# CLAUDE.md — Instrucciones para Claude Code

## Proyecto
Cotizador multicliente para Metalúrgica Ceibo (y futuros clientes). Configurador de implementos agrícolas por pasos con validación dimensional, bonificaciones en cascada, IVA por producto, y generación de PDF.

## Stack
- **Python 3.12+**
- **Django 5.1+**
- **PostgreSQL 16** (local dev y Railway prod)
- **HTMX 2.x** para interactividad sin SPA
- **Tailwind CSS 3.x** via CDN en dev, build en prod
- **WeasyPrint** para generación de PDF
- **Railway** para deploy

## Estructura del Proyecto

```
cotizador/
├── CLAUDE.md              ← Este archivo
├── SPEC.md                ← Lógica de negocio completa (LEER PRIMERO)
├── manage.py
├── config/                ← Settings del proyecto Django
│   ├── settings/
│   │   ├── base.py
│   │   ├── local.py
│   │   └── production.py
│   ├── urls.py
│   └── wsgi.py
├── apps/
│   ├── accounts/          ← User custom, auth, login
│   │   ├── models.py      ← User con rol y requiere_validacion
│   │   ├── admin.py
│   │   └── ...
│   ├── tenants/           ← Tenant, middleware multi-tenant
│   │   ├── models.py
│   │   ├── middleware.py   ← TenantMiddleware
│   │   └── ...
│   ├── catalogo/          ← Implementos, Familias, Productos, Propiedades, Compatibilidades
│   │   ├── models.py
│   │   ├── admin.py
│   │   └── ...
│   ├── precios/           ← ListasPrecios, PreciosProductos, Prearmados, EstructuraPrearmados
│   │   ├── models.py
│   │   ├── admin.py
│   │   └── ...
│   ├── clientes/          ← TiposCliente, Clientes, FormasPago
│   │   ├── models.py
│   │   ├── admin.py
│   │   └── ...
│   └── cotizaciones/      ← Cotizaciones, CotizacionItems, CotizacionDimensiones, motor de validación
│       ├── models.py
│       ├── admin.py
│       ├── services.py     ← Motor de cotización (filtros, cálculos)
│       └── ...
├── templates/
│   └── base.html
├── static/
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
└── scripts/
    └── import_excel.py    ← Fase 2: importar datos desde Excel
```

## Convenciones

### Django
- **User custom** con `AbstractUser`, email como username (`USERNAME_FIELD = 'email'`). Definir ANTES de la primera migration.
- **Multi-tenant**: Todas las tablas (excepto User) tienen `tenant_id`. Usar un `TenantManager` que filtre automáticamente por `request.tenant`.
- **Soft delete**: Campo `activo` en vez de borrar. Usar manager que filtre `activo=True` por defecto.
- **Timestamps**: `created_at` y `updated_at` en todos los modelos (abstract base model).
- Nombres de modelos en **español** (Implemento, Familia, Producto, etc.) — consistente con el negocio.
- Nombres de tablas en **snake_case** plural: `class Producto(models.Model): class Meta: db_table = 'productos'`

### Modelo Base
```python
class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class TenantModel(TimeStampedModel):
    tenant = models.ForeignKey('tenants.Tenant', on_delete=models.CASCADE)
    
    class Meta:
        abstract = True
```

### Enums
Usar `models.TextChoices` para enums:
```python
class TipoSeleccion(models.TextChoices):
    UNO = 'O', 'Uno (radio)'
    VARIOS = 'Y', 'Varios (checkbox)'
```

### Admin
Registrar todos los modelos en admin.py con:
- `list_display` con los campos principales
- `list_filter` por tenant, estado, tipo
- `search_fields` por nombre
- `raw_id_fields` para FKs pesadas (productos, etc.)

### Base de datos
- PostgreSQL local: `cotizador_db` user `cotizador_user`
- Usar `decimal` (no float) para todos los montos y porcentajes
- `DecimalField(max_digits=14, decimal_places=2)` para precios
- `DecimalField(max_digits=5, decimal_places=2)` para porcentajes
- `unique_together` donde aplique: `(lista, producto)` en precios_productos

### Tests

Usar **pytest-django** + **factory_boy** + **faker**.

**Estructura de tests:**
```
apps/
├── catalogo/
│   └── tests/
│       ├── __init__.py
│       ├── factories.py      ← Factories de Implemento, Familia, Producto, etc.
│       ├── test_models.py    ← Validaciones de modelo, constraints, herencia
│       └── test_services.py  ← Motor de cotización, filtros, cálculos
├── cotizaciones/
│   └── tests/
│       ├── factories.py
│       ├── test_models.py
│       ├── test_services.py  ← Bonificaciones cascada, IVA por alícuota
│       └── test_views.py     ← Flujo HTMX, permisos por rol
```

**Convenciones de tests:**
- Nombre: `test_<que_testea>_<escenario>_<resultado_esperado>`. Ej: `test_check_compatibilidad_producto_vetado_no_aparece`
- Cada model factory hereda de `factory.django.DjangoModelFactory`
- Usar `@pytest.mark.django_db` para tests que tocan DB
- Mínimo 1 test por regla de negocio crítica (ver SPEC.md sección 11)
- Tests del motor deben cubrir: producto vetado, producto forzado, filtro dimensional (pasa y no pasa), bonificación en cascada, IVA por alícuota, bonif_max como techo

**Ejemplo de factory:**
```python
# apps/catalogo/tests/factories.py
import factory
from apps.tenants.tests.factories import TenantFactory

class ImplementoFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = 'catalogo.Implemento'
    
    tenant = factory.SubFactory(TenantFactory)
    nombre = factory.Faker('word')
    accesorios_tipo = None
    nivel_rodado = None
```

**Ejemplo de test:**
```python
# apps/cotizaciones/tests/test_services.py
import pytest
from decimal import Decimal
from apps.cotizaciones.services import calcular_bonificaciones

@pytest.mark.django_db
def test_bonificacion_cascada_aplica_cliente_primero_luego_pago():
    resultado = calcular_bonificaciones(
        subtotal_bruto=Decimal('10000'),
        bonif_cliente_pct=Decimal('10'),
        bonif_pago_pct=Decimal('5'),
    )
    # Cascada: 10000 - 1000 (10%) = 9000, luego 9000 - 450 (5%) = 8550
    assert resultado['subtotal_neto'] == Decimal('8550')
    assert resultado['bonif_cliente_monto'] == Decimal('1000')
    assert resultado['bonif_pago_monto'] == Decimal('450')
```

**Correr tests:**
```bash
pytest                           # Todos
pytest apps/cotizaciones/        # Solo una app
pytest -k "test_bonificacion"    # Por nombre
pytest --cov=apps --cov-report=html  # Con coverage
```

### Git

**Branches:**
- `main` — producción, siempre deployable
- `develop` — integración, donde se mergean features
- `feature/<nombre>` — una feature o fase. Ej: `feature/fase-1-models`, `feature/motor-cotizacion`
- `fix/<nombre>` — bugfixes

**Commits semánticos** (Conventional Commits):
```
feat: agregar modelo Cotizacion con bonificaciones en cascada
fix: corregir cálculo IVA cuando producto tiene 10.5%
test: agregar tests para check de compatibilidad vetado/forzado
refactor: extraer lógica de dimensiones acumuladas a servicio
docs: actualizar SPEC.md con cambios de Ezequiel
chore: configurar pytest y factory_boy
```

**Flujo por fase:**
```bash
git checkout develop
git checkout -b feature/fase-1-models
# ... trabajar ...
git add .
git commit -m "feat: crear proyecto Django con estructura de apps"
git commit -m "feat: agregar models de las 18 tablas"
git commit -m "feat: registrar todos los models en admin"
git commit -m "test: agregar factories básicas para todos los models"
git push origin feature/fase-1-models
# Crear PR → develop, revisar, mergear
```

**Cada PR debe tener:**
- Tests pasando
- Commits limpios (squash si hay muchos WIP)
- Sin migrations conflictivas

### CI (GitHub Actions)

Crear `.github/workflows/ci.yml` en Fase 1:
```yaml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test_user
          POSTGRES_PASSWORD: test_pass
        ports: ['5432:5432']
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install -r requirements/local.txt
      - run: pytest --tb=short
        env:
          DATABASE_URL: postgres://test_user:test_pass@localhost:5432/test_db
          DJANGO_SETTINGS_MODULE: config.settings.local
```

## Referencia Rápida del Modelo (18 tablas + estimación)

### Tenant + Auth
- `Tenant`: id(uuid), nombre, slug(uk), bonif_max_porcentaje, moneda, activo
- `User`: id, tenant(fk), email(uk), password, nombre, rol(enum), requiere_validacion(bool), activo

### Clientes
- `TipoCliente`: id, tenant(fk), nombre, bonificacion_default
- `Cliente`: id, tenant(fk), tipo_cliente(fk), nombre, telefono, email, direccion, bonificacion_porcentaje
- `FormaPago`: id, tenant(fk), nombre, bonificacion_porcentaje, activo

### Catálogo
- `Implemento`: id, tenant(fk), nombre, accesorios_tipo, nivel_rodado
- `Familia`: id, tenant(fk), implemento(fk), nombre, orden, tipo_seleccion(O/Y), obligatoria(SI/NO)
- `Producto`: id, tenant(fk), implemento(fk), familia(fk), nombre, cod_comercio, plano, cod_factura, orden, iva_porcentaje
- `Propiedad`: id, tenant(fk), nombre, unidad, agregacion(SUM/MAX)
- `ProductoPropiedad`: id, producto(fk), propiedad(fk), tipo(Exacto/Min/Max), valor, valor_neto, prioridad
- `Compatibilidad`: id, tenant(fk), producto_padre(fk), producto_hijo(fk), tipo(Vetado/Forzado)

### Precios
- `ListaPrecio`: id, tenant(fk), numero, nombre, fecha_creacion, estado(vigente/historica/borrador), ajuste_pct, lista_base(fk self), creada_por(fk user)
- `PrecioProducto`: id, lista(fk), producto(fk), precio, editado_por(fk user) — UQ(lista, producto)
- `Prearmado`: id, tenant(fk), implemento(fk), nombre, precio_referencia
- `EstructuraPrearmado`: id, prearmado(fk), producto(fk), cantidad

### Cotizaciones
- `Cotizacion`: id, tenant(fk), implemento(fk), vendedor(fk user), cliente(fk), lista(fk), forma_pago(fk), numero(uk), subtotal_bruto, bonif_cliente_pct/monto, bonif_pago_pct/monto, subtotal_neto, iva_105_base/monto, iva_21_base/monto, iva_total, precio_total, fecha_entrega, estado(borrador/aprobada/confirmada), confirmada_por(fk user), pdf_url, notas
- `CotizacionItem`: id, cotizacion(fk), producto(fk), familia(fk), cantidad, precio_unitario, precio_linea, iva_porcentaje
- `CotizacionDimension`: id, cotizacion(fk), propiedad(fk), valor_acumulado

## Fases de Desarrollo (Roadmap completo)

### Fase 0 — Setup inicial del entorno
**Hacer ANTES de cualquier otra fase.**

Checklist:
1. Crear entorno virtual: `python -m venv venv`
2. Activar: `source venv/bin/activate` (Linux/Mac) o `venv\Scripts\activate` (Windows)
3. Crear `.gitignore` con:
```
# Python
venv/
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.eggs/

# Django
db.sqlite3
media/
staticfiles/
*.log

# Entorno
.env
.env.local

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Coverage
htmlcov/
.coverage
.pytest_cache/
```
4. Crear `.env.example` con:
```
DEBUG=True
SECRET_KEY=cambiar-esto-en-produccion
DATABASE_URL=postgres://cotizador_user:password@localhost:5432/cotizador_db
ALLOWED_HOSTS=localhost,127.0.0.1
```
5. Crear `.env` copiando `.env.example` y completando con valores locales
6. Instalar pip-tools: `pip install pip-tools`
7. Crear `requirements/base.txt`:
```
Django>=5.1,<5.2
psycopg2-binary>=2.9
python-decouple>=3.8
dj-database-url>=2.1
```
8. Crear `requirements/local.txt`:
```
-r base.txt
pytest>=8.0
pytest-django>=4.8
factory-boy>=3.3
faker>=24.0
pytest-cov>=5.0
django-debug-toolbar>=4.3
```
9. Crear `requirements/production.txt`:
```
-r base.txt
gunicorn>=22.0
whitenoise>=6.6
weasyprint>=62.0
```
10. Instalar dependencias: `pip install -r requirements/local.txt`
11. Crear DB PostgreSQL local:
```bash
createdb cotizador_db
createuser cotizador_user
# Si necesita password:
psql -c "ALTER USER cotizador_user WITH PASSWORD 'password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE cotizador_db TO cotizador_user;"
```

**Commits esperados:**
```
chore: setup entorno virtual y .gitignore
chore: agregar .env.example y requirements
```

---

### Fase 1 — Scaffolding + Models + Admin
**Branch:** `feature/fase-1-models`

Checklist:
1. `django-admin startproject config .`
2. Crear estructura de apps: `accounts`, `tenants`, `catalogo`, `precios`, `clientes`, `cotizaciones`
3. Settings split (base/local/production) con PostgreSQL
4. `requirements/base.txt` con Django, psycopg2-binary, pytest-django, factory-boy, faker
5. Modelo User custom en accounts (ANTES de primera migration)
6. Modelos abstractos base: `TimeStampedModel`, `TenantModel`
7. Todos los models de las 18 tablas según la referencia de arriba
8. Migrations
9. Admin registrado para todas las tablas con list_display, list_filter, search_fields
10. Factories básicas para todos los models en `tests/factories.py` de cada app
11. Tests básicos: crear instancia de cada modelo, verificar constraints (unique, FK)
12. `.github/workflows/ci.yml` con PostgreSQL service
13. `pytest.ini` o `pyproject.toml` con config de pytest
14. Crear superuser
15. Verificar que se puede crear Tenant → User → Implemento → Familia → Producto desde admin

**Commits esperados:**
```
chore: setup proyecto Django con settings split y PostgreSQL
feat: agregar modelo User custom con rol y requiere_validacion
feat: agregar models de tenant, catalogo y propiedades
feat: agregar models de clientes, tipos_cliente y formas_pago
feat: agregar models de listas_precios y precios_productos
feat: agregar models de prearmados y estructura
feat: agregar models de cotizaciones, items y dimensiones
feat: registrar todos los models en admin
test: agregar factories y tests básicos de models
chore: configurar CI con GitHub Actions
```

---

### Fase 2 — Importación datos Excel Ceibo
**Branch:** `feature/fase-2-import-excel`

Checklist:
1. Copiar `DBA_Cotizador_Ceibo.xlsx` a `scripts/data/`
2. Crear `scripts/import_excel.py` como management command de Django (`python manage.py import_ceibo`)
3. Crear el Tenant "Ceibo" automáticamente
4. Importar Implementos (hoja Implementos)
5. Importar Familias (hoja Familias) con orden, tipo_seleccion, obligatoria
6. Importar Productos (hoja Productos) con familia_id, implemento_id
7. Importar Propiedades (hoja Propiedades)
8. Importar ProductoPropiedades (hoja Prod_Prop) con tipo Exacto/Min/Max y valor_neto
9. Importar Compatibilidades (hoja Compat_Vetado)
10. Importar Prearmados (hoja Prearmados)
11. Importar EstructuraPrearmados (hoja Estructuras)
12. Crear ListaPrecio #81 con estado='vigente'
13. Importar PrecioProductos desde hoja Precio_Productos vinculados a Lista #81
14. Tests: verificar conteos post-import, verificar que relaciones FK son correctas
15. Documentar qué columnas del Excel mapean a qué campos

**Commits esperados:**
```
feat: crear management command import_ceibo
feat: importar implementos, familias y productos desde Excel
feat: importar propiedades y producto_propiedades
feat: importar compatibilidades y prearmados con estructura
feat: crear lista de precios #81 con precios del Excel
test: verificar integridad de datos importados
docs: documentar mapeo Excel → DB
```

---

### Fase 3 — Motor de cotización (backend)
**Branch:** `feature/fase-3-motor-cotizacion`

Checklist:
1. Crear `apps/cotizaciones/services.py` con clase `MotorCotizacion`
2. Servicio de dimensiones acumuladas: dado lista de items seleccionados, calcular SUM/MAX por propiedad
3. Servicio check_compatibilidad: dado producto candidato + seleccionados, retornar SI/NO/None
4. Servicio check_propiedades: dado producto candidato + dimensiones acumuladas, retornar True/False
5. Servicio get_productos_disponibles: dado implemento + orden actual + seleccionados, retornar lista filtrada
6. Servicio de rodados automáticos: detectar accesorios_tipo='Rodados', inyectar familias, calcular cantidades desde propiedades del chasis
7. Servicio calcular_bonificaciones: cascada tipo_cliente → forma_pago, validar contra bonif_max
8. Servicio calcular_iva: agrupar items por alícuota, calcular base gravada proporcional post-bonificaciones, calcular IVA por alícuota
9. Servicio calcular_totales: orquestar todo → subtotal_bruto, bonificaciones, subtotal_neto, IVA desglosado, total
10. Tests exhaustivos para cada servicio (mínimo 3-5 casos por servicio)

**Tests críticos:**
```
test_producto_vetado_no_aparece_en_disponibles
test_producto_forzado_aparece_en_disponibles
test_chasis_fuera_de_rango_longitud_no_aparece
test_chasis_dentro_de_rango_longitud_aparece
test_dimensiones_sum_longitud_acumula_correctamente
test_dimensiones_max_altura_toma_maximo
test_rodados_se_inyectan_con_cantidades_del_chasis
test_centro_chasis_filtra_llantas_compatibles
test_bonificacion_cascada_cliente_primero_luego_pago
test_bonificacion_no_excede_bonif_max
test_iva_desglosa_por_alicuota_105_y_21
test_iva_proporcional_post_bonificacion
test_total_es_neto_mas_iva
```

**Commits esperados:**
```
feat: agregar servicio de dimensiones acumuladas SUM/MAX
feat: agregar check de compatibilidad vetado/forzado
feat: agregar check de propiedades Min/Max
feat: agregar servicio de productos disponibles por paso
feat: agregar lógica de rodados automáticos
feat: agregar cálculo de bonificaciones en cascada
feat: agregar cálculo de IVA por alícuota
feat: agregar orquestador de totales
test: agregar tests completos del motor de cotización
```

---

### Fase 4 — UI del cotizador (HTMX + Tailwind)
**Branch:** `feature/fase-4-ui-cotizador`

Checklist:
1. Template base con Tailwind CSS (CDN en dev), navbar, layout responsive
2. Vista de selección/carga de cliente (búsqueda + form inline para nuevo)
3. Vista de selección de implemento (cards o lista)
4. Vista step-by-step: partial HTMX que se swapea en cada paso
5. Paso tipo O: radio buttons agrupados por familia (tabs o acordeones si mismo orden), "Ninguno" por defecto si obligatoria=NO
6. Paso tipo Y: checkboxes, nada marcado por defecto si obligatoria=NO
7. Mostrar dimensiones acumuladas en vivo (sidebar o barra superior)
8. Paso de bonificaciones: barra deslizante tipo cliente + selector forma de pago + barra deslizante forma pago. Tope visual = bonif_max
9. Desglose de IVA por alícuota en vivo
10. Resumen final con todos los totales
11. Input fecha de entrega
12. Botón "Aprobar" (genera PDF, pasa a aprobada)
13. Tests de views: permisos por rol, flujo completo, validaciones

**Commits esperados:**
```
feat: agregar template base con Tailwind y navbar
feat: agregar vista selección de cliente con HTMX
feat: agregar vista selección de implemento
feat: agregar flujo step-by-step con partials HTMX
feat: agregar paso tipo O con radio buttons y agrupación por familia
feat: agregar paso tipo Y con checkboxes
feat: agregar barras de bonificación con tope bonif_max
feat: agregar desglose IVA por alícuota en vivo
feat: agregar resumen final y aprobación
test: agregar tests de views y flujo completo
```

---

### Fase 5 — PDF + Listas de precios
**Branch:** `feature/fase-5-pdf-precios`

Checklist:
1. Instalar WeasyPrint
2. Template HTML para PDF cotización (logo, datos tenant/cliente/vendedor, productos con cantidad SIN precio unitario, bonificaciones, IVA desglosado, total, fecha entrega, notas)
3. Vista de generación de PDF: renderizar template → WeasyPrint → guardar archivo → actualizar pdf_url
4. Vista de descarga de PDF
5. Panel de listas de precios: ver lista vigente, crear nueva con % ajuste
6. Servicio crear_nueva_lista: generar precios con CEILING, estado borrador
7. Vista edición de precios individuales en lista borrador
8. Botón activar lista (anterior → historica, nueva → vigente)
9. Vista historial de listas
10. Template HTML para PDF lista prearmados (nombre + precio calculado desde lista vigente)
11. Botón generar PDF prearmados para concesionarios
12. Tests: PDF se genera, listas se crean correctamente, precios se calculan con CEILING

**Commits esperados:**
```
feat: agregar generación de PDF cotización con WeasyPrint
feat: agregar panel de listas de precios
feat: agregar servicio crear nueva lista con % ajuste
feat: agregar edición de precios individuales en borrador
feat: agregar activación de lista y historial
feat: agregar PDF de lista prearmados para concesionarios
test: agregar tests de generación PDF y listas de precios
```

---

### Fase 6 — Roles, permisos y aprobación
**Branch:** `feature/fase-6-permisos`

Checklist:
1. TenantMiddleware: inyectar tenant en request, filtrar querysets automáticamente
2. Decoradores/mixins de permisos: `@rol_requerido('dueno')`, `@mismo_tenant`
3. Login/logout views con template
4. Visibilidad de cotizaciones: vendedor ve solo las suyas, dueño ve todas
5. Flujo de aprobación: vendedor con requiere_validacion=true → cotización queda en "aprobada" → dueño confirma → "confirmada"
6. Vista de "cotizaciones pendientes de confirmación" para el dueño
7. Botón confirmar cotización (registrar confirmada_por y confirmada_at)
8. Vendedor sin requiere_validacion → puede confirmar directamente
9. Tests: permisos por rol, vendedor no ve cotizaciones ajenas, flujo aprobación completo

**Commits esperados:**
```
feat: agregar TenantMiddleware y filtrado automático
feat: agregar decoradores de permisos por rol
feat: agregar login/logout con templates
feat: agregar visibilidad de cotizaciones por rol
feat: agregar flujo de aprobación y confirmación
test: agregar tests de permisos y flujo de aprobación
```

---

### Fase 7 — ABM panels del Dueño
**Branch:** `feature/fase-7-abm-panels`

Checklist:
1. Dashboard del dueño con accesos rápidos
2. CRUD Implementos (lista + crear/editar/desactivar)
3. CRUD Familias con árbol visual de órdenes del implemento, herencia de tipo_seleccion al elegir orden existente
4. CRUD Productos
5. CRUD Propiedades y ProductoPropiedades (inline en producto)
6. CRUD Compatibilidades (selección de producto padre/hijo + tipo)
7. CRUD Tipos de Cliente y Formas de Pago
8. Panel de edición de precios (tabla editable con búsqueda)
9. Configuración bonif_max del tenant
10. Gestión de usuarios: crear/editar/desactivar vendedores, toggle requiere_validacion
11. Historial de cotizaciones con filtros (fecha, vendedor, implemento, estado, cliente)
12. Reportes básicos sobre cotizaciones confirmadas
13. Tests de cada CRUD y permisos

**Commits esperados:**
```
feat: agregar dashboard del dueño
feat: agregar CRUD implementos y familias con árbol de órdenes
feat: agregar CRUD productos con propiedades inline
feat: agregar CRUD compatibilidades
feat: agregar CRUD tipos cliente y formas de pago
feat: agregar panel de edición de precios
feat: agregar gestión de usuarios
feat: agregar historial de cotizaciones con filtros
feat: agregar reportes básicos
test: agregar tests de ABM y permisos
```

---

### Fase 8 — Deploy + CI + Cierre
**Branch:** `feature/fase-8-deploy`

Checklist:
1. Configurar settings/production.py (ALLOWED_HOSTS, CSRF, STATIC, etc.)
2. Procfile o railway.toml para Railway
3. PostgreSQL en Railway
4. Variables de entorno en Railway (DATABASE_URL, SECRET_KEY, DEBUG=False)
5. Collectstatic + WhiteNoise para archivos estáticos
6. Dominio custom (si aplica)
7. Migrar DB en producción
8. Crear tenant Ceibo + usuario dueño en producción
9. Correr import_ceibo en producción
10. Smoke test en producción: crear cotización completa, generar PDF, confirmar
11. README.md con instrucciones de setup local, deploy y uso
12. Tag de versión: `v1.0.0`

**Commits esperados:**
```
chore: configurar settings de producción
chore: agregar Procfile y config Railway
feat: agregar WhiteNoise para static files
docs: agregar README con setup y deploy
chore: tag v1.0.0
```

## Comandos útiles
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Documentación completa
Leer `SPEC.md` para la lógica de negocio completa: flujos, cálculos, reglas de validación, permisos por rol, etc.
