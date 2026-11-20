"""
api/index.py
============
Backend de Geobooks Aburrá (FastAPI).

Cada ruta decide de dónde saca los datos:
  - USE_MOCK=true  -> funciones de mock_data.py (sin base de datos)
  - USE_MOCK=false -> consultas SQL de queries.py contra Supabase

Ambas devuelven filas con la misma forma, por eso el código de las rutas es uno solo.

Ejecutar en local:  uvicorn api.index:app --reload --port 8000
"""
import os
import sys
from datetime import datetime

# Permite "import db" y "import queries" tanto en local como en Vercel.
sys.path.insert(0, os.path.dirname(__file__))

import psycopg
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

import mock_data
import queries
from db import USE_MOCK, consultar, consultar_uno

app = FastAPI(title="Geobooks Aburrá API", version="1.0")

# CORS abierto: es una API pública de solo lectura (y un POST de eventos de demostración).
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ====================================================================== MANEJO DE ERRORES
# Todos los errores responden {"detail": "mensaje claro"}.
@app.exception_handler(psycopg.errors.ForeignKeyViolation)
async def error_llave_foranea(request: Request, exc):
    return JSONResponse(status_code=400, content={"detail": "El libro o la biblioteca indicados no existen."})


@app.exception_handler(psycopg.OperationalError)
async def error_conexion(request: Request, exc):
    return JSONResponse(status_code=503, content={
        "detail": "No se pudo conectar con la base de datos. Revisa DATABASE_URL (puerto 6543) o usa USE_MOCK=true."})


@app.exception_handler(psycopg.Error)
async def error_sql(request: Request, exc):
    # Casi siempre es un nombre de tabla/columna distinto: corregir en api/queries.py (marcas AJUSTAR).
    return JSONResponse(status_code=500, content={
        "detail": f"Error en la consulta SQL. Revisa los nombres en api/queries.py. Detalle: {exc}"})


@app.exception_handler(RuntimeError)
async def error_configuracion(request: Request, exc):
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ====================================================================== VALIDACIONES
SRID_PERMITIDOS = (4326, 3857, 9377, 3116)


def srid_valido(srid: int = Query(4326, description="Sistema de coordenadas de salida")):
    """Dependencia: valida ?srid= (por defecto 4326)."""
    if srid not in SRID_PERMITIDOS:
        raise HTTPException(status_code=422, detail=f"srid inválido. Usa uno de: {list(SRID_PERMITIDOS)}")
    return srid


class Punto(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class SugerenciaIn(BaseModel):
    puntos: list[Punto] = Field(min_length=1, max_length=50)


class EventoIn(BaseModel):
    titulo: str = Field(min_length=3, max_length=150)
    categoria_id: int = Field(gt=0)
    biblioteca_id: int = Field(gt=0)
    fecha: datetime
    descripcion: str = Field(default="", max_length=1000)


# ====================================================================== AYUDAS
def a_geojson(filas):
    """Convierte filas (con clave 'geometry') en una FeatureCollection GeoJSON."""
    features = []
    for fila in filas:
        props = {k: v for k, v in fila.items() if k != "geometry"}
        if props.get("distancia_m") is not None:
            props["distancia_m"] = round(float(props["distancia_m"]), 1)
        features.append({"type": "Feature", "id": props.get("id", props.get("evento_id")),
                         "geometry": fila["geometry"], "properties": props})
    return {"type": "FeatureCollection", "features": features}


def leer(sql, params, funcion_mock, *args):
    """Si hay mock usa mock_data; si no, ejecuta el SQL en la base."""
    return funcion_mock(*args) if USE_MOCK else consultar(sql, params)


# ====================================================================== RUTAS
@app.get("/api/salud")
def salud():
    if USE_MOCK:
        return {"estado": "ok", "mock": True, "base_de_datos": "no se usa (modo mock)"}
    consultar(queries.SALUD)  # si falla, el manejador de errores responde 503
    return {"estado": "ok", "mock": False, "base_de_datos": "conectada"}


@app.get("/api/bibliotecas")
def bibliotecas(srid: int = Depends(srid_valido)):
    return a_geojson(leer(queries.BIBLIOTECAS, {"srid": srid}, mock_data.listar_bibliotecas, srid))


@app.get("/api/bibliotecas/cercanas")
def bibliotecas_cercanas(lat: float = Query(..., ge=-90, le=90), lon: float = Query(..., ge=-180, le=180),
                         limite: int = Query(5, ge=1, le=20), srid: int = Depends(srid_valido)):
    params = {"lat": lat, "lon": lon, "limite": limite, "srid": srid}
    return a_geojson(leer(queries.BIBLIOTECAS_CERCANAS, params,
                          mock_data.bibliotecas_cercanas, lat, lon, limite, srid))


@app.get("/api/municipios")
def municipios(srid: int = Depends(srid_valido)):
    return a_geojson(leer(queries.MUNICIPIOS, {"srid": srid}, mock_data.listar_municipios, srid))


@app.get("/api/estaciones")
def estaciones(srid: int = Depends(srid_valido)):
    return a_geojson(leer(queries.ESTACIONES, {"srid": srid}, mock_data.listar_estaciones, srid))


@app.get("/api/cobertura")
def cobertura(srid: int = Depends(srid_valido)):
    return a_geojson(leer(queries.COBERTURA, {"srid": srid}, mock_data.listar_cobertura, srid))


@app.post("/api/sugerencia")
def sugerencia(datos: SugerenciaIn):
    """IDEA DIFERENCIADORA: centro del grupo de lectores + biblioteca más cercana a ese centro."""
    puntos = [p.model_dump() for p in datos.puntos]
    if USE_MOCK:
        fila = mock_data.sugerencia(puntos)
    else:
        fila = consultar_uno(queries.SUGERENCIA, {"lons": [p["lon"] for p in puntos],
                                                  "lats": [p["lat"] for p in puntos]})
    if not fila:
        raise HTTPException(status_code=404, detail="No hay bibliotecas registradas para sugerir.")
    return {
        "centro": {"lat": fila["centro_lat"], "lon": fila["centro_lon"]},
        "biblioteca": {"id": fila["id"], "nombre": fila["nombre"], "direccion": fila["direccion"],
                       "municipio": fila["municipio"], "lat": fila["lat"], "lon": fila["lon"],
                       "distancia_m": round(float(fila["distancia_m"]), 1)},
        "lectores": len(puntos),
    }


@app.get("/api/libros")
def libros():
    return leer(queries.LIBROS, None, mock_data.listar_libros)


@app.get("/api/eventos")
def eventos(srid: int = Depends(srid_valido)):
    return a_geojson(leer(queries.EVENTOS, {"srid": srid}, mock_data.listar_eventos, srid))


@app.post("/api/eventos", status_code=201)
def crear_evento(datos: EventoIn):
    valores = datos.model_dump()
    if USE_MOCK:
        nuevo_id = mock_data.crear_evento(valores)
        if nuevo_id is None:
            raise HTTPException(status_code=400, detail="El libro o la biblioteca indicados no existen.")
    else:
        nuevo_id = consultar_uno(queries.CREAR_EVENTO, valores)["id"]
    return {"id": nuevo_id, "mensaje": "Evento creado correctamente."}


# Descripción de cada sistema (solo informativa, para la demostración de transformación)
NOMBRES_SRID = {
    4326: ("WGS 84 (longitud, latitud)", "grados"),
    3857: ("Web Mercator (mapas web)", "metros"),
    9377: ("MAGNA-SIRGAS Origen Nacional", "metros"),
    3116: ("MAGNA-SIRGAS Bogotá", "metros"),
}


@app.get("/api/coordenadas/{biblioteca_id}")
def coordenadas(biblioteca_id: int):
    """La misma biblioteca expresada en los 4 sistemas de coordenadas."""
    fila = mock_data.coordenadas_biblioteca(biblioteca_id) if USE_MOCK \
        else consultar_uno(queries.COORDENADAS, {"id": biblioteca_id})
    if not fila:
        raise HTTPException(status_code=404, detail=f"No existe la biblioteca {biblioteca_id}.")
    sistemas = {}
    for srid, (nombre, unidad) in NOMBRES_SRID.items():
        sistemas[str(srid)] = {"nombre": nombre, "unidad": unidad,
                               "x": round(float(fila[f"x_{srid}"]), 6 if srid == 4326 else 2),
                               "y": round(float(fila[f"y_{srid}"]), 6 if srid == 4326 else 2)}
    return {"id": fila["id"], "nombre": fila["nombre"], "sistemas": sistemas}
