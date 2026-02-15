import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  define: { global: 'globalThis' },
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000'
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
