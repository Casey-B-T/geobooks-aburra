// src/api.js
// ÚNICO lugar donde el frontend habla con el backend. Ningún dato está escrito en el código:
// todo (bibliotecas, libros, eventos...) llega de estas llamadas.
//
// El mapa siempre trabaja en EPSG:4326, por eso se pide srid=4326 explícitamente.

// Vacío = mismo dominio (proxy de Vite en local, rewrite de Vercel en producción).
const BASE = import.meta.env.VITE_API_URL || '';
const SRID_MAPA = 4326;

// Hace la petición y convierte los errores del backend en mensajes legibles.
async function pedir(ruta, opciones) {
  let respuesta;
  try {
    respuesta = await fetch(`${BASE}${ruta}`, opciones);
  } catch {
    throw new Error('No hay conexión con el servidor. ¿Está encendido el backend?');
  }
  if (!respuesta.ok) {
    let mensaje = `Error ${respuesta.status}`;
    try {
      const cuerpo = await respuesta.json();
      // FastAPI manda "detail" como texto (nuestros errores) o como lista (validación)
      mensaje = typeof cuerpo.detail === 'string' ? cuerpo.detail : 'Los datos enviados no son válidos.';
    } catch { /* la respuesta no era JSON */ }
    throw new Error(mensaje);
  }
  return respuesta.json();
}

const enviarJSON = (metodo, datos) => ({
  method: metodo,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(datos),
});

export const api = {
  salud: () => pedir('/api/salud'),
  bibliotecas: () => pedir(`/api/bibliotecas?srid=${SRID_MAPA}`),
  cercanas: (lat, lon, limite = 5) =>
    pedir(`/api/bibliotecas/cercanas?lat=${lat}&lon=${lon}&limite=${limite}&srid=${SRID_MAPA}`),
  municipios: () => pedir(`/api/municipios?srid=${SRID_MAPA}`),
  estaciones: () => pedir(`/api/estaciones?srid=${SRID_MAPA}`),
  cobertura: () => pedir(`/api/cobertura?srid=${SRID_MAPA}`),
  sugerencia: (puntos) => pedir('/api/sugerencia', enviarJSON('POST', { puntos })),
  libros: () => pedir('/api/libros'),
  eventos: () => pedir(`/api/eventos?srid=${SRID_MAPA}`),
  crearEvento: (datos) => pedir('/api/eventos', enviarJSON('POST', datos)),
  coordenadas: (id) => pedir(`/api/coordenadas/${id}`),
};
