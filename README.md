# Geobooks Aburrá

Geoportal donde los lectores ven las bibliotecas del Valle de Aburrá, encuentran la más cercana y crean eventos de lectura.
**Idea diferenciadora:** se marcan en el mapa las ubicaciones de varios lectores, el sistema calcula el **centro del grupo** (`ST_Centroid` en EPSG:9377) y sugiere la **biblioteca más cercana a ese centro**.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, psycopg v3, python-dotenv |
| Frontend | HTML + CSS + JS, Leaflet, Vite (solo para construir) |
| Base de datos | Supabase (PostgreSQL + PostGIS), Transaction Pooler (puerto 6543) |
| Despliegue | GitHub + Vercel (un solo repositorio) |

## Estructura

```
api/index.py       rutas FastAPI
api/db.py          conexión (prepare_threshold=None por el pooler)
api/queries.py     TODO el SQL
api/mock_data.py   datos de ejemplo + lógica del modo mock
src/main.js        lógica de la página
src/map.js         mapa Leaflet
src/api.js         llamadas al backend
src/style.css      estilos
index.html · vite.config.js · vercel.json · package.json · requirements.txt
```

## Ejecutar en local (modo mock, sin base de datos)

```bash
cp .env.example .env            # USE_MOCK=true
python -m venv .venv && source .venv/bin/activate   # en Windows: .venv\Scripts\activate
pip install -r requirements.txt
npm install

# Terminal 1: backend
npm run api                     # http://127.0.0.1:8000/docs
# Terminal 2: frontend
npm run dev                     # http://localhost:5173
```

Requiere Node.js 20.19 o superior (por Vite 7) y Python 3.12.

## Conectar la base real (Supabase)

1. En `.env`: `USE_MOCK=false` y `DATABASE_URL` con la cadena del **Transaction Pooler** (puerto 6543).
2. Si algún nombre de tabla o columna es distinto, **corrígelo solo en `api/queries.py`** (busca los comentarios `AJUSTAR`).
3. Revisa `http://127.0.0.1:8000/api/salud`: debe decir `"mock": false` y `"base_de_datos": "conectada"`.

Supuestos de la base: `bibliotecas`, `libros`, `eventos_lectura`, `municipios`, `estaciones` y la vista materializada `cobertura_500m`, con `geom_9377` (SRID 9377) en cada tabla espacial.

## Endpoints

| Método | Ruta | Respuesta |
|---|---|---|
| GET | `/api/bibliotecas?srid=` | GeoJSON |
| GET | `/api/bibliotecas/cercanas?lat=&lon=&limite=5` | GeoJSON con `distancia_m` |
| GET | `/api/municipios` · `/api/estaciones` · `/api/cobertura` | GeoJSON |
| POST | `/api/sugerencia` | JSON `{centro, biblioteca}` |
| GET | `/api/libros` | JSON |
| GET / POST | `/api/eventos` | GeoJSON / JSON |
| GET | `/api/coordenadas/{id}` | JSON (4 sistemas) |
| GET | `/api/salud` | JSON |

`srid` acepta 4326 (por defecto), 3857, 9377 o 3116. El mapa siempre pide 4326.

## Despliegue en Vercel

1. Sube el repositorio a GitHub e impórtalo en Vercel (se detecta Vite automáticamente).
2. Variables de entorno: `USE_MOCK` y `DATABASE_URL`.
3. `vercel.json` reenvía `/api/*` a `api/index.py` (la función de Python). Vercel instala las dependencias desde `requirements.txt`.

## Notas para la defensa

- **Sin datos quemados:** el frontend solo pinta lo que responde la API; municipios, libros, tarjetas y eventos salen de allí. Pasar de mock a base real es cambiar una variable.
- **Por qué 9377 para medir:** está en metros, así `ST_Distance` y `ST_Centroid` dan resultados reales; el mapa usa 4326 porque Leaflet lo exige.
- **Por qué `prepare_threshold=None`:** el Transaction Pooler reparte cada transacción entre conexiones distintas y no soporta sentencias preparadas.
- **Límites del mock:** los círculos de cobertura no se unen y las proyecciones se calculan con fórmulas propias (en la base lo hace PostGIS).
