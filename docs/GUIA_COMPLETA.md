# Guía completa de construcción
Objetivo: pasar de una extracción reproducible a un producto con historia de
revisiones y publicación segura. Proyecto independiente del repositorio de taxis.

## 1. Alcance y preguntas
Consumidor: analista que necesita indicadores macroeconómicos consistentes.
Preguntas: ¿qué cambió entre dos capturas?, ¿qué conocía el sistema entonces?,
¿cómo alinear la tasa diaria con inflación mensual?, ¿qué consulta ve un consumidor
si falla un nuevo modelo?
No se construye un scoring crediticio, una predicción ni una recomendación financiera.
Cierre: explicar las diferencias entre periodo económico, instante de captura y
fecha oficial de publicación, que no está disponible en este producto.

## 2. Entorno y estructura
Python 3.12, uv 0.13.4 o compatible, Git, Docker con Compose.
```bash
uv sync --frozen --extra dev
uv run --frozen macro --help
uv run --frozen pytest -q
```
Sin TEST_DATABASE_URL las pruebas de base de datos se omiten explícitamente.
Carpetas: src/peru_macro (código y SQL), dbt (modelos y tests), tests (regresiones),
docs (contratos y operación), scripts (evidencia reproducible).
No instalar pgserver/PGlite para el uso normal: fueron herramientas locales de
validación, no dependencias de la aplicación.

Cierre: entorno instalado y pruebas unitarias verdes.

## 3. Levantar una demo aislada
```bash
cp .env.example .env
docker compose -p macro-demo up -d postgres
docker compose -p macro-demo run --rm runner demo
docker compose -p macro-demo run --rm runner demo --revised
docker compose -p macro-demo run --rm runner status
```
La segunda demo modifica un periodo de PBI. Consultar macro_raw.observation_history:
la versión anterior tiene valid_to y la nueva queda abierta.
Datos reales y demo no pueden compartir la misma base. Para cambiar:
```bash
docker compose -p macro-demo stop postgres
docker compose -p macro-real up -d postgres
```
Los volúmenes se conservan y tienen prefijos distintos por proyecto Compose.
Ambos servicios usan el puerto local 5433: no ejecutarlos simultáneamente sin
cambiar ese mapeo.
Cierre: demostrar una revisión sin borrar su valor anterior.

## 4. Explorar la API y el catálogo
Leer las páginas oficiales indicadas en DATA_CONTRACT.md y README.
El catálogo fija ocho series y su frecuencia. No inferirla por el sufijo del código:
PD12301MD es diaria. No utilizar PN01270PM para valores recientes porque corresponde
a un índice descontinuado. Cada solicitud contiene un código; así la posición
de values no se confunde entre respuestas de frecuencias distintas.

El API solicita idioma ing, pero se observó Set en fechas de septiembre.
El parser acepta ese alias de forma explícita. No usar un parser que convierta
cualquier texto silenciosamente.
Cierre: identificar unidad, frecuencia y fuente de cada serie.

## 5. Extraer y preservar Bronze
```bash
docker compose -p macro-real run --rm runner sync \
  --start 2005-01-01 --end 2025-12-31 --ingest-only
```
El cliente aplica tres intentos, límites de tamaño y timeouts. Los 4xx distintos
de 429 fallan directamente. La captura se almacena como código/SHA.json.
Cambiar bytes produce otra versión. Un archivo con nombre hash cuyo contenido
fue alterado bloquea el proceso.
Toda la extracción termina antes de publicar las observaciones en PostgreSQL.
Un fallo de una serie no deja una carga parcial de las otras en historia.
Cierre: rastrear una observación hasta los bytes exactos que la originaron.

## 6. Contratos, faltantes y cuarentena
Los valores se parsean como Decimal, no float; NUMERIC preserva la precisión.
n.d. representa un faltante explícito, no cero.
Un valor malformado va a macro_control.rejects con código, periodo, valor original
y motivo. Si supera el 1% dentro de una serie, se rechaza toda la ingesta.
Fechas desconocidas, duplicados y esquemas incorrectos fallan sin publicar.

El histórico real detectó una celda diaria concatenada. El proyecto no toma
arbitrariamente el primer número: la conserva en cuarentena.
Si antes existía un valor aceptado para esa clave, se mantiene y puede quedar
desactualizado. Esa elección debe explicarse al consumidor con observed_since
y el reporte de rechazos.

Cierre: explicar las tres situaciones: valor numérico, faltante explícito y
actualización rechazada. Son estados diferentes.

## 7. Construir el historial SCD2
Clave de negocio: serie y periodo. Clave de versión: serie, periodo y valid_from.
Intervalos semiabiertos: valid_from <= instante < valid_to.
Un valor igual no genera versión; un cambio cierra la anterior e inserta la nueva.
Los periodos ausentes no se borran. Un cambio a n.d. sí es una revisión explícita.
Una restricción parcial evita dos versiones abiertas.

La marca por defecto se toma después de capturar la fuente. No se asigna
artificialmente 2005 a los datos históricos descargados hoy.
```sql
select code,period,value,valid_from,valid_to
from macro_raw.observation_history
where code='PN01770AM'
order by period,valid_from;
```
Cierre: mostrar que una consulta as-of antes y después de una revisión devuelve
valores distintos. No afirmar que reconstruye las publicaciones originales del BCRP.

## 8. Modelar con dbt
Cuatro modelos:
1. stg_current_observations: snapshot de las versiones abiertas.
2. fct_monthly_observations: un valor por serie y mes.
3. mart_macro_dashboard: panel de indicadores con sus unidades.
4. mart_revisions: cantidad de versiones observadas por clave.

Para tasa diaria se usa el último dato no nulo del propio mes.
No arrastrar valores desde meses anteriores. PBI YoY compara con el mes exacto
del año anterior, no con doce filas disponibles si hay huecos.
No calcular variación porcentual sobre una variable que ya expresa una tasa
sin justificar una métrica distinta.
Cierre: poder explicar cada columna y evitar mezclar bases de índices o unidades.

## 9. Separar construcción de publicación
Cada ejecución crea build_UUID. dbt materializa tablas ahí y ejecuta pruebas.
Solo después se cambian las tres vistas de macro_analytics en una transacción.
Si dbt falla, la historia ya aceptada puede haber avanzado, pero el consumidor
mantiene la publicación anterior.

Este patrón no promete una transacción global entre Python, HTTP y dbt.
Leer ADR 002 y ejecutar la prueba de promoción fallida.
Cierre: distinguir estado ingested de published y diagnosticar un run failed
sin suponer que toda su ingesta fue revertida.

## 10. Actualizar rangos y recuperar
Para actualizar un rango reciente:
```bash
docker compose -p macro-real run --rm runner sync \
  --start 2024-01-01 --end 2025-12-31
```
Para capturar revisiones antiguas, repetir el histórico completo acordado.
No hay scheduler activado ni watermark que garantice detectar toda revisión.
RUNBOOK.md explica una estrategia de lookback más backfill completo periódico.

En macOS/Linux/Git Bash, para ejecutar Python contra el PostgreSQL local:
```bash
set -a
source .env
set +a
uv run --frozen macro status
```
PowerShell:
```powershell
$env:DATABASE_URL = "postgresql://macro:local_demo_only_change_me@localhost:5433/macro"
uv run --frozen macro status
```
La contraseña de ejemplo es pública y solo para un entorno descartable local.

## 11. Verificar y generar documentación de dbt
```bash
uv run --frozen ruff check src tests scripts
uv run --frozen ruff format --check src tests scripts
DBT_SEND_ANONYMOUS_USAGE_STATS=false uv run --frozen dbt parse --project-dir dbt --profiles-dir dbt
uv run --frozen pytest --cov -q
uv build
```
Para pruebas de integración, TEST_DATABASE_URL debe apuntar a una base descartable:
las fixtures eliminan esquemas del proyecto. No reutilizar una base de producción.
CI incluye PostgreSQL 16, test de dos escritores y demo completa.

Para documentación navegable de dbt, configurar las variables PGHOST/PGPORT/
PGUSER/PGPASSWORD/PGDATABASE del perfil y una base con modelos construidos:
```bash
DBT_SEND_ANONYMOUS_USAGE_STATS=false uv run --frozen dbt docs generate --project-dir dbt --profiles-dir dbt
```
Los artefactos generados quedan en dbt/target y no se versionan.

## 12. Evidencia real
scripts/validate_live.py captura el histórico si no existe data/real_inputs,
publica una vez y repite exactamente los mismos snapshots.
Requiere DATABASE_URL y ejecutarse con uv run para encontrar dbt.
Genera docs/validation.json. scripts/plot_evidence.py genera la figura del README.
```bash
uv run --frozen python scripts/validate_live.py
uv run --frozen --extra analysis python scripts/plot_evidence.py
```
En la evidencia incluida el motor fue PGlite/WASM. El script declara ese alcance;
actualizar la descripción si se ejecuta contra PostgreSQL normal.
Cierre: resultados, figura y conteos deben tener un origen reproducible.

## 13. Publicación profesional
Crear un repositorio vacío peru-macro-data-platform.
Revisar .gitignore y git diff antes del primer commit: no incluir .env, DSN,
datos originales, dbt/logs, bases ni .venv. Añadir About:
“Revision-aware BCRP data platform with PostgreSQL SCD2, dbt and tested publication.”
Topics sugeridos: data-engineering, postgres, dbt, python, bcrp, scd2, data-quality.
Son sugerencias; no se han aplicado a un repositorio remoto desde este paquete.

Demo para un reclutador: problema, captura real, revisión sintética identificada,
consulta as-of y fallo de promoción. Cerrar con límites y próxima mejora.
No inventar impacto de negocio, ahorro ni despliegue cloud.

## 14. Plan de cuatro semanas
| Semana | Trabajo | Cierre verificable |
|---|---|---|
| 1 | API, catálogo, Bronze y contratos | Captura real y problema de calidad explicado |
| 2 | SCD2, as-of y faltantes | Revisión y replay sin duplicados |
| 3 | dbt y promoción | Modelo fallido no cambia vistas de consumo |
| 4 | PostgreSQL 16, CI, respaldo y demo | Concurrencia y restauración comprobadas |

El código inicial se entrega completo; el plan reserva tiempo para dominarlo y
extenderlo con criterio. Revisa ROADMAP.md antes de atribuir capacidades pendientes.
