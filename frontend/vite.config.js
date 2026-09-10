import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

const BACKEND_TARGET = 'http://127.0.0.1:8000'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler', // 使用现代 Sass API
        silenceDeprecations: ['legacy-js-api'], // 静默旧警告
      }
    }
  },
  optimizeDeps: {
    esbuildOptions: {
      target: 'es2022'
    },
    force: true,
    exclude: ['tree-sitter'],
  },
  build: {
    target: 'es2022',
  },
  server: {
    port: 3002,
    host: '0.0.0.0',
    headers: {
      'Cache-Control': 'no-cache, no-store, must-revalidate',
      'Pragma': 'no-cache',
      'Expires': '0',
    },
    proxy: {
      '^/api/': {
        target: BACKEND_TARGET,
        changeOrigin: true,
        secure: false,
      },
      '^/admin/': {
        target: BACKEND_TARGET,
        changeOrigin: true,
        secure: false,
      },
      '^/static/': {
        target: BACKEND_TARGET,
        changeOrigin: true,
        secure: false,
      },
      '^/media/': {
        target: BACKEND_TARGET,
        changeOrigin: true,
        secure: false,
      },
      '^/app-automation-templates/': {
        target: BACKEND_TARGET,
        changeOrigin: true,
        secure: false,
      },
      '^/app-automation-reports/': {
        target: BACKEND_TARGET,
        changeOrigin: true,
        secure: false,
      },
      '^/ws/': {
        target: BACKEND_TARGET,
        ws: true,
        changeOrigin: true,
        secure: false,
        configure: (proxy) => {
          proxy.on('error', (err) => {
            console.warn('[vite ws proxy]', err?.message || err)
          })
          proxy.on('proxyReqWs', (proxyReq, req, socket) => {
            socket.on('error', () => {})
          })
        },
      },
    },
  },
  assetsInclude: ['**/*.wasm'],
})
