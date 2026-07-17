/**
 * esbuild 打包脚本（通过 Node.js API，绕过 CLI 二进制兼容问题）
 * 用法: node tools\build_editor.js
 */
const esbuild = require('esbuild');

async function build() {
  console.log('Building workflow editor bundle...');
  
  const result = await esbuild.build({
    entryPoints: ['tools/rf_test_entry.jsx'],
    outfile: 'tools/rf_test_bundle.js',
    bundle: true,
    minify: true,
    jsx: 'automatic',
    format: 'iife',
    globalName: 'VeroRunEditor',
    loader: {
      '.js': 'jsx',
    },
    logLevel: 'info',
  });

  console.log('✅ Build complete: tools/rf_test_bundle.js');
}

build().catch(err => {
  console.error('❌ Build failed:', err);
  process.exit(1);
});
