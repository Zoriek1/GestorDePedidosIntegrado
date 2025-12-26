const { injectManifest } = require('workbox-build');
const { execSync } = require('child_process');
const workboxConfig = require('./workbox-config.js');

// Primeiro, compilar o sw-src.js com Rollup
console.log('📦 Compilando Service Worker com Rollup...');
try {
  execSync('npx rollup -c rollup-sw.config.js', { stdio: 'inherit' });
  console.log('✅ Compilação concluída');
} catch (error) {
  console.error('❌ Erro na compilação:', error);
  process.exit(1);
}

// Usar injectManifest para injetar o manifest no arquivo compilado
console.log('🔧 Injetando precache manifest...');
injectManifest(workboxConfig)
  .then(({ count, size }) => {
    console.log(`✅ Service Worker gerado com sucesso!`);
    console.log(`   - ${count} URLs precacheadas`);
    console.log(`   - ${(size / 1024).toFixed(2)} kB total`);
  })
  .catch((error) => {
    console.error('❌ Erro ao injetar manifest:', error);
    process.exit(1);
  });
