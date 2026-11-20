"""
api/db.py
=========
Conexión a Supabase (PostgreSQL + PostGIS) con psycopg v3.

IMPORTANTE: se usa el Transaction Pooler (puerto 6543). Este pooler NO soporta
sentencias preparadas, por eso se pasa prepare_threshold=None.
"""
import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()  # lee el archivo .env cuando se trabaja en local

# Modo mock: si es "true" no se toca la base de datos.
USE_MOCK = os.getenv("USE_MOCK", "true").strip().lower() == "true"


def conectar():
    """Abre una conexión nueva. Cada petición abre y cierra la suya (ideal para serverless)."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "Falta la variable DATABASE_URL. Defínela en .env o en Vercel, "
            "o usa USE_MOCK=true para trabajar sin base de datos."
        )
    return psycopg.connect(
        url,
        prepare_threshold=None,  # obligatorio con el Transaction Pooler
        row_factory=dict_row,    # cada fila llega como diccionario
        connect_timeout=10,
    )


def consultar(sql, params=None):
    """Ejecuta un SELECT y devuelve TODAS las filas (lista de diccionarios)."""
    with conectar() as conn:  # al salir: confirma y cierra
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            return cur.fetchall()


def consultar_uno(sql, params=None):
    """Ejecuta una consulta y devuelve solo la primera fila (o None)."""
    with conectar() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params or {})
            return cur.fetchone()
