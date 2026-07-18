/**
 * 自包含打包脚本：将 React + ReactDOM + ReactFlow 打包为一个浏览器脚本
 * 用法: node tools\bundle_rf_test.js
 * 
 * 原理：
 *   react-flow-renderer 的 UMD 代码已经被打包为单个文件，但它需要
 *   React 和 ReactDOM 作为全局变量。我们获取 React/ReactDOM 的 UMD 字符串
 *   合并到一个文件中按顺序执行。
 * 
 *   注意不能直接用 readFile 拼接 UMD，因为 react-flow-renderer 的 UMD
 *   使用了 import/module 检测，可能影响浏览器加载。所以我们手动构建。
 */

const fs = require('fs');
const path = require('path');

const TOOLS = __dirname;
const ROOT = path.resolve(TOOLS, '..');

// 读取所有 UMD 源文件
function read(name) {
  return fs.readFileSync(path.resolve(ROOT, 'node_modules', name), 'utf-8');
}

// 生成 bundle
function build() {
  const parts = [];

  // Part 1: React 生产 UMD (10KB, 设置 window.React)
  parts.push('// === React 18.3.1 ===');
  parts.push(read('react/umd/react.production.min.js'));

  // Part 2: ReactDOM 开发版 UMD — 需要包裹以确保在浏览器中工作
  // 问题：react-dom.development.js 检测 typeof exports !== undefined 时
  // 会走 CommonJS 路径。我们用 eval 包装确保在浏览器全局作用域执行。
  parts.push('// === ReactDOM 18.3.1 (development) ===');
  var rdSrc = read('react-dom/umd/react-dom.development.js');
  // 替换 UMD 检测，强制走浏览器全局路径
  // 原始: (function(global,factory){typeof exports==='object'...?factory(exports,require('react')):...})
  // 改为: 强制走最后一个分支
  rdSrc = rdSrc.replace(
    'typeof exports === \'object\' && typeof module !== \'undefined\'',
    'false /* forced browser path */'
  );
  parts.push(rdSrc);

  // Part 3: react-flow-renderer UMD (160KB)
  // 它的 UMD 已经打包好，它需要的 window.React 和 window.ReactDOM 应该已存在
  parts.push('// === react-flow-renderer 10.3.17 ===');
  var rfSrc = read('react-flow-renderer/dist/umd/index.js');
  // 同样强制浏览器路径
  rfSrc = rfSrc.replace(
    'typeof exports === \'object\' && typeof module !== \'undefined\'',
    'false /* forced browser path */'
  );
  parts.push(rfSrc);

  const bundle = parts.join('\n\n');
  const outPath = path.resolve(TOOLS, 'local-libs', 'bundle.js');
  fs.writeFileSync(outPath, bundle, 'utf-8');
  
  const kb = (bundle.length / 1024).toFixed(1);
  console.log(`✅ Bundle created: ${outPath} (${kb} KB)`);
}

build();
