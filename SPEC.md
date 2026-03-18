# Cotizador Ceibo — Documento de Lógica de Negocio y Flujo v3

**Versión:** 3.0  
**Fecha:** Marzo 2026  
**Autor:** AutomatizaLab  
**Stack:** Django + HTMX + Tailwind CSS + PostgreSQL (Railway)  

---

## 1. Visión General

Sistema de configuración de productos complejos por pasos. Un vendedor selecciona un implemento, elige/carga un cliente, y va seleccionando componentes de distintas familias de forma guiada. En cada paso, el sistema filtra dinámicamente qué productos son compatibles según dimensiones acumuladas y reglas de vetado/forzado. Al finalizar se aplican bonificaciones (por tipo de cliente y por forma de pago) en cascada, se calcula IVA por alícuota de cada producto, y se genera un PDF profesional.

Multi-tenant: cada empresa-cliente tiene sus propios datos, usuarios, precios y reglas.

---

## 2. Roles y Autenticación

### 2.1 Login

Email + contraseña (Django AbstractUser).

### 2.2 Roles

| Rol | Descripción |
|-----|-------------|
| **Admin** | AutomatizaLab. Configura tenants, acceso total. Superusuario Django. |
| **Dueño** | Dueño de la empresa. CRUD completo del catálogo. Edita precios. Define bonif_max. Aprueba cotizaciones de vendedores que requieren validación. Gestiona usuarios. |
| **Vendedor** | Cotiza. Ve solo sus cotizaciones. Aplica bonificación dentro del límite. Algunos requieren aprobación del Dueño para confirmar. |

### 2.3 Matriz de Permisos

| Acción | Admin | Dueño | Vendedor |
|--------|-------|-------|----------|
| CRUD Implementos/Familias/Productos | ✅ | ✅ | ❌ |
| CRUD Propiedades/Compatibilidades | ✅ | ✅ | ❌ |
| CRUD Tipos Cliente/Formas Pago | ✅ | ✅ | ❌ |
| Gestión Listas de Precios | ✅ | ✅ | ❌ |
| Editar precios individuales en lista | ✅ | ✅ | ❌ |
| Configurar bonif_max | ✅ | ✅ | ❌ |
| Crear cotización | ✅ | ✅ | ✅ |
| Ver todas las cotizaciones del tenant | ✅ | ✅ | ❌ |
| Ver solo sus cotizaciones | — | — | ✅ |
| Ajustar bonificación (≤ bonif_max) | ✅ | ✅ | ✅ |
| Aprobar cotizaciones (→ confirmada) | ✅ | ✅ | ❌ |
| Generar PDF cotización | ✅ | ✅ | ✅ |
| Generar PDF lista prearmados | ✅ | ✅ | ❌ |
| Gestionar usuarios del tenant | ✅ | ✅ | ❌ |
| Gestionar tenants | ✅ | ❌ | ❌ |

### 2.4 Validación de Cotizaciones

Campo `requiere_validacion` (bool) en users. Si es true, la cotización necesita que el Dueño la **confirme**. Si es false, el vendedor puede confirmar directamente.

Estados de cotización: `borrador` → `aprobada` → `confirmada`
- **borrador**: En proceso de selección de productos.
- **aprobada**: Completa con precio calculado, PDF generado. Lista para confirmar.
- **confirmada**: El Dueño la confirmó (si requiere_validacion=true) o el vendedor la confirmó directamente. Cuenta para reportes.

---

## 3. Jerarquía de Datos (ABM)

### 3.1 Implementos

Categorías principales. Cada implemento agrupa familias.

| ID | Implemento | Accesorios | Nivel Rodado |
|----|-----------|------------|-------------|
| 1 | Elevadores Frontales | — | — |
| 2 | Retroexcavadoras | — | — |
| 3 | Desmalezadoras | Rodados | 1 |
| 4 | Grúas | Rodados | 1 |
| 5 | Niveladoras | Rodados | 1 |
| 6 | Acoplados Rurales | Rodados | 3 |
| 7 | Acoplados Trailer | Rodados | 3 |
| 8 | Acoplados Viñateros | Rodados | 1 |
| 9 | Acoplados Volcadores | Rodados | 2 |
| 10 | Rodados | — | — |

Cuando `accesorios_tipo = 'Rodados'`, al terminar las familias propias se agregan automáticamente las de Rodados (Llantas → Ejes → Elásticos). `nivel_rodado` indica cuántos sets.

### 3.2 Familias

Cada familia pertenece a un implemento y define un "paso" en el cotizador:

- **orden**: Secuencia de aparición (1, 2, 3...). Varias familias pueden compartir el mismo orden.
- **tipo_seleccion (Y/O)**:
  - **O** = Elegir UNO (radio). Familias con mismo orden y tipo "O" son alternativas mutuamente excluyentes.
  - **Y** = Elegir VARIOS (checkboxes).
- **obligatoria (SI/NO)**:
  - **SI** = DEBE seleccionar al menos uno.
  - **NO** = Puede no elegir ninguno (botón "Ninguno" seleccionado por defecto en tipo O, simplemente no marcar nada en tipo Y).

**UI al crear familia con orden existente**: Si el usuario elige un orden que ya existe para ese implemento, el tipo_seleccion y obligatoria se heredan automáticamente (no editables). Se muestra un árbol visual de las familias del implemento con sus órdenes para referencia. Si se quiere un orden nuevo que "empuja" al existente, preguntar si desplazar.

**Familias con mismo orden y tipo O**: NO se presentan todos los productos juntos. Se separan por familia con algún criterio visual (tabs, acordeones, o agrupados por nombre de familia) para que no sea una lista interminable.

### 3.3 Productos

Cada producto pertenece a una familia. No existe distinción base/opcional — las familias definen todo el comportamiento (obligatoria SI/NO, tipo O/Y).

Campos: nombre, cod_comercio, plano, cod_factura, orden (hereda de familia), **iva_porcentaje** (10.5%, 21%, etc. — cada producto tiene su propia alícuota de IVA).

### 3.4 Propiedades

Dimensiones físicas con tipo de agregación explícito:

| Propiedad | Unidad | Agregación |
|-----------|--------|------------|
| Longitud | mts | SUM |
| Peso | kg | SUM |
| Capacidad | lts | SUM |
| Altura | mm | MAX |
| LongitudLat | mts | MAX |
| Elásticos | u | MAX |
| Ejes | u | MAX |
| Llantas | u | MAX |
| Centro | mm | MAX |

### 3.5 Producto-Propiedades

Tres tipos: Exacto (valor fijo), Mínimo (acumulado debe ser ≥), Máximo (acumulado debe ser ≤).

El peso que soportan las llantas es por unidad de llantas (determinado por la cantidad anotada en propiedades del chasis).

---

## 4. Clientes, Bonificaciones y Formas de Pago

### 4.1 Tipos de Cliente

Categorías predefinidas por el Dueño. Cada tipo tiene un % de bonificación por defecto.

| Tipo | Bonif Default |
|------|--------------|
| Concesionario | 15% |
| Vendedor | 10% |
| Cliente Final | 0% |

### 4.2 Clientes

Cada cliente se crea con un tipo_cliente_id. Al crearlo, **hereda** la bonificación default del tipo. Pero se puede editar individualmente después (según permisos).

Campos: nombre, telefono, email, direccion, tipo_cliente_id, bonificacion_porcentaje (heredado, editable).

### 4.3 Formas de Pago

Tabla ABM con las formas de pago disponibles y su bonificación asociada.

| Forma de Pago | Bonif % |
|--------------|---------|
| Contado | 15% |
| Cheque 30 días | 10% |
| Cheque 60 días | 5% |
| Financiado | 0% |

### 4.4 Cálculo de Bonificaciones (en cascada)

```
subtotal_bruto         = Σ(precio_linea de todos los items)
bonif_tipocliente      = subtotal_bruto × (bonif_cliente% / 100)
subtotal_post_cliente  = subtotal_bruto - bonif_tipocliente
bonif_formapago        = subtotal_post_cliente × (bonif_pago% / 100)
subtotal_neto          = subtotal_post_cliente - bonif_formapago
```

Ambas bonificaciones son ajustables por el vendedor mediante una **barra deslizante** que va de 0% hasta el valor heredado/configurado. El límite máximo de ajuste total está definido por `tenants.bonif_max_porcentaje` — el vendedor no puede superar ese techo combinado.

### 4.5 Cálculo de IVA (por alícuota)

Cada producto tiene su `iva_porcentaje`. Se agrupa por alícuota:

```
Para cada alícuota (ej: 10.5%, 21%):
  base_gravada  = Σ(precio_linea de items con esa alícuota) - proporción de bonificaciones
  iva_alicuota  = base_gravada × (alícuota / 100)

iva_total = Σ(iva de cada alícuota)
precio_total = subtotal_neto + iva_total
```

En el PDF se desglosa cada alícuota por separado.

---

## 5. Flujo del Cotizador (Paso a Paso)

### 5.0 Selección/Carga de Cliente

Antes de empezar a cotizar, el vendedor elige un cliente existente o carga uno nuevo. Al seleccionar cliente, se carga su bonificación (heredada del tipo de cliente, o personalizada).

### 5.1 Selección de Implemento

El vendedor elige qué tipo de implemento cotizar.

### 5.2 Iteración por Familias (por orden)

Para cada grupo de orden:

1. **Cargar familias** del orden actual.
2. **Generar productos candidatos** de esas familias.
3. **Filtrar por Compatibilidad (Check_Comp)**: Vetado → ocultar. Forzado → mostrar obligatoriamente. Ya seleccionado → ocultar.
4. **Filtrar por Propiedades (Check_Prop)**: Verificar Min/Max contra dimensiones acumuladas.
5. **Presentar opciones**:
   - **Tipo O**: Radio buttons. Si obligatoria=NO → "Ninguno" seleccionado por defecto. Si hay varias familias con mismo orden y tipo O → separar visualmente por familia (tabs/acordeones), NO mezclar todo junto.
   - **Tipo Y**: Checkboxes. Si obligatoria=NO → nada marcado por defecto (no necesita botón "-").
6. **Al seleccionar**: Actualizar dimensiones acumuladas (SUM o MAX según propiedad.agregacion).
7. **Avance**: Tipo O → avanza tras selección. Tipo Y → avanza cuando el usuario indica que terminó.

### 5.3 Rodados Automáticos

Si `accesorios_tipo='Rodados'`: se inyectan Llantas → Ejes → Elásticos. Cantidades definidas por el chasis. Centro del chasis filtra llantas compatibles. Peso soportado por llantas es por unidad (determinado por cantidad en propiedades).

### 5.4 Bonificaciones y Forma de Pago

Al terminar la selección de productos:

1. Se muestra el subtotal bruto.
2. Se muestra la bonificación por tipo de cliente (heredada del cliente seleccionado en paso 0). Barra ajustable hasta bonif_max.
3. Se selecciona forma de pago. Barra ajustable para la bonificación de forma de pago, hasta bonif_max.
4. Se calcula en cascada: primero tipo cliente sobre subtotal, luego forma de pago sobre el resultado.
5. Se muestra IVA desglosado por alícuota.
6. Se muestra total final.
7. Se ingresa fecha de entrega estimada.

### 5.5 Finalización

- Estado pasa a `finalizada`. Se genera PDF.
- Si `user.requiere_validacion = true`: queda pendiente de aprobación del Dueño.
- Si `user.requiere_validacion = false`: puede pasar directamente a `confirmada`.
- Cotizaciones confirmadas cuentan para reportes.

### 5.6 Generación de PDF Cotización

Contenido del PDF:
- Logo y datos del tenant
- Número de cotización y fecha
- Fecha de entrega estimada
- Datos del cliente (nombre, teléfono, email, tipo)
- Nombre del vendedor
- Implemento cotizado
- Desglose: Lista de productos con cantidad (SIN precio unitario ni precio línea)
- Subtotal bruto
- Bonificación tipo cliente (% y monto)
- Bonificación forma de pago (% y monto)
- Subtotal neto
- IVA desglosado por alícuota (10.5%: $X, 21%: $Y, etc.)
- **TOTAL**
- Notas/observaciones

### 5.7 PDF de Lista de Prearmados

El Dueño puede generar un PDF con la lista de prearmados y sus precios (calculados desde la lista vigente) para pasar a concesionarios. Botón disponible en el panel de prearmados.

---

## 6. Sistema de Precios y Listas

### 6.1 Listas de Precios

Precios agrupados en listas numeradas (Lista 81, 82...). Solo una vigente a la vez. Nueva lista = % ajuste global + edición individual en borrador. Historial consultable.

### 6.2 Flujo de Creación

1. Dueño crea nueva lista con % de ajuste sobre la anterior.
2. Sistema genera todos los precios: `CEILING(precio_anterior × (1 + %/100), 1)`.
3. Lista en estado `borrador` → Dueño revisa/ajusta precios individuales.
4. Activar → anterior pasa a `historica`, nueva a `vigente`.

### 6.3 Precio Vigente

Precio del producto en la lista con estado='vigente'. Unique constraint: (lista_id, producto_id).

### 6.4 Cotización: Snapshot de Lista

Cada cotización guarda `lista_id` para saber con qué lista se cotizó.

### 6.5 Prearmados (BOM)

Templates de configuraciones estándar. Precio calculado = Σ(precio_en_lista_vigente × cantidad). Botón para generar PDF de lista de prearmados para concesionarios.

---

## 7. Motor de Validación (Detalle Técnico)

### 7.1 Dimensiones Acumuladas

```python
for propiedad in propiedades:
    if propiedad.agregacion == 'SUM':
        acumulado[propiedad] = sum(...)
    else:  # MAX
        acumulado[propiedad] = max(...)
```

### 7.2 Check de Compatibilidad

```python
def check_compatibilidad(candidato_id, seleccionados_ids, reglas, cotizacion_items):
    for sel_id in seleccionados_ids:
        regla = reglas.filter(padre=sel_id, hijo=candidato_id).first()
        if regla and regla.tipo == 'Forzado': return 'SI'
        if regla and regla.tipo == 'Vetado': return 'NO'
    if candidato_id in [item.producto_id for item in cotizacion_items]:
        return 'NO'
    return None
```

### 7.3 Check de Propiedades

```python
def check_propiedades(candidato_id, acumulado, prod_props):
    for propiedad, min_val, max_val in get_minmax(candidato_id):
        dim_actual = acumulado.get(propiedad, 0)
        if min_val and dim_actual < min_val: return False
        if max_val and dim_actual > max_val: return False
    return True
```

---

## 8. Historial y Reportes

### 8.1 Historial de Cotizaciones

Filtros: fecha, vendedor, implemento, estado, cliente.

Visibilidad: Vendedor ve solo las suyas. Dueño/Admin ven todas.

### 8.2 Reportes

Solo sobre cotizaciones **confirmadas**. Métricas posibles: total cotizado por período, por vendedor, por implemento, por cliente/tipo de cliente.

---

## 9. Stack Técnico

| Capa | Tecnología |
|------|-----------|
| Backend | Django 5.1+ (AbstractUser) |
| Frontend | HTMX 2.x + Tailwind CSS 3.x |
| Base de datos | PostgreSQL 16 |
| PDF | WeasyPrint |
| Hosting | Railway |
| Multi-tenant | Filtro por tenant_id (middleware) |
| Versionado | Git + GitHub |
| Tests | pytest-django + factory_boy |
| CI | GitHub Actions |

---

## 10. Resumen de Reglas de Negocio

1. **Jerarquía**: Implemento → Familias (ordenadas) → Productos.
2. **No hay distinción base/opcional** — las familias definen todo con tipo_seleccion y obligatoria.
3. **Navegación**: Tipo O avanza tras una selección. Tipo Y permite múltiples.
4. **Obligatoriedad**: SI = debe elegir. NO = "Ninguno" por defecto (tipo O) o nada marcado (tipo Y).
5. **Familias mismo orden + tipo O**: Separar visualmente por familia, no mezclar todo.
6. **Familia con orden existente**: Hereda tipo_seleccion y obligatoria. Opción de desplazar.
7. **Dimensiones acumuladas**: SUM para Longitud/Peso/Capacidad, MAX para el resto.
8. **Filtro Compatibilidad**: Vetado oculta, Forzado muestra.
9. **Filtro Propiedades**: Min/Max del candidato vs dimensiones acumuladas.
10. **Rodados automáticos**: accesorios_tipo='Rodados' inyecta Llantas→Ejes→Elásticos. Peso llantas es por unidad.
11. **Cliente**: Se elige/carga al inicio. Hereda bonificación del tipo de cliente. Editable.
12. **Bonificaciones en cascada**: Primero tipo cliente sobre subtotal, luego forma de pago sobre el resultado. Ambas ajustables con barra hasta bonif_max.
13. **IVA por producto**: Cada producto tiene su alícuota. Se desglosa por alícuota en el PDF.
14. **Precio total**: subtotal - bonif_cliente - bonif_pago + IVA_desglosado.
15. **Listas de precios**: Numeradas, una vigente. Nueva = % ajuste global + edición individual.
16. **PDF cotización**: Sin precio unitario/línea. Con bonificaciones, IVA desglosado, fecha entrega.
17. **PDF prearmados**: Para concesionarios, desde lista vigente.
18. **Estados**: borrador → aprobada → confirmada. Confirmada requiere aprobación si vendedor.requiere_validacion=true.
19. **Reportes**: Solo sobre cotizaciones confirmadas.
20. **Visibilidad**: Vendedor ve solo sus cotizaciones. Dueño ve todas.
21. **Panel Dueño**: CRUD completo catálogo, precios, bonif_max, usuarios, aprobación de cotizaciones.

---

## 11. Diccionario de Datos (18 tablas)

### 11.1 TENANTS

Tabla raíz multicliente.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | uuid PK | Identificador |
| nombre | varchar | Razón social |
| slug | varchar UK | URL-friendly |
| bonif_max_porcentaje | decimal(5,2) | Límite máximo de bonificación total para vendedores (tope de la barra) |
| moneda | varchar(3) | Default "ARS" |
| activo | bool | Soft delete |

**Relaciones**: 1:N hacia users, implementos, propiedades, listas_precios, tipos_cliente, formas_pago, clientes, compatibilidades, prearmados, cotizaciones.

---

### 11.2 USERS

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | Identificador |
| tenant_id | uuid FK → tenants | Empresa |
| email | varchar UK | Login |
| password_hash | varchar | Django AbstractUser |
| nombre | varchar | Nombre para mostrar |
| rol | enum | admin / dueno / vendedor |
| requiere_validacion | bool def false | Si true, sus cotizaciones necesitan aprobación del Dueño para pasar a confirmada |
| activo | bool | |

**Relaciones**: → cotizaciones (vendedor_id), → precios_productos (editado_por), → listas_precios (creada_por).

---

### 11.3 TIPOS_CLIENTE

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | Identificador |
| tenant_id | uuid FK → tenants | |
| nombre | varchar | Ej: "Concesionario", "Vendedor", "Cliente Final" |
| bonificacion_default | decimal(5,2) | % de bonificación que heredan los clientes de este tipo |

**Relaciones**: 1:N → clientes.

---

### 11.4 CLIENTES

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | Identificador |
| tenant_id | uuid FK → tenants | |
| tipo_cliente_id | int FK → tipos_cliente | Categoría del cliente |
| nombre | varchar | |
| telefono | varchar null | |
| email | varchar null | |
| direccion | text null | |
| bonificacion_porcentaje | decimal(5,2) | Heredado del tipo al crear, editable después |

**Relaciones**: → cotizaciones (cliente_id). Hereda bonificacion_default de tipo_cliente al crearse.

---

### 11.5 FORMAS_PAGO

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | Identificador |
| tenant_id | uuid FK → tenants | |
| nombre | varchar | Ej: "Contado", "Cheque 30 días" |
| bonificacion_porcentaje | decimal(5,2) | % de bonificación por esta forma de pago |
| activo | bool def true | |

**Relaciones**: → cotizaciones (forma_pago_id).

---

### 11.6 IMPLEMENTOS

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | |
| tenant_id | uuid FK → tenants | |
| nombre | varchar | |
| accesorios_tipo | varchar null | 'Rodados' → inyecta familias de rodados |
| nivel_rodado | int null | Sets de rodados (1, 2, 3) |

**Relaciones**: 1:N → familias, productos, cotizaciones, prearmados.

---

### 11.7 FAMILIAS

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | |
| tenant_id | uuid FK → tenants | |
| implemento_id | int FK → implementos | |
| nombre | varchar | |
| orden | int | Secuencia. Mismo orden = mismo paso |
| tipo_seleccion | enum('O','Y') | O=uno, Y=varios |
| obligatoria | enum('SI','NO') | SI=debe elegir, NO=puede no elegir |

**Regla**: Al crear con orden existente → hereda tipo_seleccion y obligatoria automáticamente.

---

### 11.8 PRODUCTOS

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | |
| tenant_id | uuid FK → tenants | |
| implemento_id | int FK → implementos | |
| familia_id | int FK → familias | |
| nombre | varchar | |
| cod_comercio | varchar null | |
| plano | varchar null | |
| cod_factura | varchar null | |
| orden | int | Hereda de familia |
| iva_porcentaje | decimal(5,2) def 21.00 | Alícuota IVA del producto (10.5%, 21%, etc.) |

**Relaciones**: → producto_propiedades, precios_productos, compatibilidades (padre+hijo), cotizacion_items, estructura_prearmados.

---

### 11.9 PROPIEDADES

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | |
| tenant_id | uuid FK → tenants | |
| nombre | varchar | Longitud, Peso, Capacidad, Altura, etc. |
| unidad | varchar | mts, kg, lts, mm, unidades |
| agregacion | enum('SUM','MAX') | Cómo se acumula |

---

### 11.10 PRODUCTO_PROPIEDADES

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | |
| producto_id | int FK → productos | |
| propiedad_id | int FK → propiedades | |
| tipo | enum('Exacto','Minimo','Maximo') | |
| valor | decimal(12,4) | |
| valor_neto | decimal(12,4) null | Peso vacío (para cálculos manuales) |
| prioridad | int def 0 | |

---

### 11.11 COMPATIBILIDADES

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | |
| tenant_id | uuid FK → tenants | |
| producto_padre_id | int FK → productos | Trigger |
| producto_hijo_id | int FK → productos | Afectado |
| tipo | enum('Vetado','Forzado') | |

---

### 11.12 LISTAS_PRECIOS

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | |
| tenant_id | uuid FK → tenants | |
| numero | int | Secuencial (81, 82...) |
| nombre | varchar null | Descripción |
| fecha_creacion | timestamp | |
| estado | enum('vigente','historica','borrador') | |
| ajuste_pct | decimal null | % aplicado sobre anterior |
| lista_base_id | int FK null → listas_precios | Self-ref: cadena de ajustes |
| creada_por | int FK → users | |

---

### 11.13 PRECIOS_PRODUCTOS

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | |
| lista_id | int FK → listas_precios | |
| producto_id | int FK → productos | |
| precio | decimal(14,2) | |
| editado_por | int FK null → users | null=generado automáticamente |

UQ(lista_id, producto_id).

---

### 11.14 PREARMADOS

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | |
| tenant_id | uuid FK → tenants | |
| implemento_id | int FK → implementos | |
| nombre | varchar | |
| precio_referencia | decimal null | Precio comercial de referencia |

Botón para generar PDF de lista de prearmados con precios de lista vigente.

---

### 11.15 ESTRUCTURA_PREARMADOS

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | |
| prearmado_id | int FK → prearmados | |
| producto_id | int FK → productos | |
| cantidad | int | |

---

### 11.16 COTIZACIONES

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | |
| tenant_id | uuid FK → tenants | |
| implemento_id | int FK → implementos | |
| vendedor_id | int FK → users | |
| cliente_id | int FK → clientes | |
| lista_id | int FK → listas_precios | Lista usada |
| forma_pago_id | int FK → formas_pago | |
| numero | varchar UK | Auto (COT-2026-0001) |
| subtotal_bruto | decimal(14,2) | Σ precio_linea |
| bonif_cliente_pct | decimal(5,2) | % aplicado por tipo cliente |
| bonif_cliente_monto | decimal(14,2) | |
| bonif_pago_pct | decimal(5,2) | % aplicado por forma pago |
| bonif_pago_monto | decimal(14,2) | |
| subtotal_neto | decimal(14,2) | Bruto - bonif_cliente - bonif_pago |
| iva_105_base | decimal(14,2) def 0 | Base gravada al 10.5% |
| iva_105_monto | decimal(14,2) def 0 | |
| iva_21_base | decimal(14,2) def 0 | Base gravada al 21% |
| iva_21_monto | decimal(14,2) def 0 | |
| iva_total | decimal(14,2) | |
| precio_total | decimal(14,2) | subtotal_neto + iva_total |
| fecha_entrega | date null | Fecha estimada de entrega |
| estado | enum('borrador','aprobada','confirmada') | |
| confirmada_por | int FK null → users | Quién aprobó |
| confirmada_at | timestamp null | Cuándo se aprobó |
| pdf_url | text null | |
| notas | text null | |
| created_at | timestamp | |

**Relaciones**: → cotizacion_items (1:N), → cotizacion_dimensiones (1:N). ← users, implementos, clientes, listas_precios, formas_pago.

---

### 11.17 COTIZACION_ITEMS

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | |
| cotizacion_id | int FK → cotizaciones | |
| producto_id | int FK → productos | |
| familia_id | int FK → familias | |
| cantidad | int | |
| precio_unitario | decimal(14,2) | Snapshot |
| precio_linea | decimal(14,2) | unitario × cantidad |
| iva_porcentaje | decimal(5,2) | Snapshot de la alícuota del producto |

---

### 11.18 COTIZACION_DIMENSIONES

| Campo | Tipo | Descripción |
|-------|------|-------------|
| id | int PK | |
| cotizacion_id | int FK → cotizaciones | |
| propiedad_id | int FK → propiedades | |
| valor_acumulado | decimal(12,4) | |
