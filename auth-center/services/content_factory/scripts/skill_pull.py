#!/usr/bin/env python3
"""
Hermes Skill Pull — 从 VeroRon 维洛智能 内容工厂拉取技能到本地

用法:
    # 列出可拉取的 skills
    python3 skill_pull.py list

    # 拉取所有新 skills
    python3 skill_pull.py pull

    # 拉取指定 ID
    python3 skill_pull.py pull --id 1

    # 指定目标目录 (默认 ~/.hermes/skills/)
    python3 skill_pull.py pull --dir ~/.hermes/skills/

    # 指定 Agent 类型
    python3 skill_pull.py pull --agent openclaw

配置:
    首次运行会在 ~/.hermes/skill_pull.json 创建配置，或设环境变量:
        SKILL_PULL_URL=http://agent.{DOMAIN}:8084/admin/content-factory/api/v1/skills
        SKILL_PULL_DIR=~/.hermes/skills/
"""
import json, os, sys, hashlib, argparse
from pathlib import Path

CONFIG_FILE = os.path.expanduser('~/.hermes/skill_pull.json')
DEFAULT_URL = f'http://agent.{DOMAIN}:8084/admin/content-factory/api/v1/skills'
DEFAULT_DIR = os.path.expanduser('~/.hermes/skills/')


def load_config():
    config = {
        'api_url': os.environ.get('SKILL_PULL_URL', DEFAULT_URL),
        'install_dir': os.environ.get('SKILL_PULL_DIR', DEFAULT_DIR),
        'downloaded_ids': [],
        'agent': 'hermes',
    }
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            saved = json.load(f)
            config.update(saved)
    return config


def save_config(config):
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    print(f"[✓] 配置已保存: {CONFIG_FILE}")


def list_skills(config):
    """从远程拉取可用 skill 列表"""
    import urllib.request
    url = config['api_url'] + f'?agent={config["agent"]}'
    try:
        resp = urllib.request.urlopen(url, timeout=10)
        data = json.loads(resp.read())
        if not data.get('success'):
            print(f"[✗] API 返回错误: {data}")
            return
        skills = data.get('skills', [])
        if not skills:
            print("[i] 暂无可用 skills")
            return
        print(f"\n📦 可用 Skills ({data['count']} 个 — {config['agent']}):\n")
        for s in skills:
            dl_status = '✓已拉取' if s['id'] in config['downloaded_ids'] else '○未拉取'
            print(f"  {s['id']:3d}. {dl_status} | {s['skill_name']}")
            print(f"       标题: {s['title']}")
            print(f"       描述: {s['description'][:80]}")
            print(f"       版本: {s['version']} | 推送: {s['pushed_at'][:16]}")
            print()
    except Exception as e:
        print(f"[✗] 连接失败: {e}")
        print(f"   URL: {url}")
        print(f"   确保 VeroRon 维洛智能 服务运行中")


def download_skill(config, skill_id):
    """下载单个 skill，返回 SKILL.md 内容"""
    import urllib.request
    url = f'{config["api_url"]}/{skill_id}/download'
    try:
        resp = urllib.request.urlopen(url, timeout=10)
        data = json.loads(resp.read())
        if not data.get('success'):
            print(f"[✗] 下载 skill #{skill_id} 失败: {data}")
            return None
        return data['skill']
    except Exception as e:
        print(f"[✗] 下载失败 #{skill_id}: {e}")
        return None


def install_skill(skill, install_dir):
    """将 skill 写入本地目录"""
    name = skill['skill_name']
    category = skill.get('category', 'content')
    content = skill['skill_content']

    # 目标路径: ~/.hermes/skills/<category>/<name>/SKILL.md
    target_dir = os.path.join(install_dir, category, name)
    os.makedirs(target_dir, exist_ok=True)
    target_file = os.path.join(target_dir, 'SKILL.md')

    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)

    # 写入元数据
    meta = {
        'source': 'VeroRon 维洛智能',
        'skill_id': skill['id'],
        'pushed_at': skill.get('pushed_at', ''),
        'installed_at': __import__('datetime').datetime.now().isoformat(),
        'version': skill.get('version', '1.0'),
        'agent': skill.get('target_agent', 'hermes'),
    }
    with open(os.path.join(target_dir, '.skill_meta.json'), 'w') as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    return target_file


def pull_skills(config, skill_id=None):
    """拉取并安装 skills"""
    import urllib.request

    # 获取列表
    url = config['api_url'] + f'?agent={config["agent"]}'
    try:
        resp = urllib.request.urlopen(url, timeout=10)
        data = json.loads(resp.read())
        if not data.get('success'):
            print(f"[✗] API 错误: {data}")
            return
        skills = data.get('skills', [])
    except Exception as e:
        print(f"[✗] 连接失败: {e}")
        return

    if skill_id:
        skills = [s for s in skills if s['id'] == skill_id]
        if not skills:
            print(f"[✗] 未找到 skill #{skill_id}")
            return

    new_count = 0
    for s in skills:
        sid = s['id']
        if sid in config['downloaded_ids'] and not skill_id:
            continue  # 跳过已拉取的

        print(f"  → 下载: {s['skill_name']} (id={sid}) ...", end=' ')
        skill = download_skill(config, sid)
        if not skill:
            print('失败')
            continue

        target_file = install_skill(skill, config['install_dir'])
        if sid not in config['downloaded_ids']:
            config['downloaded_ids'].append(sid)
        new_count += 1
        print(f'OK → {target_file}')

    save_config(config)
    print(f"\n[✓] 完成: 新增 {new_count} 个 skills")


def main():
    parser = argparse.ArgumentParser(description='Hermes Skill Pull — 拉取内容工厂 skills')
    parser.add_argument('action', nargs='?', default='list',
                        choices=['list', 'pull'],
                        help='list: 列出可用 skills; pull: 拉取安装')
    parser.add_argument('--id', type=int, help='指定 skill ID (仅拉取单个)')
    parser.add_argument('--dir', help='安装目录 (默认 ~/.hermes/skills/)')
    parser.add_argument('--agent', default='hermes', help='目标 agent (hermes/openclaw)')
    parser.add_argument('--url', help='API URL (默认配置中的)')

    args = parser.parse_args()
    config = load_config()

    if args.dir:
        config['install_dir'] = os.path.expanduser(args.dir)
    if args.agent:
        config['agent'] = args.agent
    if args.url:
        config['api_url'] = args.url

    if args.action == 'list':
        list_skills(config)
    elif args.action == 'pull':
        pull_skills(config, args.id)


if __name__ == '__main__':
    main()
