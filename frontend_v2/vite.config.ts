import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false, // Allow self-signed certificates if needed
        ws: false, // Disable WebSocket proxy (not needed for REST API)
      },
    },
    // Ensure Vite dev server uses HTTP, not HTTPS
    https: false,
  },
})
