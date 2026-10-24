# Peru Macro Data Platform
**Observatorio macroeconómico del Perú con historial de revisiones y publicación validada.**

[English README](README.md) · [Guía completa](docs/GUIA_COMPLETA.md)

Este segundo proyecto añade complejidad sobre un batch ETL: API real, series
diarias y mensuales, PostgreSQL, historial SCD2, dbt y promoción de tablas probadas.
Permite responder qué valor conocía el sistema en una carga anterior y conservar
las tablas de consulta cuando falla un nuevo modelo.

## Resultados reales
Ocho series del BCRP entre enero de 2005 y diciembre de 2025:
7,242 observaciones recibidas, 7,241 claves aceptadas, 106 faltantes explícitos
y un valor numérico malformado en cuarentena. Se generaron 252 meses analíticos.
Repetir exactamente la captura creó cero versiones nuevas en el historial.

Se ejecutaron cuatro modelos y 12 pruebas de dbt. Las pruebas Python terminaron
con 44 aprobadas, una omitida y 87% de cobertura. La validación SQL local usó
PGlite/WASM: no sustituye comprobar la concurrencia de PostgreSQL 16, que está
configurada en CI. [Detalle y límites](docs/VALIDATION.md).

## Demo con Docker
```bash
cp .env.example .env
docker compose -p macro-demo up -d postgres
docker compose -p macro-demo run --rm runner demo
docker compose -p macro-demo run --rm runner demo --revised
```
Las credenciales de ejemplo son públicas y solo para desarrollo local.
La demo y los datos reales deben usar bases distintas. Docker no se ejecutó
en el entorno de creación; la guía indica qué comprobaciones quedan pendientes.

## Qué demuestra
- Extracción por API con límites, reintentos y Bronze inmutable.
- Preservación de precisión decimal y faltantes, sin convertirlos en cero.
- Historial por serie y periodo; consultas as-of sobre tiempos observados.
- Tasa diaria agregada con el último valor disponible dentro de cada mes.
- Construcción y pruebas de dbt en esquemas aislados.
- Publicación atómica de vistas, auditoría y procedimientos de recuperación.

No reconstruye publicaciones oficiales anteriores a la primera captura.
El panel es descriptivo; no es un modelo de inversión ni de riesgo crediticio.
Autor: [Neil Borjas Ramos](https://github.com/NeilBorjasRamos).
