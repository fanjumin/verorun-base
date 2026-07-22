#!/usr/bin/env python3
"""安全表达式评估器 - 使用 AST 解析限制允许的操作"""
import ast

def safe_eval(expression: str, local_vars: dict) -> bool:
    """
    安全地评估布尔表达式
    
    允许的操作：
    - 比较运算符: <, <=, >, >=, ==, !=, in, not in, is, is not
    - 逻辑运算符: and, or, not
    - 算术运算符: +, -, *, /, %, //, **
    - 内置常量: True, False, None
    - 访问 local_vars 中的变量
    
    禁止的操作：
    - 函数调用
    - 属性访问（除了基本类型的 __eq__ 等）
    - 下标访问
    - lambda 表达式
    - 导入
    """
    try:
        # 解析表达式为 AST
        tree = ast.parse(expression, mode='eval')
        
        # 遍历 AST 节点进行安全检查
        for node in ast.walk(tree):
            # 禁止函数调用
            if isinstance(node, ast.Call):
                raise ValueError(f"Function calls are not allowed: {ast.dump(node)}")
            
            # 禁止属性访问（防止 __class__.__base__ 等攻击）
            if isinstance(node, ast.Attribute):
                raise ValueError(f"Attribute access is not allowed: {ast.dump(node)}")
            
            # 禁止下标访问
            if isinstance(node, ast.Subscript):
                raise ValueError(f"Subscript access is not allowed: {ast.dump(node)}")
            
            # 禁止 lambda 表达式
            if isinstance(node, ast.Lambda):
                raise ValueError(f"Lambda expressions are not allowed")
            
            # 禁止导入
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                raise ValueError(f"Imports are not allowed")
            
            # 禁止复杂表达式
            if isinstance(node, (ast.DictComp, ast.SetComp, ast.ListComp, ast.GeneratorExp)):
                raise ValueError(f"Comprehensions are not allowed")
        
        # 检查危险的标识符
        forbidden_names = [
            '__class__', '__base__', '__subclasses__', '__globals__', '__builtins__',
            '__dict__', '__getattr__', '__setattr__', '__reduce__', '__reduce_ex__',
            '__getattribute__', '__bases__', '__mro__', '__init__', 'eval', 'exec',
            'compile', 'open', '__import__', 'getattr', 'setattr', 'hasattr', 'delattr'
        ]
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and node.id in forbidden_names:
                raise ValueError(f"Forbidden name: {node.id}")
        
        # 使用空的 __builtins__ 进行评估
        return bool(eval(compile(tree, '<string>', 'eval'), {"__builtins__": {}}, local_vars))
    
    except SyntaxError as e:
        raise ValueError(f"Invalid expression syntax: {e}")
    except Exception as e:
        raise ValueError(f"Expression evaluation error: {e}")
