import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import { readFileSync } from 'fs'

/**
 * 从项目根目录 config.yaml 读取端口，避免与后端 / start.bat 硬编码不一致。
 * 优先级：环境变量 > config.yaml > 默认值（与 start_backend.py、start.bat 保持一致）。
 */
const readConfigPort = (key, fallback) => {
  const envValue = String(process.env[key] ?? '').trim()
  if (/^\d+$/.test(envValue)) {
    return Number(envValue)
  }
  try {
    const configPath = resolve(__dirname, '..', 'config.yaml')
    const text = readFileSync(configPath, 'utf-8')
    // 兼容 8001 / '8001' / "8001" 三种写法
    const match = text.match(new RegExp(`^\\s*${key}:\\s*['"]?(\\d+)['"]?\\s*$`, 'm'))
    if (match) {
      return Number(match[1])
    }
  } catch {
    // config.yaml 不存在或不可读时回退到默认值
  }
  return fallback
}

const BACKEND_PORT = readConfigPort('BACKEND_PORT', 8000)
const FRONTEND_PORT = readConfigPort('FRONTEND_PORT', 3000)
const BACKEND_TARGET = `http://127.0.0.1:${BACKEND_PORT}`

console.log(`[vite] 前端端口: ${FRONTEND_PORT}  |  后端代理目标: ${BACKEND_TARGET}`)

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
    port: FRONTEND_PORT,
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
