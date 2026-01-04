module.exports = {
  globDirectory: './',
  globPatterns: [
    // App Shell
    'index.html',
    'manifest.json',
    
    // CSS
    'assets/css/style.css',
    
    // JavaScript - Core
    'assets/js/app.js',
    'assets/js/router.js',
    'assets/js/api.js',
    'assets/js/db.js',
    'assets/js/auth.js',
    'assets/js/utils.js',
    'assets/js/form.js',
    'assets/js/painel.js',
    'assets/js/masks.js',
    'assets/js/validators.js',
    'assets/js/cep-api.js',
    'assets/js/telemetry.js',      // ← ADICIONAR
    'assets/js/diagnostics.js', 
    
    // JavaScript - Components
    'assets/js/components/notification.js',
    'assets/js/components/modal.js',
    'assets/js/components/pedido-card.js',
    'assets/js/components/autocomplete-cliente.js',
    
    // Pages
    'pages/criar-pedido.html',
    'pages/painel.html',
    'pages/login.html',
    'pages/clientes.html',
    'pages/fontes-pedido.html',
    'pages/rota-entrega.html',
    
    // Ícones essenciais
    'assets/images/Buques.ico',
    'assets/js/icons/icon-72x72.png',
    'assets/js/icons/icon-96x96.png',
    'assets/js/icons/icon-128x128.png',
    'assets/js/icons/icon-144x144.png',
    'assets/js/icons/icon-152x152.png',
    'assets/js/icons/icon-192x192.png',
    'assets/js/icons/icon-384x384.png',
    'assets/js/icons/icon-512x512.png',
    
    // Imagens essenciais
    'assets/images/Logo.png',
    'assets/images/logo_print.png'
  ],
  
  // Ignorar querystrings de cache-busting (ex: ?v=buques)
  dontCacheBustURLsMatching: /^v$|^cache_bust$/,
  
  // Arquivo fonte do Service Worker (compilado pelo Rollup)
  swSrc: 'sw-compiled.js',
  
  // Arquivo de saída (gerado)
  swDest: 'sw.js',
  
  // Não precachear CDNs externas
  globIgnores: [
    '**/node_modules/**',
    '**/package*.json',
    '**/workbox-config.js',
    '**/sw-src.js',
    '**/.git/**'
  ],
  
  // Modo de injeção do manifest
  injectionPoint: 'self.__WB_MANIFEST',
  
  // Máximo de tamanho de arquivo para precache (5MB)
  maximumFileSizeToCacheInBytes: 5 * 1024 * 1024
};
