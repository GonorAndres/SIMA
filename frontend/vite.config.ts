import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  define: { global: 'globalThis' },
  plugins: [react()],
  server: {
    proxy: {
      // Port 8000 is the documented default; override when the backend is
      // already occupying another port locally.
      '/api': process.env.VITE_API_PROXY || 'http://localhost:8000'
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('plotly.js')) return 'plotly';
          if (id.includes('react-dom') || id.includes('/react/') || id.includes('react-router')) return 'vendor';
        },
      },
    },
  },
  optimizeDeps: {
    include: [
      'plotly.js/lib/core',
      'plotly.js/lib/heatmap',
      'plotly.js/lib/surface',
      'plotly.js/lib/waterfall',
    ],
  },
})
