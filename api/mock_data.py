"""
api/mock_data.py
================
Datos de EJEMPLO para el modo mock (USE_MOCK=true).

Las funciones de abajo devuelven filas con la MISMA forma que devuelve la base real
(lista de diccionarios con una clave "geometry"), así el resto del backend y el
frontend no notan la diferencia.

Las coordenadas son aproximadas y solo sirven para demostración.
Los datos se declaran en 4326 (lon, lat) y se transforman aquí a otros sistemas
con fórmulas de Mercator Transversa (solo para el mock; en la base real lo hace PostGIS).
"""
import math
from datetime import datetime

# =====================================================================
# 1. TRANSFORMACIÓN DE COORDENADAS (equivalente simple a ST_Transform)
# =====================================================================
A = 6378137.0                # semieje mayor GRS80/WGS84
F = 1 / 298.257222101        # aplanamiento GRS80
E2 = F * (2 - F)             # excentricidad al cuadrado
EP2 = E2 / (1 - E2)

# Parámetros de las proyecciones colombianas
PROYECCIONES = {
    9377: dict(lat0=4.0, lon0=-73.0, k0=0.9992, x0=5000000.0, y0=2000000.0),   # Origen Nacional
    3116: dict(lat0=4.596200416666666, lon0=-74.07750791666666, k0=1.0,
               x0=1000000.0, y0=1000000.0),                                    # MAGNA Bogotá
}


def _arco_meridiano(phi):
    """Distancia sobre el meridiano desde el ecuador hasta la latitud phi (radianes)."""
    e4, e6 = E2 ** 2, E2 ** 3
    return A * ((1 - E2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * phi
                - (3 * E2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * math.sin(2 * phi)
                + (15 * e4 / 256 + 45 * e6 / 1024) * math.sin(4 * phi)
                - (35 * e6 / 3072) * math.sin(6 * phi))


def _mercator_transversa(lon, lat, p):
    """lon/lat (grados) -> x/y (metros) con la proyección p."""
    phi, lam = math.radians(lat), math.radians(lon)
    n = A / math.sqrt(1 - E2 * math.sin(phi) ** 2)
    t = math.tan(phi) ** 2
    c = EP2 * math.cos(phi) ** 2
    a = (lam - math.radians(p["lon0"])) * math.cos(phi)
    m, m0 = _arco_meridiano(phi), _arco_meridiano(math.radians(p["lat0"]))
    x = p["x0"] + p["k0"] * n * (a + (1 - t + c) * a ** 3 / 6
                                 + (5 - 18 * t + t * t + 72 * c - 58 * EP2) * a ** 5 / 120)
    y = p["y0"] + p["k0"] * (m - m0 + n * math.tan(phi) * (
        a * a / 2 + (5 - t + 9 * c + 4 * c * c) * a ** 4 / 24
        + (61 - 58 * t + t * t + 600 * c - 330 * EP2) * a ** 6 / 720))
    return x, y


def transformar_xy(lon, lat, srid):
    """Transforma un punto de 4326 al SRID pedido."""
    if srid == 4326:
        return lon, lat
    if srid == 3857:  # Web Mercator
        return A * math.radians(lon), A * math.log(math.tan(math.pi / 4 + math.radians(lat) / 2))
    return _mercator_transversa(lon, lat, PROYECCIONES[srid])


def transformar_geometria(geom, srid):
    """Transforma una geometría GeoJSON completa (punto, polígono, multipolígono)."""
    decimales = 6 if srid == 4326 else 2

    def convertir(c):
        if isinstance(c[0], (int, float)):
            x, y = transformar_xy(c[0], c[1], srid)
            return [round(x, decimales), round(y, decimales)]
        return [convertir(i) for i in c]

    return {"type": geom["type"], "coordinates": convertir(geom["coordinates"])}


def _punto(lon, lat):
    return {"type": "Point", "coordinates": [lon, lat]}


# =====================================================================
# 2. DATOS DE EJEMPLO (siempre en 4326)
# =====================================================================
# 12 bibliotecas aproximadas: (id, nombre, direccion, municipio, lat, lon)
_BIBLIOTECAS = [
    (1, "Biblioteca Pública Piloto", "Carrera 64 #50-32", "Medellín", 6.2672, -75.5895),
    (2, "Parque Biblioteca España", "Carrera 33B #107", "Medellín", 6.2937, -75.5424),
    (3, "Parque Biblioteca León de Greiff", "Carrera 36 #53", "Medellín", 6.2573, -75.5568),
    (4, "Parque Biblioteca San Javier", "Calle 42B #99", "Medellín", 6.2563, -75.6122),
    (5, "Parque Biblioteca Belén", "Calle 30A #76", "Medellín", 6.2326, -75.6049),
    (6, "Biblioteca Marco Fidel Suárez", "Carrera 50 #51", "Bello", 6.3373, -75.5560),
    (7, "Biblioteca Municipal de Copacabana", "Carrera 50 #50", "Copacabana", 6.3470, -75.5090),
    (8, "Biblioteca Diego Echavarría Misas", "Carrera 51 #51", "Itagüí", 6.1730, -75.6110),
    (9, "Biblioteca Débora Arango", "Carrera 43A #38S", "Envigado", 6.1705, -75.5860),
    (10, "Biblioteca Municipal de Sabaneta", "Carrera 45 #70S", "Sabaneta", 6.1515, -75.6160),
    (11, "Biblioteca Pública de La Estrella", "Calle 80S #60", "La Estrella", 6.1580, -75.6430),
    (12, "Biblioteca Pública de Caldas", "Carrera 50 #131S", "Caldas", 6.0910, -75.6360),
]

# 3 municipios simplificados (anillos cerrados [lon, lat])
_MUNICIPIOS = [
    (1, "Medellín", [[-75.64, 6.19], [-75.54, 6.19], [-75.52, 6.24], [-75.52, 6.32],
                     [-75.60, 6.33], [-75.68, 6.25], [-75.64, 6.19]]),
    (2, "Bello", [[-75.60, 6.31], [-75.52, 6.31], [-75.52, 6.37], [-75.58, 6.38],
                  [-75.62, 6.34], [-75.60, 6.31]]),
    (3, "Itagüí", [[-75.65, 6.15], [-75.59, 6.15], [-75.58, 6.19], [-75.64, 6.19],
                   [-75.65, 6.15]]),
]

# 6 estaciones del Metro: (id, nombre, tipo, lat, lon)
_ESTACIONES = [
    (1, "Niquía", "Metro", 6.3374, -75.5453),
    (2, "Bello", "Metro", 6.3330, -75.5560),
    (3, "San Antonio", "Metro", 6.2472, -75.5690),
    (4, "Poblado", "Metro", 6.2090, -75.5700),
    (5, "Itagüí", "Metro", 6.1820, -75.6070),
    (6, "La Estrella", "Metro", 6.1570, -75.6430),
]

# 3 libros
_LIBROS = [
    {"id": 1, "titulo": "Cien años de soledad", "autor": "Gabriel García Márquez"},
    {"id": 2, "titulo": "El olvido que seremos", "autor": "Héctor Abad Faciolince"},
    {"id": 3, "titulo": "La Virgen de los sicarios", "autor": "Fernando Vallejo"},
]

# 2 eventos de ejemplo (la lista es modificable: POST /api/eventos agrega aquí mientras corre el servidor)
_EVENTOS = [
    {"id": 1, "titulo": "Tertulia: Cien años de soledad", "libro_id": 1, "biblioteca_id": 1,
     "fecha": datetime(2026, 12, 5, 16, 0), "descripcion": "Conversación abierta sobre Macondo y su legado."},
    {"id": 2, "titulo": "Club de lectura: El olvido que seremos", "libro_id": 2, "biblioteca_id": 2,
     "fecha": datetime(2026, 12, 12, 15, 0), "descripcion": "Lectura compartida de fragmentos y charla."},
]


# =====================================================================
# 3. FUNCIONES QUE IMITAN LAS CONSULTAS DE queries.py
# =====================================================================
def _biblioteca_por_id(biblioteca_id):
    return next((b for b in _BIBLIOTECAS if b[0] == biblioteca_id), None)


def _fila_biblioteca(b, srid):
    return {"id": b[0], "nombre": b[1], "direccion": b[2], "municipio": b[3],
            "geometry": transformar_geometria(_punto(b[5], b[4]), srid)}


def _metros(lon, lat):
    """Coordenadas en 9377 (metros) para medir distancias planas, igual que la base real."""
    return transformar_xy(lon, lat, 9377)


def listar_bibliotecas(srid):
    return [_fila_biblioteca(b, srid) for b in sorted(_BIBLIOTECAS, key=lambda b: b[1])]


def bibliotecas_cercanas(lat, lon, limite, srid):
    px, py = _metros(lon, lat)
    filas = []
    for b in _BIBLIOTECAS:
        bx, by = _metros(b[5], b[4])
        fila = _fila_biblioteca(b, srid)
        fila["distancia_m"] = math.hypot(bx - px, by - py)
        filas.append(fila)
    return sorted(filas, key=lambda f: f["distancia_m"])[:limite]


def listar_municipios(srid):
    return [{"id": m[0], "nombre": m[1],
             "geometry": transformar_geometria({"type": "Polygon", "coordinates": [m[2]]}, srid)}
            for m in _MUNICIPIOS]


def listar_estaciones(srid):
    return [{"id": e[0], "nombre": e[1], "tipo": e[2],
             "geometry": transformar_geometria(_punto(e[4], e[3]), srid)}
            for e in _ESTACIONES]


def listar_cobertura(srid):
    """Círculos de 500 m. OJO: en el mock NO se unen los que se solapan (la vista real sí)."""
    circulos = []
    for b in _BIBLIOTECAS:
        lat, lon = b[4], b[5]
        dlat = 500 / 111320
        dlon = 500 / (111320 * math.cos(math.radians(lat)))
        anillo = [[lon + dlon * math.cos(2 * math.pi * i / 32),
                   lat + dlat * math.sin(2 * math.pi * i / 32)] for i in range(33)]
        anillo[-1] = anillo[0]  # cierra el anillo
        circulos.append([anillo])
    return [{"id": 1, "geometry": transformar_geometria(
        {"type": "MultiPolygon", "coordinates": circulos}, srid)}]


def _inversa_9377(x, y, lat, lon):
    """Pasa de 9377 a 4326 por aproximaciones sucesivas (parte de una estimación inicial)."""
    for _ in range(8):
        fx, fy = _metros(lon, lat)
        lat += (y - fy) / 110574
        lon += (x - fx) / (111320 * math.cos(math.radians(lat)))
    return lat, lon


def sugerencia(puntos):
    """Centro del grupo (promedio en 9377 = ST_Centroid) y biblioteca más cercana a ese centro."""
    xy = [_metros(p["lon"], p["lat"]) for p in puntos]
    cx = sum(p[0] for p in xy) / len(xy)
    cy = sum(p[1] for p in xy) / len(xy)
    lat0 = sum(p["lat"] for p in puntos) / len(puntos)
    lon0 = sum(p["lon"] for p in puntos) / len(puntos)
    centro_lat, centro_lon = _inversa_9377(cx, cy, lat0, lon0)
    mejor = min(_BIBLIOTECAS, key=lambda b: math.hypot(_metros(b[5], b[4])[0] - cx,
                                                       _metros(b[5], b[4])[1] - cy))
    bx, by = _metros(mejor[5], mejor[4])
    return {"id": mejor[0], "nombre": mejor[1], "direccion": mejor[2], "municipio": mejor[3],
            "distancia_m": math.hypot(bx - cx, by - cy), "lat": mejor[4], "lon": mejor[5],
            "centro_lat": centro_lat, "centro_lon": centro_lon}


def listar_libros():
    return sorted(_LIBROS, key=lambda l: l["titulo"])


def listar_eventos(srid):
    filas = []
    for e in sorted(_EVENTOS, key=lambda e: e["fecha"]):
        libro = next(l for l in _LIBROS if l["id"] == e["libro_id"])
        b = _biblioteca_por_id(e["biblioteca_id"])
        filas.append({"evento_id": e["id"], "titulo": e["titulo"], "fecha": e["fecha"],
                      "descripcion": e["descripcion"], "libro_id": libro["id"],
                      "libro_titulo": libro["titulo"], "autor": libro["autor"],
                      "biblioteca_id": b[0], "biblioteca_nombre": b[1], "municipio": b[3],
                      "geometry": transformar_geometria(_punto(b[5], b[4]), srid)})
    return filas


def crear_evento(datos):
    """Agrega un evento a la lista en memoria. Devuelve el id nuevo, o None si libro/biblioteca no existen."""
    if not any(l["id"] == datos["libro_id"] for l in _LIBROS) or not _biblioteca_por_id(datos["biblioteca_id"]):
        return None
    nuevo = {"id": max(e["id"] for e in _EVENTOS) + 1 if _EVENTOS else 1, **datos}
    _EVENTOS.append(nuevo)
    return nuevo["id"]


def coordenadas_biblioteca(biblioteca_id):
    b = _biblioteca_por_id(biblioteca_id)
    if not b:
        return None
    fila = {"id": b[0], "nombre": b[1]}
    for srid in (4326, 3857, 9377, 3116):
        x, y = transformar_xy(b[5], b[4], srid)
        fila[f"x_{srid}"], fila[f"y_{srid}"] = x, y
    return fila
