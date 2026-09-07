import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // 1. Proxy upload and delete actions to Backend 1 (segy-processing-service :8000)
      '/api/segy-files/upload': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/api/segy-files/batch-delete': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/api/blocks/upload-zip': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      // 2. Proxy remaining API requests to Backend 2 (data-serving :8001)
      '/api': {
        target: 'http://localhost:8001',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
