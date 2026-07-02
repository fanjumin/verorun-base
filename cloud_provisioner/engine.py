#!/usr/bin/env python3
"""Provisioner Engine — 自动开通编排核心

工作流程：
  1. 接收开通请求
  2. 验证配置合法性
  3. 创建 Provider 适配器
  4. 调用 provider.provision() 创建资源
  5. 轮询状态直到 running
  6. 更新数据库记录
  7. 记录开通日志
  8. 返回连接信息

AI 集成：
  - 通过 Shop Agent 的指令控制台调用
  - 示例: "给我开通一台 2C4G 的云服务器"
  - Agent 解析规格 → 创建商品 → 下单 → 调用引擎开通
"""
import json, time, threading, logging
from datetime import datetime, timedelta
from .models import create_instance, update_instance, add_log, get_instance
from .providers import get_provider

logger = logging.getLogger(__name__)


class ProvisionerEngine:
    """自动开通编排引擎"""

    def __init__(self, provider_type='template', provider_config=None):
        self.provider = get_provider(provider_type, provider_config or {})

    def provision(self, order_data: dict) -> dict:
        """
        执行自动开通
        
        order_data:
            order_id: str           — 订单号
            user_id: int            — 用户ID
            product_id: int         — 商品ID
            product_title: str      — 商品名称
            product_config: dict    — 商品配置 (规格/镜像/脚本等)
            service_type: str       — vps/oss/cdn/rds
            provider: str           — template/aliyun
            expire_at: str          — 到期时间
            auto_renew: bool        — 自动续费
        """
        product_config = order_data.get('product_config', {})
        specs = product_config.get('specs', {})
        service_type = order_data.get('service_type', product_config.get('service_type', 'vps'))
        provider_type = order_data.get('provider', product_config.get('provider', 'template'))

        # Step 0: 创建实例记录
        instance_id = create_instance({
            'order_id': order_data['order_id'],
            'user_id': order_data['user_id'],
            'product_id': order_data['product_id'],
            'product_title': order_data.get('product_title', ''),
            'provider': provider_type,
            'service_type': service_type,
            'specs': specs,
            'expire_at': order_data.get('expire_at'),
            'auto_renew': int(order_data.get('auto_renew', False)),
            'metadata': product_config.get('metadata', {}),
        })

        result = {'instance_id': instance_id, 'status': 'pending', 'connect_info': None, 'error': None}

        def _log(step, status='running', msg='', output=''):
            add_log(instance_id, step, status, msg, output)
            update_instance(instance_id, provision_log=f'[{step}] {msg[:200]}')

        try:
            _log('validate', 'running', '正在验证配置...', '')
            valid, err = self.provider.validate_config({'specs': specs})
            if not valid:
                raise ValueError(f'配置验证失败: {err}')
            _log('validate', 'success', '配置验证通过', '')

            # Step 1: 更新状态为 provisioning
            update_instance(instance_id, status='provisioning')
            _log('provision', 'running', f'开始开通 (provider={provider_type}, type={service_type})', json.dumps(specs))

            # Step 2: 创建 Provider 并执行开通
            provider = get_provider(provider_type, product_config.get('provider_config', {}))
            provision_result = provider.provision(instance_id, specs, log_callback=_log)

            # Step 3: 更新实例信息
            connect_info = provision_result.get('connect_info', {})
            resource_id = provision_result.get('resource_id', '')
            extra = provision_result.get('extra', {})

            update_instance(
                instance_id,
                status='running',
                resource_id=resource_id,
                connect_info=connect_info,
                metadata=extra
            )

            _log('notify', 'success',
                 f'开通完成！资源ID: {resource_id}, IP: {connect_info.get("ip", "")}',
                 json.dumps(connect_info))

            result['status'] = 'running'
            result['connect_info'] = connect_info
            result['resource_id'] = resource_id

        except Exception as e:
            logger.error(f'开通失败 (instance={instance_id}): {e}')
            update_instance(instance_id, status='failed')
            _log('failed', 'failed', str(e)[:500], '')
            result['status'] = 'failed'
            result['error'] = str(e)

        return result

    def get_status(self, instance_id: int) -> str:
        """查询实例状态"""
        inst = get_instance(instance_id)
        if not inst:
            return 'not_found'
        if inst['status'] in ('running', 'stopped', 'terminated', 'failed'):
            return inst['status']
        # 对于 pending/provisioning，查询 Provider 获取实时状态
        provider_type = inst.get('provider', 'template')
        resource_id = inst.get('resource_id', '')
        if resource_id:
            try:
                provider = get_provider(provider_type, {})
                real_status = provider.get_status(resource_id)
                if real_status != inst['status']:
                    update_instance(instance_id, status=real_status)
                return real_status
            except Exception:
                return inst['status']
        return inst['status']

    def terminate(self, instance_id: int) -> bool:
        """销毁实例"""
        inst = get_instance(instance_id)
        if not inst:
            return False
        provider_type = inst.get('provider', 'template')
        resource_id = inst.get('resource_id', '')
        if resource_id:
            try:
                provider = get_provider(provider_type, {})
                success = provider.terminate(resource_id)
                if success:
                    update_instance(instance_id, status='terminated')
                    add_log(instance_id, 'terminate', 'success', '资源已销毁', '')
                return success
            except Exception as e:
                add_log(instance_id, 'terminate', 'failed', str(e), '')
                return False
        else:
            update_instance(instance_id, status='terminated')
            return True
