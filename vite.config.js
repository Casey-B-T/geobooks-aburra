// vite.config.js
// En desarrollo, Vite reenvía las peticiones /api al backend FastAPI (puerto 8000).
// En producción (Vercel) esa tarea la hace vercel.json.
import { defineConfig } from 'vite';

export default defineConfig({
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
    },
  },
});
