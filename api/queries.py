"""
api/queries.py
==============
TODO el SQL del proyecto vive en este archivo.
Si en tu base de datos una tabla o columna se llama distinto, SOLO se corrige aquí.

Convenciones:
- Los parámetros usan el estilo de psycopg: %(nombre)s  (nunca se concatena texto del usuario).
- %(srid)s es el sistema de coordenadas de salida (4326, 3857, 9377 o 3116).
  Todas las geometrías se convierten con ST_Transform desde geom_9377 (origen nacional).
- Cada consulta con geometría devuelve una columna llamada "geometry" (GeoJSON como json).
"""

# Fragmento reutilizable: convierte la geometría 9377 al SRID pedido y la entrega como GeoJSON.
# AJUSTAR: geom_9377 debe tener SRID 9377 definido en PostGIS.
_GEOJSON = "ST_AsGeoJSON(ST_Transform({tabla}.geom_9377, %(srid)s::int))::json AS geometry"

# ---------------------------------------------------------------- BIBLIOTECAS
BIBLIOTECAS = f"""
    SELECT b.id, b.nombre, b.direccion, b.municipio,
           {_GEOJSON.format(tabla="b")}
    FROM bibliotecas b
    ORDER BY b.nombre
"""  # AJUSTAR: columnas nombre, direccion, municipio

# Bibliotecas más cercanas a un punto (lat/lon en 4326 -> se pasa a 9377 para medir en metros).
# El operador <-> ordena usando el índice espacial (KNN) y ST_Distance da los metros exactos.
BIBLIOTECAS_CERCANAS = f"""
    WITH punto AS (
        SELECT ST_Transform(
                   ST_SetSRID(ST_MakePoint(%(lon)s::float8, %(lat)s::float8), 4326),
                   9377) AS g
    )
    SELECT b.id, b.nombre, b.direccion, b.municipio,
           ST_Distance(b.geom_9377, p.g) AS distancia_m,
           {_GEOJSON.format(tabla="b")}
    FROM bibliotecas b, punto p
    ORDER BY b.geom_9377 <-> p.g
    LIMIT %(limite)s
"""

# ---------------------------------------------------------------- CAPAS DE APOYO
MUNICIPIOS = """
    SELECT row_number() OVER () AS id,
           COALESCE(to_jsonb(m)->>'name', to_jsonb(m)->>'nombre') AS nombre,
           ST_AsGeoJSON(ST_Transform(m.geom, %(srid)s::int))::json AS geometry
    FROM municipios m
    WHERE GeometryType(m.geom) IN ('POLYGON', 'MULTIPOLYGON')
    ORDER BY nombre
"""

ESTACIONES = """
    SELECT row_number() OVER () AS id,
           COALESCE(to_jsonb(e)->>'name', to_jsonb(e)->>'nombre', 'Estación') AS nombre,
           COALESCE(to_jsonb(e)->>'railway', to_jsonb(e)->>'tipo', 'station') AS tipo,
           ST_AsGeoJSON(ST_Transform(e.geom, %(srid)s::int))::json AS geometry
    FROM estaciones e
    WHERE GeometryType(e.geom) = 'POINT'
    ORDER BY nombre
"""

# Vista materializada con las zonas de 500 m ya unidas.
COBERTURA = f"""
    SELECT c.id, {_GEOJSON.format(tabla="c")}
    FROM cobertura_500m c
"""

# ---------------------------------------------------------------- IDEA DIFERENCIADORA
# 1) Cada lector (lon, lat en 4326) se pasa a 9377.
# 2) ST_Centroid(ST_Collect(...)) calcula el centro del grupo en metros.
# 3) Se busca la biblioteca más cercana a ese centro y se devuelve todo en 4326 para el mapa.
SUGERENCIA = """
    WITH lectores AS (
        SELECT ST_Transform(ST_SetSRID(ST_MakePoint(t.lon, t.lat), 4326), 9377) AS g
        FROM unnest(%(lons)s::float8[], %(lats)s::float8[]) AS t(lon, lat)
    ),
    centro AS (
        SELECT ST_Centroid(ST_Collect(g)) AS g FROM lectores
    )
    SELECT b.id, b.nombre, b.direccion, b.municipio,
           ST_Distance(b.geom_9377, c.g)                       AS distancia_m,
           ST_Y(ST_Transform(b.geom_9377, 4326))               AS lat,
           ST_X(ST_Transform(b.geom_9377, 4326))               AS lon,
           ST_Y(ST_Transform(c.g, 4326))                       AS centro_lat,
           ST_X(ST_Transform(c.g, 4326))                       AS centro_lon
    FROM bibliotecas b, centro c
    ORDER BY b.geom_9377 <-> c.g
    LIMIT 1
"""

# ---------------------------------------------------------------- LIBROS Y EVENTOS
# Ahora devuelve las categorías (se mantiene el nombre LIBROS para no tocar api.js)
LIBROS = """
    SELECT id, nombre AS titulo, ''::text AS autor
    FROM categorias
    ORDER BY (nombre = 'Otro'), nombre
"""

EVENTOS = f"""
    SELECT e.id AS evento_id, e.titulo_evento AS titulo, e.fecha_reunion AS fecha,
           e.descripcion, c.id AS categoria_id, c.nombre AS categoria,
           b.id AS biblioteca_id, b.nombre AS biblioteca_nombre, b.municipio,
           {_GEOJSON.format(tabla="b")}
    FROM eventos_lectura e
    LEFT JOIN categorias c ON c.id = e.categoria_id
    JOIN bibliotecas b     ON b.id = e.biblioteca_id
    ORDER BY e.fecha_reunion
"""

CREAR_EVENTO = """
    INSERT INTO eventos_lectura (titulo_evento, categoria_id, biblioteca_id, fecha_reunion, descripcion)
    VALUES (%(titulo)s, %(categoria_id)s, %(biblioteca_id)s, %(fecha)s, %(descripcion)s)
    RETURNING id
"""

# ---------------------------------------------------------------- DEMOSTRACIÓN DE TRANSFORMACIÓN
# Una misma biblioteca expresada en los 4 sistemas (se transforma desde 9377).
COORDENADAS = """
    SELECT b.id, b.nombre,
           ST_X(ST_Transform(b.geom_9377, 4326)) AS x_4326, ST_Y(ST_Transform(b.geom_9377, 4326)) AS y_4326,
           ST_X(ST_Transform(b.geom_9377, 3857)) AS x_3857, ST_Y(ST_Transform(b.geom_9377, 3857)) AS y_3857,
           ST_X(b.geom_9377)                     AS x_9377, ST_Y(b.geom_9377)                     AS y_9377,
           ST_X(ST_Transform(b.geom_9377, 3116)) AS x_3116, ST_Y(ST_Transform(b.geom_9377, 3116)) AS y_3116
    FROM bibliotecas b
    WHERE b.id = %(id)s
"""

SALUD = "SELECT 1 AS ok"
