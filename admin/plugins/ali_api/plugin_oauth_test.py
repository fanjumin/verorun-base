#!/usr/bin/env python3
"""
1688 授权 + 商品查询 完整测试脚本

用法：
  1. 运行 python plugin_oauth_test.py
  2. 打开浏览器访问授权URL
  3. 登录1688并授权
  4. 浏览器地址栏会变成 redirect_uri?code=xxxx
  5. 把 code 粘贴到终端
  6. 输入 1688 商品ID 查询
"""
import os, sys, json

# 请通过环境变量 ALIBABA_APP_KEY / ALIBABA_APP_SECRET 配置密钥
import os
if not os.environ.get('ALIBABA_APP_KEY') or not os.environ.get('ALIBABA_APP_SECRET'):
    print('请先设置环境变量:')
    print('  set ALIBABA_APP_KEY=your_app_key')
    print('  set ALIBABA_APP_SECRET=your_app_secret')
    sys.exit(1)

from .services.alibaba_client_v2 import (
    get_auth_url, get_access_token, get_product as get_product_v2
)

APP_KEY = os.environ['ALIBABA_APP_KEY']
APP_SECRET = os.environ['ALIBABA_APP_SECRET']

def main():
    print('=' * 60)
    print('  1688 商品查询工具')
    print('=' * 60)
    
    # Step 1: 检查是否有缓存的 token
    token_file = os.path.join(os.path.dirname(__file__), '.1688_token.json')
    access_token = None
    
    if os.path.exists(token_file):
        with open(token_file) as f:
            cached = json.load(f)
            access_token = cached.get('access_token')
            print(f'✅ 找到缓存的 token (ali_id: {cached.get("ali_id", "?")})')
    
    if not access_token:
        # Step 2: 获取授权
        redirect_uri = 'https://your-domain.com/ali-callback'
        auth_url = get_auth_url(APP_KEY, redirect_uri, 'test')
        
        print('\n🔼 请打开以下链接授权 1688：')
        print(f'\n  {auth_url}\n')
        print('（如果无法直接打开，复制到浏览器地址栏打开）')
        print('授权后会跳转到 https://your-domain.com/ali-callback?code=XXXXX')
        print()
        
        code = input('🙠 请输入授权码 code: ').strip()
        if not code:
            print('❌ 未输入 code')
            return
        
        # Step 3: 换取 access_token
        print('\n🔄 正在获取 access_token...')
        result = get_access_token(APP_KEY, APP_SECRET, code, redirect_uri)
        
        if 'error' in result:
            print(f'❌ 获取 token 失败: {result.get("error_message", result["error"])}')
            return
        
        access_token = result['access_token']
        # 缓存 token
        with open(token_file, 'w') as f:
            json.dump(result, f)
        
        print(f'✅ 授权成功！')
        print(f'   ali_id: {result.get("ali_id", "?")}')
        print(f'   access_token: {access_token[:20]}...')
        print(f'   有效期: {result.get("expires_in", 0)} 秒')
    
    # Step 4: 查询商品
    while True:
        print('\n' + '=' * 60)
        pid = input('🔳 输入 1688 商品ID (输入 q 退出): ').strip()
        if pid.lower() == 'q':
            break
        
        print(f'\n🔄 正在查询商品 {pid}...')
        result = get_product_v2(pid, access_token, APP_KEY, APP_SECRET)
        
        if 'error' in result:
            print(f'❌ 查询失败: {result.get("error_message", result["error"])}')
            continue
        
        product_info = result.get('productInfo', {})
        if not product_info:
            print(f'⚠️  API 返回空商品信息')
            print(f'   原始响应: {json.dumps(result, ensure_ascii=False, indent=2)[:500]}')
            continue
        
        print(f'\n✅ 查询成功！')
        print(f'   标题: {product_info.get("subject", "N/A")}')
        print(f'   价格: {product_info.get("saleInfo", {}).get("priceRanges", [{}])[0].get("price", "N/A")}')
        print(f'   库存: {product_info.get("saleInfo", {}).get("amountOnSale", "N/A")}')
        print(f'   类目: {product_info.get("categoryName", "N/A")}')
        print(f'   状态: {product_info.get("status", "N/A")}')
        print(f'   卖家: {product_info.get("sellerLoginId", "N/A")}')
        
        images = product_info.get('image', {}).get('images', [])
        print(f'   图片数: {len(images)}')
        
        skus = product_info.get('skuInfos', [])
        print(f'   SKU数: {len(skus)}')
        
        print(f'\n   完整数据:')
        print(json.dumps(product_info, ensure_ascii=False, indent=2)[:1000])
        
        # 保存到文件
        save_file = f'1688_product_{pid}.json'
        with open(save_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        print(f'\n💑 已保存到 {save_file}')


if __name__ == '__main__':
    main()