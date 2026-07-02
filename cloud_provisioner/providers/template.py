#!/usr/bin/env python3
"""Template Provider — Docker/LXC 模板化开通（零资质要求）

工作模式：
1. 在宿主机上创建 Docker 容器
2. 分配端口映射和资源限制
3. 执行初始化脚本
4. 返回连接信息给客户

配置项（system_config）：
  cloud.template.host       = 宿主机IP (默认本机)
  cloud.template.ssh_user   = SSH用户 (默认 root)
  cloud.template.ssh_key    = SSH私钥路径
  cloud.template.docker_cmd = docker (默认 /usr/bin/docker)
"""
import json, os, time, subprocess, threading, random, string
from datetime import datetime, timedelta
from .base import BaseProvider


class TemplateProvider(BaseProvider):
    """Docker 模板化开通适配器"""

    def __init__(self, config: dict = None):
        self.config = config or {}
        self.docker_cmd = self.config.get('docker_cmd', 'docker')
        self.host = self.config.get('host', '127.0.0.1')

    def validate_config(self, config: dict) -> tuple:
        specs = config.get('specs', {})
        cpu = specs.get('cpu', 1)
        mem = specs.get('memory_gb', 1)
        disk = specs.get('disk_gb', 10)
        if cpu < 1 or cpu > 32:
            return False, 'CPU 核心数必须在 1-32 之间'
        if mem < 0.5 or mem > 64:
            return False, '内存必须在 0.5-64 GB 之间'
        if disk < 5 or disk > 500:
            return False, '磁盘必须在 5-500 GB 之间'
        return True, ''

    def provision(self, instance_id: int, specs: dict, log_callback=None) -> dict:
        """
        在宿主机上创建 Docker 容器
        
        specs:
            cpu: int (默认 1)
            memory_gb: float (默认 1)
            disk_gb: int (默认 10)
            image: str (默认 ubuntu:22.04)
            ports: [int] 需要暴露的端口列表 (默认 [80, 22, 443])
            setup_script: str 初始化脚本名称 (默认 init_ubuntu.sh)
            domain: str 分配的域名 (可选)
        """
        cpu = specs.get('cpu', 1)
        memory_gb = specs.get('memory_gb', 1)
        disk_gb = specs.get('disk_gb', 10)
        image = specs.get('image', 'ubuntu:22.04')
        ports = specs.get('ports', [80, 22, 443])
        setup_script = specs.get('setup_script', 'init_ubuntu.sh')

        container_name = f'cloud-{instance_id}-{self._rand_str(6)}'
        host_ports = {}

        def _log(step, status='running', msg='', output=''):
            if log_callback:
                log_callback(step, status, msg, output)

        try:
            # Step 1: 拉取镜像
            _log('pull_image', 'running', f'正在拉取镜像 {image}...', '')
            self._run_cmd([self.docker_cmd, 'pull', image], timeout=120)
            _log('pull_image', 'success', f'镜像 {image} 拉取完成', '')

            # Step 2: 分配端口
            _log('alloc_ports', 'running', '正在分配端口...', '')
            port_mappings = []
            for container_port in ports:
                host_port = self._find_free_port()
                host_ports[container_port] = host_port
                port_mappings.append('-p')
                port_mappings.append(f'{host_port}:{container_port}')

            # Step 3: 创建容器
            _log('create_container', 'running', f'正在创建容器 {container_name} (CPU={cpu}, 内存={memory_gb}G)...', '')
            cmd = [
                self.docker_cmd, 'run', '-d',
                '--name', container_name,
                '--restart', 'unless-stopped',
                '--cpus', str(cpu),
                '-m', f'{memory_gb}g',
                '--memory-swap', f'{memory_gb * 2}g',
            ] + port_mappings + [image, '/bin/bash', '-c', 'while true; do sleep 3600; done']

            self._run_cmd(cmd, timeout=30)
            time.sleep(2)  # 等待容器启动

            # 验证容器状态
            inspect = self._run_cmd([self.docker_cmd, 'inspect', container_name, '--format', '{{.State.Status}}'], timeout=10)
            if 'running' not in inspect:
                raise Exception(f'容器启动失败: {inspect}')

            _log('create_container', 'success', f'容器 {container_name} 已创建', inspect)

            # Step 4: 执行初始化脚本
            root_password = self._gen_password()
            script_path = os.path.join(os.path.dirname(__file__), '..', 'scripts', setup_script)
            if os.path.exists(script_path):
                with open(script_path, 'r') as f:
                    script_content = f.read()

                _log('run_setup', 'running', f'正在执行初始化脚本: {setup_script}', '')
                script_content = script_content.replace('{{ROOT_PASSWORD}}', root_password)
                script_content = script_content.replace('{{CONTAINER_NAME}}', container_name)
                script_content = script_content.replace('{{INSTANCE_ID}}', str(instance_id))

                # 写入脚本并执行
                self._run_cmd([self.docker_cmd, 'cp', '-', f'{container_name}:/tmp/setup.sh'],
                              input_data=script_content.encode(), timeout=10)
                result = self._run_cmd(
                    [self.docker_cmd, 'exec', container_name, 'bash', '/tmp/setup.sh'],
                    timeout=120)
                _log('run_setup', 'success', f'初始化脚本执行完成', result[:1000])
            else:
                _log('run_setup', 'success', f'未找到脚本 {setup_script}，跳过初始化', '')

            # 获取容器 IP
            container_ip = self._run_cmd(
                [self.docker_cmd, 'inspect', container_name, '--format', '{{.NetworkSettings.IPAddress}}'],
                timeout=10).strip()

            return {
                'resource_id': container_name,
                'connect_info': {
                    'ip': self.host if self.host != '127.0.0.1' else container_ip,
                    'ports': host_ports,
                    'ssh_port': host_ports.get(22, ''),
                    'http_port': host_ports.get(80, ''),
                    'username': 'root',
                    'password': root_password,
                    'container_ip': container_ip,
                },
                'extra': {
                    'image': image,
                    'ports': host_ports,
                }
            }

        except Exception as e:
            _log('provision', 'failed', str(e), '')
            raise

    def get_status(self, resource_id: str) -> str:
        """查询 Docker 容器状态"""
        try:
            status = self._run_cmd(
                [self.docker_cmd, 'inspect', resource_id, '--format', '{{.State.Status}}'],
                timeout=10).strip()
            mapping = {
                'running': 'running',
                'exited': 'stopped',
                'paused': 'stopped',
                'created': 'pending',
                'dead': 'terminated',
            }
            return mapping.get(status, 'failed')
        except Exception:
            return 'terminated'

    def terminate(self, resource_id: str) -> bool:
        """销毁容器"""
        try:
            self._run_cmd([self.docker_cmd, 'stop', resource_id], timeout=30)
            self._run_cmd([self.docker_cmd, 'rm', '-v', resource_id], timeout=30)
            return True
        except Exception:
            return False

    # ── 内部辅助方法 ──

    def _run_cmd(self, cmd, timeout=30, input_data=None):
        result = subprocess.run(cmd, capture_output=True, timeout=timeout, input=input_data)
        output = (result.stdout + result.stderr).decode('utf-8', errors='replace')
        if result.returncode != 0:
            raise Exception(f'命令执行失败: {cmd[0]}... → {output[:200]}')
        return output

    def _find_free_port(self, start=10000, end=60000):
        """查找空闲端口"""
        import socket
        for _ in range(100):
            port = random.randint(start, end)
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                if s.connect_ex(('127.0.0.1', port)) != 0:
                    return port
        raise Exception('无法找到空闲端口')

    def _gen_password(self, length=16):
        chars = string.ascii_letters + string.digits + '!@#$%'
        return ''.join(random.choice(chars) for _ in range(length))

    def _rand_str(self, n=6):
        return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(n))
