import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // Listen on all interfaces
    port: 5173,
    proxy: {
      '/api': 'http://localhost:8000'
    }
  }
})