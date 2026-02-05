import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const apiTarget = env.VITE_API_TARGET || 'http://localhost:5000';

  const apiProxy = {
    '/api': {
      target: apiTarget,
      changeOrigin: true,
      secure: false, // allow self-signed HTTPS backend
      ws: false,
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      configure: (proxy: any) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        proxy.on('proxyReq', (proxyReq: any, req: any) => {
          // Forward Authorization header explicitly (alguns proxies/ambientes podem omitir)
          if (req?.headers?.authorization) {
            proxyReq.setHeader('authorization', req.headers.authorization);
          }
        });
      },
    },
  } as const;

  const isProduction = mode === 'production';

  return {
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
        '@/components': path.resolve(__dirname, './src/components'),
        '@/features': path.resolve(__dirname, './src/features'),
        '@/api': path.resolve(__dirname, './src/api'),
        '@/lib': path.resolve(__dirname, './src/lib'),
        '@/hooks': path.resolve(__dirname, './src/hooks'),
      },
      extensions: ['.mjs', '.js', '.mts', '.ts', '.jsx', '.tsx', '.json']
    },
    plugins: [
      react(),
      VitePWA({
        registerType: 'autoUpdate',
        includeAssets: ['favicon.ico'],
        manifest: {
          name: 'Plante Uma Flor - Gestão de Pedidos',
          short_name: 'Plante Uma Flor',
          description: 'Sistema de gestão de pedidos',
          theme_color: '#047857',
          background_color: '#ffffff',
          display: 'standalone',
          start_url: '/',
          icons: [
            {
              src: 'pwa-192x192.png',
              sizes: '192x192',
              type: 'image/png'
            },
            {
              src: 'pwa-512x512.png',
              sizes: '512x512',
              type: 'image/png'
            }
          ]
        },
        workbox: {
          // Forçar atualização imediata quando nova versão for detectada
          skipWaiting: true,
          clientsClaim: true,
          // Excluir rotas do backend - devem ir direto para o Flask (não SPA shell)
          // IMPORTANTE: OAuth callback da Nuvemshop é navegação para /api/... e o SW não pode interceptar.
          navigateFallbackDenylist: [/^\/api\//, /^\/capig/, /^\/meta-gateway/],
          runtimeCaching: [
            // Rotas do Meta Gateway - sempre buscar da rede, nunca cachear
            {
              urlPattern: /^\/capig\/.*/,
              handler: 'NetworkOnly'
            },
            {
              urlPattern: /^\/meta-gateway\/.*/,
              handler: 'NetworkOnly'
            },
            {
              urlPattern: /^https:\/\/fonts\.googleapis\.com\/.*/i,
              handler: 'CacheFirst',
              options: {
                cacheName: 'google-fonts-cache',
                expiration: {
                  maxEntries: 10,
                  maxAgeSeconds: 60 * 60 * 24 * 365
                }
              }
            },
            {
              urlPattern: /^https:\/\/fonts\.gstatic\.com\/.*/i,
              handler: 'CacheFirst',
              options: {
                cacheName: 'google-fonts-stylesheets-cache',
                expiration: {
                  maxEntries: 10,
                  maxAgeSeconds: 60 * 60 * 24 * 365
                }
              }
            },
            {
              urlPattern: /\.(?:png|jpg|jpeg|svg|gif|webp)$/,
              handler: 'CacheFirst',
              options: {
                cacheName: 'images-cache',
                expiration: {
                  maxEntries: 50,
                  maxAgeSeconds: 60 * 60 * 24 * 30
                }
              }
            },
            {
              urlPattern: /^\/api\/health$/,
              handler: 'NetworkFirst',
              options: {
                cacheName: 'health-cache',
                networkTimeoutSeconds: 3,
                expiration: {
                  maxEntries: 1,
                  maxAgeSeconds: 60 * 5
                }
              }
            },
            {
              urlPattern: /^\/api\/pedidos\?.*/,
              handler: 'NetworkFirst',
              options: {
                cacheName: 'pedidos-cache',
                networkTimeoutSeconds: 5,
                expiration: {
                  maxEntries: 50,
                  maxAgeSeconds: 60 * 60 * 24
                }
              }
            },
            {
              urlPattern: /^\/api\/stats$/,
              handler: 'NetworkFirst',
              options: {
                cacheName: 'stats-cache',
                networkTimeoutSeconds: 5,
                expiration: {
                  maxEntries: 10,
                  maxAgeSeconds: 60 * 60 * 24
                }
              }
            },
            {
              // ViaCEP proxy - sempre buscar da rede (não cachear)
              urlPattern: /^\/api\/cep\/.*/,
              handler: 'NetworkOnly'
            },
            {
              urlPattern: /^\/api\/.*/,
              handler: 'NetworkOnly'
            }
          ]
        }
      })
    ],
    server: {
      port: 5173,
      host: true,
      proxy: apiProxy,
    },
    preview: {
      port: 3000,
      host: true,
      allowedHosts: [
        'gestaopedidos.planteumaflor.online',
        'localhost',
        '127.0.0.1'
      ],
      proxy: apiProxy,
    },
    build: {
      // Source maps for production debugging (can be disabled for smaller builds)
      sourcemap: isProduction ? false : true,
      // Chunk size warning limit
      chunkSizeWarningLimit: 1000,
      // Performance optimizations
      reportCompressedSize: false, // Desabilita cálculo de tamanho comprimido (mais rápido)
      // Rollup options for better code splitting
      rollupOptions: {
        output: {
          manualChunks: {
            // Vendor chunks
            'react-vendor': ['react', 'react-dom', 'react-router-dom'],
            'mui-vendor': ['@mui/material', '@mui/icons-material', '@emotion/react', '@emotion/styled'],
            'query-vendor': ['@tanstack/react-query'],
            'form-vendor': ['react-hook-form', '@hookform/resolvers', 'zod'],
            'date-vendor': ['date-fns', 'dayjs'],
            'map-vendor': ['leaflet', 'react-leaflet'],
          }
        },
        // Limitar paralelismo para evitar sobrecarga (apenas em desenvolvimento local)
        ...(process.env.CI ? {} : { 
          maxParallelFileOps: 2, // Limitar operações paralelas de arquivo
        }),
      },
      // Minification
      minify: 'esbuild',
      // Target modern browsers
      target: 'esnext',
    },
    // Optimize dependencies
    optimizeDeps: {
      include: [
        'react',
        'react-dom',
        'react-router-dom',
        '@mui/material',
        '@tanstack/react-query'
      ]
    }
  };
})
