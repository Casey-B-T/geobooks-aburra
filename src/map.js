// src/map.js
// Todo lo relacionado con Leaflet. No conoce la API: recibe GeoJSON ya cargado.
// El mapa siempre usa EPSG:4326, y GeoJSON trae las coordenadas como [lon, lat].
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const CENTRO_VALLE = [6.2442, -75.5812]; // [lat, lon] vista inicial del Valle de Aburrá
let mapa;
let baseActual;
const grupos = {};           // un grupo de capas por tema (se prenden/apagan juntos)
const marcadores = new Map(); // id de biblioteca -> marcador

// Mapas base disponibles
const BASES = {
  claro: L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    { maxZoom: 19, attribution: '© OpenStreetMap' }),
  oscuro: L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png',
    { maxZoom: 19, attribution: '© OpenStreetMap © CARTO' }),
};

export function crearMapa(idContenedor) {
  mapa = L.map(idContenedor, { zoomControl: false }).setView(CENTRO_VALLE, 11);
  L.control.zoom({ position: 'bottomright' }).addTo(mapa);
  baseActual = BASES.claro.addTo(mapa);
  // Orden de creación = orden de apilado (lo último queda encima)
  ['municipios', 'cobertura', 'estaciones', 'bibliotecas', 'usuario', 'grupo', 'resultado']
    .forEach((n) => { grupos[n] = L.layerGroup(); });
  // Las capas auxiliares siempre visibles; las temáticas las controla capaVisible()
  ['usuario', 'grupo', 'resultado'].forEach((n) => grupos[n].addTo(mapa));
  return mapa;
}

export function capaVisible(nombre, visible) {
  if (visible) grupos[nombre].addTo(mapa); else mapa.removeLayer(grupos[nombre]);
}

export function cambiarBase(nombre) {
  mapa.removeLayer(baseActual);
  baseActual = BASES[nombre].addTo(mapa);
  baseActual.bringToBack();
}

export const centrarValle = () => mapa.setView(CENTRO_VALLE, 11);
export const redimensionar = () => mapa.invalidateSize();
export const ajustarA = (latlngs) => mapa.fitBounds(L.latLngBounds(latlngs).pad(0.3), { maxZoom: 15 });
export const onClickMapa = (fn) => mapa.on('click', (e) => fn(e.latlng.lat, e.latlng.lng));
export const setModoGrupo = (activo) => mapa.getContainer().classList.toggle('modo-grupo', activo);

// ---------------------------------------------------------------- BIBLIOTECAS
const iconoBiblioteca = L.divIcon({
  className: 'pin', html: '<span>📖</span>', iconSize: [34, 34], iconAnchor: [17, 34], popupAnchor: [0, -30],
});

// features: GeoJSON de bibliotecas. crearPopup(props, lat, lon) devuelve el HTML del globo.
export function dibujarBibliotecas(features, crearPopup) {
  grupos.bibliotecas.clearLayers();
  marcadores.clear();
  features.forEach((f) => {
    const [lon, lat] = f.geometry.coordinates;
    const m = L.marker([lat, lon], { icon: iconoBiblioteca, title: f.properties.nombre })
      .bindPopup(() => crearPopup(f.properties, lat, lon));
    m.addTo(grupos.bibliotecas);
    marcadores.set(f.properties.id, m);
  });
}

// Muestra solo las bibliotecas cuyos ids estén en el conjunto (resultado de los filtros)
export function mostrarSoloBibliotecas(ids) {
  marcadores.forEach((m, id) => {
    if (ids.has(id)) grupos.bibliotecas.addLayer(m); else grupos.bibliotecas.removeLayer(m);
  });
}

export function enfocarBiblioteca(id) {
  const m = marcadores.get(id);
  if (!m) return;
  mapa.setView(m.getLatLng(), 15);
  m.openPopup();
}

// ---------------------------------------------------------------- CAPAS DE APOYO
export function dibujarMunicipios(fc) {
  grupos.municipios.clearLayers();
  L.geoJSON(fc, {
    style: { color: '#1d5f8a', weight: 2, fillOpacity: 0.05, dashArray: '5 4' },
    onEachFeature: (f, capa) => capa.bindTooltip(f.properties.nombre, { sticky: true }),
  }).addTo(grupos.municipios);
}

export function dibujarEstaciones(fc) {
  grupos.estaciones.clearLayers();
  L.geoJSON(fc, {
    pointToLayer: (f, ll) => L.circleMarker(ll, {
      radius: 6, color: '#fff', weight: 2, fillColor: '#d7263d', fillOpacity: 1,
    }).bindTooltip(`Metro · ${f.properties.nombre}`),
  }).addTo(grupos.estaciones);
}

export function dibujarCobertura(fc) {
  grupos.cobertura.clearLayers();
  L.geoJSON(fc, { style: { color: '#0e9f8e', weight: 1, fillColor: '#0e9f8e', fillOpacity: 0.22 } })
    .addTo(grupos.cobertura);
}

// ---------------------------------------------------------------- UBICACIÓN DEL USUARIO
export function marcarUbicacion(lat, lon) {
  grupos.usuario.clearLayers();
  L.circleMarker([lat, lon], { radius: 8, color: '#fff', weight: 3, fillColor: '#2563eb', fillOpacity: 1 })
    .bindTooltip('Tú estás aquí').addTo(grupos.usuario);
}

// ---------------------------------------------------------------- GRUPO DE LECTORES
const iconoNumero = (n) => L.divIcon({
  className: 'pin-lector', html: `<span>${n}</span>`, iconSize: [26, 26], iconAnchor: [13, 13],
});

export function dibujarLectores(puntos) {
  grupos.grupo.clearLayers();
  puntos.forEach((p, i) => L.marker([p.lat, p.lon], { icon: iconoNumero(i + 1) })
    .bindTooltip(`Lector ${i + 1}`).addTo(grupos.grupo));
}

// Dibuja el centro del grupo (estrella) y una línea hasta la biblioteca sugerida
export function dibujarSugerencia(centro, biblioteca) {
  grupos.resultado.clearLayers();
  L.marker([centro.lat, centro.lon], {
    icon: L.divIcon({ className: 'pin-centro', html: '<span>★</span>', iconSize: [30, 30], iconAnchor: [15, 15] }),
  }).bindTooltip('Centro del grupo').addTo(grupos.resultado);
  L.polyline([[centro.lat, centro.lon], [biblioteca.lat, biblioteca.lon]],
    { color: '#d97706', weight: 3, dashArray: '6 6' }).addTo(grupos.resultado);
}

export const limpiarResultado = () => grupos.resultado.clearLayers();
export function limpiarMarcas() {
  ['usuario', 'grupo', 'resultado'].forEach((n) => grupos[n].clearLayers());
}
