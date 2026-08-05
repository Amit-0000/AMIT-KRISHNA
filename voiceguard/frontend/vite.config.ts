import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: true,
    // Native fs events from a Windows-host bind mount don't reliably reach
    // chokidar inside the Linux container docker-compose runs this in —
    // without polling, edits saved on the host silently never trigger HMR
    // or even get picked up on a hard refresh (the dev server keeps serving
    // whatever it read at boot).
    watch: {
      usePolling: true,
      interval: 300,
    },
    proxy: {
      '/api': {
        // Overridable so `docker compose` can point the dev server at the
        // `backend` service name instead of localhost.
        target: process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    chunkSizeWarningLimit: 600,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'motion': ['framer-motion'],
          'radix': [
            '@radix-ui/react-dialog',
            '@radix-ui/react-dropdown-menu',
            '@radix-ui/react-scroll-area',
            '@radix-ui/react-tooltip',
            '@radix-ui/react-slot',
            '@radix-ui/react-separator',
          ],
          'state': ['zustand', '@tanstack/react-query', 'axios'],
          'forms': ['react-hook-form', 'zod'],
        },
      },
    },
  },
})
