#!/usr/bin/env python3
"""
阿里巴巴商品AI内容生成器
功能：1. 商品标题优化
2. 营销文案重写
3. 集成 agent_matrix 引擎
4. 支持多种AI供应商（DeepSeek/OpenAI/本地模型）
"""

import json
import logging
from typing import Dict, Any, Optional, Tuple
import sys
import os

# 添加agent_matrix路径
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'agent_matrix'))

from ..config import config

logger = logging.getLogger(__name__)

class AIProcessor:
    """AI内容处理器"""
    
    def __init__(self, provider: str = None, model: str = None):
        """初始化AI处理器"""
        self.provider = provider or config['ai']['provider']
        self.model = model or config['ai']['model']
        self.engine = None
        self._init_engine()
    
    def _init_engine(self) -> None:
        """初始化AI引擎"""
        try:
            from agent_matrix.engine import AIEngine
            
            # 构建agent配置
            agent_config = {
                'provider': self.provider,
                'model_name': self.model,
                'api_key_ref': f'{self.provider}_api_key',
                'system_prompt': '你是一个专业的电商文案优化专家，擅长优化商品标题和描述，使其更具吸引力和营销力。',
            }
            
            self.engine = AIEngine(agent_config)
            
            if not self.engine.client:
                logger.warning(f"AI引擎初始化失败，provider={self.provider}, model={self.model}")
                self.engine = None
            else:
                logger.info(f"AI引擎初始化成功: {self.provider}/{self.model}")
                
        except ImportError as e:
            logger.error(f"无法导入agent_matrix: {e}")
            self.engine = None
        except Exception as e:
            logger.error(f"AI引擎初始化失败: {e}")
            self.engine = None
    
    def _call_ai(self, prompt: str, max_tokens: int = None, temperature: float = None) -> Tuple[bool, Optional[str]]:
        """调用AI接口"""
        if not self.engine or not self.engine.client:
            return False, _"AI Engine Not Initialized"
        
        try:
            from openai import OpenAIError
            
            # 准备消息
            messages = [
                {"role": "system", "content": self.engine.system_prompt},
                {"role": "user", "content": prompt},
            ]
            
            # 调用参数
            params = {
                "model": self.model,
                "messages": messages,
                "max_tokens": max_tokens or config['ai']['max_tokens'],
                "temperature": temperature or config['ai']['temperature'],
            }
            
            # 调用AI
            response = self.engine.client.chat.completions.create(**params)
            
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content.strip()
                return True, content
            else:
                return False, _"AI returned empty content"
                
        except OpenAIError as e:
            logger.error(f"OpenAI调用错误: {e}")
            return False, f_"AI call failed: {e}"
        except Exception as e:
            logger.error(f_"AI call exception: {e}")
            return False, f_"AI call exception: {e}"
    
    def optimize_title(self, original_title: str, category: str = None, keywords: str = None) -> Tuple[bool, Optional[str]]:
        """优化商品标题"""
        if not original_title or len(original_title.strip()) == 0:
            return False, _"Original title cannot be empty"
        
        # 构建提示词
        prompt = config['ai']['title_prompt'].format(title=original_title)
        
        if category:
            prompt += f"\n商品类目: {category}"
        
        if keywords:
            prompt += f"\n关键词: {keywords}"
        
        prompt += "\n请输出优化后的标题，不要添加任何解释。"
        
        # 调用AI
        success, optimized = self._call_ai(prompt, max_tokens=config['ai']['title_max_length'])
        
        if success and optimized:
            # 清理结果
            optimized = optimized.strip().strip('"').strip("'")
            
            # 检查长度
            if len(optimized) > config['ai']['title_max_length']:
                optimized = optimized[:config['ai']['title_max_length']] + "..."
            
            return True, optimized
        
        return success, optimized
    
    def generate_title_options(self, product_info: Dict[str, Any]) -> Tuple[bool, Optional[list]]:
        """
        生成多版本标题选项（专业型、吸引力型、简洁型）
        返回: [(id, title, style, reason), ...]
        """
        original_title = product_info.get('title', '')
        description = product_info.get('description', '')
        specs = product_info.get('specs', {})
        category = product_info.get('category', '')
        
        if not original_title:
            return False, _"Original title cannot be empty"
        
        specs_text = json.dumps(specs, ensure_ascii=False, indent=2) if specs else _'None'
        
        prompt = f"""你是一个电商标题优化专家。请根据以下1688商品信息，生成 3 个优化后的商品标题。
原始标题：{original_title}
商品描述：{description[:200] if description else _'None'}
商品规格：{specs_text}
商品类目：{category}

要求：
1. 标题长度 20-40 字
2. 包含核心卖点和关键词
3. SEO 友好，适合搜索
4. 符合中国电商平台规范，不包含违规词
5. 3 个标题风格不同：①专业型 ②吸引力型 ③简洁型

请以 JSON 格式返回，不要包含任何其他文本：
[{{"id":1,"title":_"Title 1","style":"professional","reason":_"Select reason..."}}, ...]"""
        
        success, response = self._call_ai(prompt, max_tokens=800, temperature=0.8)
        
        if not success:
            return False, response
        
        # 尝试从AI响应中提取JSON
        try:
            # 先尝试直接解析
            options = json.loads(response)
        except json.JSONDecodeError:
            # 尝试从markdown代码块中提取
            import re
            json_match = re.search(r'```(?:json)?\s*(\[[\s\S]*?\])\s*```', response)
            if json_match:
                try:
                    options = json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    return False, _"Invalid JSON format returned by AI"
            else:
                return False, _"Invalid JSON format returned by AI"
        
        if not isinstance(options, list) or len(options) == 0:
            return False, _"AI did not generate valid title options"
        
        # 规范化输出
        result = []
        for opt in options:
            result.append({
                'id': opt.get('id', len(result) + 1),
                'title': opt.get('title', ''),
                'style': opt.get('style', 'normal'),
                'reason': opt.get('reason', ''),
            })
        
        return True, result
    
    def optimize_description(self, original_description: str, product_features: Dict[str, Any] = None) -> Tuple[bool, Optional[str]]:
        """优化商品描述"""
        if not original_description or len(original_description.strip()) == 0:
            return False, _"Original description cannot be empty"
        
        # 构建提示词
        prompt = config['ai']['description_prompt'].format(description=original_description)
        
        if product_features:
            features_text = json.dumps(product_features, ensure_ascii=False)
            prompt += f"\n商品特征: {features_text}"
        
        prompt += "\n请输出优化后的描述，突出产品卖点，适合电商平台展示。"
        
        # 调用AI
        success, optimized = self._call_ai(prompt)
        
        if success and optimized:
            # 清理结果
            optimized = optimized.strip()
            
            # 检查长度
            max_length = config['ai']['description_max_length']
            if len(optimized) > max_length:
                optimized = optimized[:max_length] + "..."
            
            return True, optimized
        
        return success, optimized
    
    def generate_marketing_copy(self, product_info: Dict[str, Any]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """生成营销文案（标题+描述+卖点）"""
        result = {
            'original_title': product_info.get('title', ''),
            'original_description': product_info.get('description', ''),
            'optimized_title': '',
            'optimized_description': '',
            'selling_points': [],
            'tags': [],
        }
        
        # 优化标题
        if product_info.get('title'):
            success, optimized_title = self.optimize_title(
                product_info['title'],
                product_info.get('category'),
                product_info.get('keywords')
            )
            if success:
                result['optimized_title'] = optimized_title
        
        # 优化描述
        if product_info.get('description'):
            success, optimized_description = self.optimize_description(
                product_info['description'],
                product_info.get('specs', {})
            )
            if success:
                result['optimized_description'] = optimized_description
        
        # 生成卖点
        if product_info.get('specs') or product_info.get('features'):
            success, selling_points = self._generate_selling_points(product_info)
            if success:
                result['selling_points'] = selling_points
        
        # 生成标签
        if product_info.get('title') or product_info.get('category'):
            success, tags = self._generate_tags(product_info)
            if success:
                result['tags'] = tags
        
        return True, result
    
    def _generate_selling_points(self, product_info: Dict[str, Any]) -> Tuple[bool, Optional[list]]:
        """生成商品卖点"""
        prompt = f"请为以下商品生成3-5个核心卖点：\n"
        prompt += f"商品名称: {product_info.get('title', '')}\n"
        
        if product_info.get('description'):
            prompt += f"商品描述: {product_info.get('description', '')}\n"
        
        if product_info.get('specs'):
            specs_text = json.dumps(product_info['specs'], ensure_ascii=False)
            prompt += f"商品规格: {specs_text}\n"
        
        prompt += "请以列表形式输出卖点，每个卖点用短句描述，不要编号。"
        
        success, response = self._call_ai(prompt, max_tokens=300)
        
        if success:
            # 解析卖点列表
            selling_points = []
            lines = response.strip().split('\n')
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith(('1.', '2.', '3.', '4.', '5.', '-', '*', '•')):
                    # 移除常见前缀
                    for prefix in ['- ', '* ', '•', '· ']:
                        if line.startswith(prefix):
                            line = line[len(prefix):]
                            break
                    selling_points.append(line)
                elif line and line.startswith(('- ', '* ', '•', '· ')):
                    selling_points.append(line[2:].strip())
            
            # 限制数量
            selling_points = selling_points[:5]
            
            return True, selling_points
        
        return False, []
    
    def _generate_tags(self, product_info: Dict[str, Any]) -> Tuple[bool, Optional[list]]:
        """生成商品标签"""
        prompt = f"请为以下商品生成5-8个相关标签：\n"
        prompt += f"商品名称: {product_info.get('title', '')}\n"
        
        if product_info.get('category'):
            prompt += f"商品类目: {product_info.get('category', '')}\n"
        
        if product_info.get('description'):
            # 只取描述的前100字
            desc = product_info['description'][:100] + "..." if len(product_info['description']) > 100 else product_info['description']
            prompt += f"商品描述: {desc}\n"
        
        prompt += "请输出标签，用逗号分隔，不要添加任何解释。"
        
        success, response = self._call_ai(prompt, max_tokens=100)
        
        if success:
            # 解析标签
            tags = []
            for tag in response.strip().split(','):
                tag = tag.strip()
                if tag:
                    tags.append(tag)
            
            # 限制数量
            tags = tags[:8]
            
            return True, tags
        
        return False, []
    
    def batch_process(self, products: list) -> Dict[str, Any]:
        """批量处理商品"""
        results = {
            'total': len(products),
            'processed': 0,
            'success': 0,
            'failed': 0,
            'results': [],
        }
        
        for i, product in enumerate(products):
            try:
                logger.info(f"处理商品 {i+1}/{len(products)}: {product.get('title', _'Unknown')}")
                
                success, result = self.generate_marketing_copy(product)
                
                if success:
                    results['success'] += 1
                    results['results'].append({
                        'product_id': product.get('product_id', f'unknown_{i}'),
                        'success': True,
                        'result': result,
                    })
                else:
                    results['failed'] += 1
                    results['results'].append({
                        'product_id': product.get('product_id', f'unknown_{i}'),
                        'success': False,
                        'error': _'AI Processing Failed',
                    })
                
                results['processed'] += 1
                
            except Exception as e:
                logger.error(f"处理商品失败: {e}")
                results['failed'] += 1
                results['results'].append({
                    'product_id': product.get('product_id', f'unknown_{i}'),
                    'success': False,
                    'error': str(e),
                })
                results['processed'] += 1
        
        return results

# 全局AI处理器实例
_ai_processor = None

def get_ai_processor() -> AIProcessor:
    """获取AI处理器单例"""
    global _ai_processor
    if _ai_processor is None:
        _ai_processor = AIProcessor()
    return _ai_processor

def is_ai_available() -> bool:
    """检查AI服务是否可用"""
    processor = get_ai_processor()
    return processor.engine is not None

if __name__ == "__main__":
    # 测试AI处理器
    import pprint
    
    print(_"AI Processor Test")
    
    processor = AIProcessor()
    
    if not processor.engine:
        print("AI引擎初始化失败，请检查配置")
    else:
        print(f_"AI Engine Initialized Successfully: {processor.provider}/{processor.model}")
        
        # 测试标题优化
        print("\n1. 标题优化测试...")
        original_title = _"2024 New Smartphone 6.7-inch Screen 5000mAh Battery 128GB Storage"
        success, optimized = processor.optimize_title(original_title, _"Mobile Electronics", _"Smartphone, Large Screen, Long Battery Life")
        print(f_"   Original Title: {original_title}")
        print(f_"   Optimization Result: {'Success' if success else 'Failed'} - {optimized}")
        
        # 测试描述优化
        print("\n2. 描述优化测试...")
        original_desc = _"This is a new smartphone with a large screen, large battery capacity, and large storage space."
        success, optimized_desc = processor.optimize_description(original_desc)
        print(f_"   Original Description: {original_desc}")
        print(f_"   Optimization Result: {'Success' if success else 'Failed'} - {optimized_desc[:50]}...")
        
        # 测试营销文案生成
        print("\n3. 营销文案生成测试...")
        product_info = {
            'title': _"Wireless Bluetooth Earphones Noise Cancellation Sports",
            'description': "无线蓝牙耳机，支持降噪，适合运动使用。",
            'category': _"Digital accessories",
            'specs': {_"Bluetooth Version": "5.0", _"Endurance": _"20 Hours", _"Waterproof rating": "IPX4"},
        }
        success, marketing_copy = processor.generate_marketing_copy(product_info)
        print(f_"   Generation Result: {'Success' if success else 'Failed'}")
        if success:
            pprint.pprint(marketing_copy)
        
        print("\n4. AI服务可用性检查")
        print(f_"   AI Available: {is_ai_available()}")
