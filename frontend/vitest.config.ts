/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Kept separate from vite.config.ts so the build config stays free of test
// concerns -- and so the Plotly manualChunks/optimizeDeps tuning there, which
// exists purely for bundle size, cannot affect how tests resolve modules.
export default defineConfig({
  define: { global: 'globalThis' },
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    // Plotly needs WebGL and a real layout engine; jsdom has neither. Charts
    // are stubbed in setup.ts, so nothing here should ever import the real one.
    exclude: ['node_modules/**', 'dist/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text-summary'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/main.tsx',
        'src/test/**',
        'src/**/*.d.ts',
        'src/lib/plotly-custom.ts',
        'src/components/charts/**',
      ],
    },
  },
});
