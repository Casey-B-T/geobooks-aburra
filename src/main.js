n · JS
// src/main.js
// Lógica de la página. Todo lo que se muestra (bibliotecas, categorías, municipios, eventos,
// distancias) viene de la API: aquí NO hay datos escritos a mano.
import './style.css';
import { api } from './api.js';
import * as M from './map.js';
 
// ---------------------------------------------------------------- AYUDAS
const $ = (s) => document.querySelector(s);
// Escapa texto de la base antes de meterlo en HTML (evita inyección de código)
const esc = (t) => String(t ?? '').replace(/[&<>"']/g,
  (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
// Quita tildes y mayúsculas para buscar "itagui" y encontrar "Itagüí"
const norm = (t) => String(t ?? '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase();
const fmtDist = (m) => (m < 1000 ? `${Math.round(m)} m` : `${(m / 1000).toFixed(1)} km`);
const fmtFecha = (iso) => new Date(iso).toLocaleString('es-CO', { dateStyle: 'long', timeStyle: 'short' });
const rutaGoogle = (lat, lon) => `https://www.google.com/maps/dir/?api=1&destination=${lat},${lon}`;
 
function mostrarAviso(texto, tipo = 'info') {
  const a = $('#aviso');
  a.textContent = texto;
  a.className = `aviso ${tipo}`;
  a.hidden = false;
  if (tipo === 'ok') setTimeout(() => { a.hidden = true; }, 4000);
}
 
// Configuración de la interfaz: qué capas existen y cuáles arrancan prendidas
const CAPAS = [
  { id: 'bibliotecas', nombre: 'Bibliotecas', activa: true },
  { id: 'municipios', nombre: 'Municipios', activa: true },
  { id: 'estaciones', nombre: 'Estaciones del Metro', activa: true },
  { id: 'cobertura', nombre: 'Cobertura a 500 m', activa: false },
];
 
// ---------------------------------------------------------------- ESTADO
const leerFavoritas = () => {
  try { return JSON.parse(localStorage.getItem('geobooks_favoritas') || '[]'); } catch { return []; }
};
 
const estado = {
  bibliotecas: [],   // features GeoJSON
  eventos: [],       // features GeoJSON
  libros: [],        // ahora contiene las categorías (id, titulo = nombre de la categoría)
  distancias: {},    // id biblioteca -> metros desde el usuario
  favoritas: new Set(leerFavoritas()),
  filtros: { texto: '', municipio: '', libro: '', soloEventos: false, soloFavoritas: false },
  puntos: [],        // lectores marcados en el mapa
  modoGrupo: false,
};
 
const eventosDe = (idBiblioteca) => estado.eventos.filter((e) => e.properties.biblioteca_id === idBiblioteca);
const biblioteca = (id) => estado.bibliotecas.find((b) => b.properties.id === id);
 
// ---------------------------------------------------------------- FILTROS
function filtradas() {
  const f = estado.filtros;
  const texto = norm(f.texto);
  const conEvento = new Set(estado.eventos.map((e) => e.properties.biblioteca_id));
  const conCategoria = f.libro
    ? new Set(estado.eventos.filter((e) => String(e.properties.categoria_id) === f.libro)
      .map((e) => e.properties.biblioteca_id))
    : null;
 
  const lista = estado.bibliotecas.filter((b) => {
    const p = b.properties;
    return (!texto || norm(`${p.nombre} ${p.direccion} ${p.municipio}`).includes(texto))
      && (!f.municipio || p.municipio === f.municipio)
      && (!conCategoria || conCategoria.has(p.id))
      && (!f.soloEventos || conEvento.has(p.id))
      && (!f.soloFavoritas || estado.favoritas.has(p.id));
  });
 
  // Si el usuario compartió su ubicación, se ordenan de la más cercana a la más lejana
  if (Object.keys(estado.distancias).length) {
    lista.sort((a, b) => (estado.distancias[a.properties.id] ?? Infinity)
      - (estado.distancias[b.properties.id] ?? Infinity));
  }
  return lista;
}
 
// Vuelve a pintar todo lo que depende de los filtros
function refrescar() {
  const lista = filtradas();
  M.mostrarSoloBibliotecas(new Set(lista.map((b) => b.properties.id)));
  $('#lista-bibliotecas').innerHTML = lista.length
    ? lista.map(tarjetaBiblioteca).join('')
    : '<p class="vacio">No hay bibliotecas con esos filtros.</p>';
  $('#resumen-resultados').textContent =
    `${lista.length} de ${estado.bibliotecas.length} bibliotecas${estado.filtros.soloFavoritas ? ' (solo favoritas)' : ''}`;
  $('#insignia-datos').textContent = `${estado.bibliotecas.length} bibliotecas · ${estado.eventos.length} eventos`;
  $('#num-favoritas').textContent = estado.favoritas.size;
  $('#btn-favoritas').classList.toggle('activo', estado.filtros.soloFavoritas);
}
 
// ---------------------------------------------------------------- TARJETAS Y POPUPS
function tarjetaBiblioteca(f) {
  const p = f.properties;
  const [lon, lat] = f.geometry.coordinates;
  const n = eventosDe(p.id).length;
  const d = estado.distancias[p.id];
  return `
    <article class="tarjeta">
      <div class="tarjeta-cabeza">
        <span class="etiqueta">${esc(p.municipio)}</span>
        ${n ? `<span class="etiqueta verde">${n} evento${n > 1 ? 's' : ''}</span>` : '<span class="etiqueta gris">Sin eventos</span>'}
      </div>
      <h3>${esc(p.nombre)}</h3>
      <p class="nota">📍 ${esc(p.direccion)}</p>
      ${d !== undefined ? `<p class="distancia">A ${fmtDist(d)} de ti</p>` : ''}
      <div class="tarjeta-pie">
        <button class="btn-primario" data-accion="ver" data-id="${p.id}">Ver en el mapa</button>
        <a class="btn-icono" title="Cómo llegar" target="_blank" rel="noopener" href="${rutaGoogle(lat, lon)}">➤</a>
        <button class="btn-icono ${estado.favoritas.has(p.id) ? 'fav' : ''}" title="Favorita"
                data-accion="fav" data-id="${p.id}">${estado.favoritas.has(p.id) ? '♥' : '♡'}</button>
      </div>
    </article>`;
}
 
function tarjetaEvento(f) {
  const p = f.properties;
  return `
    <article class="tarjeta">
      <div class="tarjeta-cabeza"><span class="etiqueta morada">${esc(p.categoria || 'Sin categoría')}</span></div>
      <h3>${esc(p.titulo)}</h3>
      <p class="nota">🕒 ${fmtFecha(p.fecha)}</p>
      <p class="nota">📍 ${esc(p.biblioteca_nombre)} · ${esc(p.municipio)}</p>
      ${p.descripcion ? `<p>${esc(p.descripcion)}</p>` : ''}
      <div class="tarjeta-pie">
        <button class="btn-primario" data-accion="ver" data-id="${p.biblioteca_id}">Ver en el mapa</button>
      </div>
    </article>`;
}
 
function crearPopup(p, lat, lon) {
  const eventos = eventosDe(p.id)
    .map((e) => `<li>${esc(e.properties.titulo)} <small>${fmtFecha(e.properties.fecha)}</small></li>`).join('');
  return `
    <div class="popup">
      <h3>${esc(p.nombre)}</h3>
      <p>${esc(p.direccion)} · ${esc(p.municipio)}</p>
      ${eventos ? `<ul>${eventos}</ul>` : '<p><em>Sin eventos todavía</em></p>'}
      <div class="popup-botones">
        <button data-accion="evento" data-id="${p.id}">Crear evento</button>
        <button data-accion="coords" data-id="${p.id}">Coordenadas</button>
        <a target="_blank" rel="noopener" href="${rutaGoogle(lat, lon)}">Cómo llegar</a>
      </div>
      <div id="coords-${p.id}"></div>
    </div>`;
}
 
const renderEventos = () => {
  $('#lista-eventos').innerHTML = estado.eventos.length
    ? estado.eventos.map(tarjetaEvento).join('')
    : '<p class="vacio">Todavía no hay eventos. ¡Crea el primero!</p>';
};
 
// ---------------------------------------------------------------- ACCIONES (clics en tarjetas y popups)
document.addEventListener('click', (e) => {
  const el = e.target.closest('[data-accion]');
  if (!el) return;
  const id = Number(el.dataset.id);
  if (el.dataset.accion === 'ver') {
    $('#mapa').scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(() => M.enfocarBiblioteca(id), 350);
  } else if (el.dataset.accion === 'fav') {
    estado.favoritas.has(id) ? estado.favoritas.delete(id) : estado.favoritas.add(id);
    try { localStorage.setItem('geobooks_favoritas', JSON.stringify([...estado.favoritas])); } catch { /* sin almacenamiento */ }
    refrescar();
  } else if (el.dataset.accion === 'evento') {
    abrirModalEvento(id);
  } else if (el.dataset.accion === 'coords') {
    mostrarCoordenadas(id);
  }
});
 
// Demostración de la transformación: misma biblioteca en 4 sistemas de coordenadas
async function mostrarCoordenadas(id) {
  const caja = document.getElementById(`coords-${id}`);
  if (!caja) return;
  caja.textContent = 'Consultando…';
  try {
    const r = await api.coordenadas(id);
    const filas = Object.entries(r.sistemas).map(([srid, s]) =>
      `<tr><td>${esc(srid)}</td><td>${esc(s.nombre)}</td><td>${s.x}</td><td>${s.y}</td></tr>`).join('');
    caja.innerHTML = `<table class="tabla-coords"><tr><th>EPSG</th><th>Sistema</th><th>X</th><th>Y</th></tr>${filas}</table>`;
  } catch (err) {
    caja.textContent = err.message;
  }
}
 
// ---------------------------------------------------------------- CERCA DE MÍ
function ubicarme() {
  if (!navigator.geolocation) return mostrarAviso('Tu navegador no permite la geolocalización.', 'error');
  mostrarAviso('Buscando tu ubicación…');
  navigator.geolocation.getCurrentPosition(async ({ coords }) => {
    const { latitude: lat, longitude: lon } = coords;
    try {
      M.marcarUbicacion(lat, lon);
      const fc = await api.cercanas(lat, lon, 20); // 20 = máximo permitido; sirve para ordenar las tarjetas
      estado.distancias = {};
      fc.features.forEach((f) => { estado.distancias[f.properties.id] = f.properties.distancia_m; });
      $('#lista-cercanas').innerHTML = fc.features.slice(0, 5).map((f) =>
        `<li><button class="enlace" data-accion="ver" data-id="${f.properties.id}">${esc(f.properties.nombre)}</button>
         <small>${fmtDist(f.properties.distancia_m)}</small></li>`).join('');
      $('#caja-cercanas').hidden = false;
      const [cLon, cLat] = fc.features[0].geometry.coordinates;
      M.ajustarA([[lat, lon], [cLat, cLon]]);
      $('#aviso').hidden = true;
      refrescar();
    } catch (err) { mostrarAviso(err.message, 'error'); }
  }, () => mostrarAviso('No pudimos obtener tu ubicación. Revisa los permisos del navegador.', 'error'),
  { enableHighAccuracy: true, timeout: 10000 });
}
 
// ---------------------------------------------------------------- GRUPO DE LECTORES (idea diferenciadora)
function alternarModoGrupo(activo) {
  estado.modoGrupo = activo;
  $('#chip-grupo').classList.toggle('activo', activo);
  $('#caja-grupo').hidden = !activo;
  M.setModoGrupo(activo);
}
 
function renderLectores() {
  M.dibujarLectores(estado.puntos);
  $('#lista-lectores').innerHTML = estado.puntos.map((p, i) =>
    `<li>Lector ${i + 1}: ${p.lat.toFixed(4)}, ${p.lon.toFixed(4)}
     <button class="enlace" data-quitar="${i}" title="Quitar">✕</button></li>`).join('');
  $('#btn-calcular').disabled = estado.puntos.length < 2;
}
 
function limpiarGrupo() {
  estado.puntos = [];
  $('#resultado-grupo').innerHTML = '';
  M.limpiarResultado();
  renderLectores();
}
 
async function calcularSugerencia() {
  try {
    const r = await api.sugerencia(estado.puntos);
    M.dibujarSugerencia(r.centro, r.biblioteca);
    M.ajustarA([...estado.puntos.map((p) => [p.lat, p.lon]), [r.biblioteca.lat, r.biblioteca.lon]]);
    $('#resultado-grupo').innerHTML = `
      <div class="resultado">
        <p>Con <b>${r.lectores}</b> lectores, la biblioteca más cercana al centro del grupo es:</p>
        <p><b>${esc(r.biblioteca.nombre)}</b> (${esc(r.biblioteca.municipio)})<br>
           a ${fmtDist(r.biblioteca.distancia_m)} del centro.</p>
        <button class="btn-primario" data-accion="evento" data-id="${r.biblioteca.id}">Crear evento aquí</button>
      </div>`;
  } catch (err) { mostrarAviso(err.message, 'error'); }
}
 
// ---------------------------------------------------------------- CREAR EVENTO (ventana modal)
function abrirModalEvento(idBiblioteca) {
  $('#e-biblioteca').value = String(idBiblioteca);
  $('#e-error').hidden = true;
  $('#modal-evento').showModal();
}
 
async function guardarEvento(ev) {
  ev.preventDefault();
  try {
    await api.crearEvento({
      titulo: $('#e-titulo').value.trim(),            // nombre del libro (texto libre)
      categoria_id: Number($('#e-libro').value),      // categoría elegida en la lista
      biblioteca_id: Number($('#e-biblioteca').value),
      fecha: $('#e-fecha').value,
      descripcion: $('#e-descripcion').value.trim(),
    });
    $('#modal-evento').close();
    $('#form-evento').reset();
    estado.eventos = (await api.eventos()).features; // se vuelven a pedir para ver el nuevo
    renderEventos();
    refrescar();
    mostrarAviso('Evento creado correctamente.', 'ok');
  } catch (err) {
    $('#e-error').textContent = err.message;
    $('#e-error').hidden = false;
  }
}
 
// ---------------------------------------------------------------- CONSTRUCCIÓN DE CONTROLES
const opciones = (lista, valor, texto) =>
  lista.map((x) => `<option value="${esc(valor(x))}">${esc(texto(x))}</option>`).join('');
 
function llenarSelects() {
  const municipios = [...new Set(estado.bibliotecas.map((b) => b.properties.municipio))].sort();
  $('#f-municipio').innerHTML += opciones(municipios, (m) => m, (m) => m);
  $('#f-libro').innerHTML += opciones(estado.libros, (l) => l.id, (l) => l.titulo);
  $('#e-libro').innerHTML = opciones(estado.libros, (l) => l.id, (l) => l.titulo);
  $('#e-biblioteca').innerHTML = opciones(
    estado.bibliotecas.map((b) => b.properties), (p) => p.id, (p) => `${p.nombre} (${p.municipio})`);
  $('#pie-municipios').textContent = municipios.join(' · ');
}
 
function construirControlCapas() {
  $('#control-capas').innerHTML = CAPAS.map((c) =>
    `<label><input type="checkbox" data-capa="${c.id}" ${c.activa ? 'checked' : ''}> ${c.nombre}</label>`).join('');
  CAPAS.forEach((c) => M.capaVisible(c.id, c.activa));
  $('#control-capas').addEventListener('change', (e) => {
    if (e.target.dataset.capa) M.capaVisible(e.target.dataset.capa, e.target.checked);
  });
}
 
function conectarEventos() {
  // Buscador
  $('#form-buscar').addEventListener('submit', (e) => {
    e.preventDefault();
    Object.assign(estado.filtros, {
      texto: $('#f-texto').value, municipio: $('#f-municipio').value, libro: $('#f-libro').value,
    });
    refrescar();
    $('#bibliotecas').scrollIntoView({ behavior: 'smooth' });
  });
  $('#btn-limpiar').addEventListener('click', () => {
    $('#form-buscar').reset();
    estado.filtros = { texto: '', municipio: '', libro: '', soloEventos: false, soloFavoritas: false };
    estado.distancias = {};
    $('#caja-cercanas').hidden = true;
    $('#chip-eventos').classList.remove('activo');
    refrescar();
  });
 
  // Chips y botones del mapa
  $('#chip-cerca').addEventListener('click', ubicarme);
  $('#btn-ubicacion').addEventListener('click', ubicarme);
  $('#chip-eventos').addEventListener('click', (e) => {
    estado.filtros.soloEventos = !estado.filtros.soloEventos;
    e.currentTarget.classList.toggle('activo', estado.filtros.soloEventos);
    refrescar();
  });
  $('#chip-grupo').addEventListener('click', () => alternarModoGrupo(!estado.modoGrupo));
  $('#btn-favoritas').addEventListener('click', () => {
    estado.filtros.soloFavoritas = !estado.filtros.soloFavoritas;
    refrescar();
    $('#bibliotecas').scrollIntoView({ behavior: 'smooth' });
  });
 
  // Herramientas SIG
  $('#sel-base').addEventListener('change', (e) => M.cambiarBase(e.target.value));
  $('#btn-centrar').addEventListener('click', M.centrarValle);
  $('#btn-limpiar-mapa').addEventListener('click', () => { M.limpiarMarcas(); limpiarGrupo(); });
 
  // Panel colapsable
  $('#btn-panel').addEventListener('click', () => {
    const colapsado = $('#inicio').classList.toggle('colapsado');
    $('#btn-panel').textContent = colapsado ? '▶' : '◀';
    setTimeout(M.redimensionar, 320); // espera a que termine la animación
  });
 
  // Grupo de lectores
  M.onClickMapa((lat, lon) => {
    if (!estado.modoGrupo) return;
    if (estado.puntos.length >= 50) return mostrarAviso('Máximo 50 lectores.', 'error');
    estado.puntos.push({ lat, lon });
    M.limpiarResultado();
    $('#resultado-grupo').innerHTML = '';
    renderLectores();
  });
  $('#lista-lectores').addEventListener('click', (e) => {
    const i = e.target.dataset.quitar;
    if (i === undefined) return;
    estado.puntos.splice(Number(i), 1);
    renderLectores();
  });
  $('#btn-calcular').addEventListener('click', calcularSugerencia);
  $('#btn-borrar-lectores').addEventListener('click', limpiarGrupo);
 
  // Eventos de lectura
  $('#btn-nuevo-evento').addEventListener('click', () => abrirModalEvento($('#e-biblioteca').value));
  $('#e-cancelar').addEventListener('click', () => $('#modal-evento').close());
  $('#form-evento').addEventListener('submit', guardarEvento);
}
 
// ---------------------------------------------------------------- ARRANQUE
async function iniciar() {
  $('#pie-anio').textContent = `© ${new Date().getFullYear()} Geobooks Aburrá · Proyecto académico de Tecnologías Geoespaciales y Desarrollo Web`;
  M.crearMapa('mapa');
  construirControlCapas();
  conectarEventos();
 
  try {
    // Todo se pide a la API al mismo tiempo
    const [salud, bib, mun, est, cob, libros, ev] = await Promise.all([
      api.salud(), api.bibliotecas(), api.municipios(), api.estaciones(),
      api.cobertura(), api.libros(), api.eventos(),
    ]);
    estado.bibliotecas = bib.features;
    estado.eventos = ev.features;
    estado.libros = libros;
 
    M.dibujarMunicipios(mun);
    M.dibujarEstaciones(est);
    M.dibujarCobertura(cob);
    M.dibujarBibliotecas(estado.bibliotecas, crearPopup);
    llenarSelects();
    renderEventos();
    refrescar();
    if (salud.mock) mostrarAviso('Modo demostración: se muestran datos de ejemplo (USE_MOCK=true).', 'info');
  } catch (err) {
    mostrarAviso(`No se pudieron cargar los datos: ${err.message}`, 'error');
    $('#insignia-datos').textContent = 'Sin conexión con los datos';
  }
}
 
iniciar();
 