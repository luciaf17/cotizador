# Cotizador

Sistema de cotizacion multicliente para implementos agricolas. Configurador por pasos con validacion dimensional, bonificaciones en cascada, IVA por producto, comisiones y generacion de PDF.

## Stack

- Python 3.12 + Django 5.1
- PostgreSQL 16
- HTMX 2.x + Tailwind CSS (CDN)
- WeasyPrint (PDF)
- Railway (deploy)

## Setup local

```bash
# Clonar
git clone https://github.com/luciaf17/cotizador.git
cd cotizador

# Entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Dependencias
pip install -r requirements/local.txt

# Base de datos
createdb cotizador_db
createuser cotizador_user
psql -c "ALTER USER cotizador_user WITH PASSWORD 'password' CREATEDB;"
psql -c "GRANT ALL PRIVILEGES ON DATABASE cotizador_db TO cotizador_user;"

# Variables de entorno
cp .env.example .env
# Editar .env con tus valores

# Migraciones
python manage.py migrate

# Superusuario
python manage.py createsuperuser

# Importar datos de Ceibo (opcional)
python manage.py import_ceibo

# Tenant de prueba (opcional)
python manage.py crear_tenant_prueba

# Servidor
python manage.py runserver
```

## Tests

```bash
pytest                              # Todos (268 tests)
pytest apps/cotizaciones/           # Solo cotizaciones
pytest apps/tests/test_seguridad.py # Solo seguridad
pytest -k "test_aislamiento"        # Solo multi-tenant
```

## Deploy en Railway

1. Crear proyecto en Railway con PostgreSQL
2. Conectar repositorio GitHub
3. Variables de entorno en Railway:
   ```
   DATABASE_URL=<auto desde PostgreSQL addon>
   SECRET_KEY=<generar con python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())">
   DJANGO_SETTINGS_MODULE=config.settings.production
   ALLOWED_HOSTS=.railway.app
   CSRF_TRUSTED_ORIGINS=https://tu-app.railway.app
   DEBUG=False
   SECURE_SSL_REDIRECT=True
   ```
4. Deploy automatico desde main
5. Post-deploy:
   ```bash
   railway run python manage.py createsuperuser
   railway run python manage.py import_ceibo  # Si aplica
   ```

## Estructura

```
apps/
  accounts/     # User, login, permisos, gestion usuarios
  tenants/      # Tenant multi-cliente, middleware, config
  catalogo/     # Implementos, Familias, Productos, Propiedades
  precios/      # Listas, Precios, Prearmados
  clientes/     # Tipos Cliente, Clientes, Formas Pago
  cotizaciones/ # Motor cotizacion, views, PDF
```

## Usuarios de prueba

### Ceibo (import_ceibo)
- admin@cotizador.com / admin123

### Tenant Test (crear_tenant_prueba)
- dueno@test.com / test123
- vendedor@test.com / test123
