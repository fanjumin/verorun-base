#!/usr/bin/env python3
"""
EasyKai 本地媒体生产器 — Windows 版
FFmpeg/MoviePy 本地渲染 + 自动推送到 easykai 服务器

用法:
  python media_producer.py upload D:\videos\myvideo.mp4
  python media_producer.py compress D:\videos\myvideo.mp4 --width 1080
  python media_producer.py slideshow img1.jpg img2.jpg --audio bgm.mp3
  python media_producer.py watermark D:\videos\myvideo.mp4 --text "品牌名"

前置准备（一次性）:
  1. 安装 Python 3.10+: https://www.python.org/downloads/
  2. 安装 FFmpeg: https://ffmpeg.org/download.html (选 Windows builds)
     解压后将 bin 目录加入系统 PATH
  3. 安装 Python 依赖:
     pip install moviepy pillow requests paramiko

服务器信息（硬编码，改了再改脚本）:
  主机: 100.124.0.103
  用户: easykai
  密码: ***REMOVED***
"""

import argparse
import os
import sys
import subprocess
import tempfile
import json
from pathlib import Path

# ── 服务器配置 ────────────────────────────────────────
SSH_HOST = "100.124.0.103"
SSH_USER = "easykai"
SSH_PASS = "***REMOVED***"
SERVER_URL = deploy.url('agent') + ':8084'"
MEDIA_LIB_API = f"{SERVER_URL}/admin/media-library/upload"

# ── SSH / Token ────────────────────────────────────────

def _ssh_exec(cmd: str) -> str:
    """在服务器上执行命令，返回 stdout"""
    import paramiko
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15)
    _, stdout, stderr = c.exec_command(cmd, timeout=15)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    c.close()
    return out


def _ssh_put(local_path: str, remote_path: str):
    """上传文件到服务器"""
    import paramiko
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(SSH_HOST, username=SSH_USER, password=SSH_PASS, timeout=15)
    sftp = c.open_sftp()
    sftp.put(local_path, remote_path)
    sftp.close()
    c.close()


def _get_admin_token() -> str:
    """获取 admin JWT token"""
    token = os.environ.get("ADMIN_TOKEN")
    if token:
        return token

    print("🔑 连接服务器获取 Token ...")

    # 获取 admin 进程 PID
    pid = _ssh_exec("pgrep -f 'python3 -B app.py 8084' | head -1")
    if not pid:
        raise RuntimeError("找不到 admin 进程 (8084)")

    # 在服务器上生成 token
    getter = f'''import os,json,time,hmac,hashlib,base64,sqlite3
pid="{pid}"
with open("/proc/"+pid+"/environ") as f:
    env=dict(x.split("=",1) for x in f.read().split("\\x00") if "=" in x)
secret=env.get("JWT_SECRET","")
db=os.environ.get("DB_PATH","/path/to/deployment/data/verorun.db")
conn=sqlite3.connect(db)
u=conn.execute("SELECT id,email FROM users WHERE is_admin=1 LIMIT 1").fetchone()
conn.close()
h=base64.urlsafe_b64encode(json.dumps({{"alg":"HS256","typ":"JWT"}}).encode()).rstrip(b"=").decode()
d={{"user_id":u[0],"email":u[1],"is_admin":1,"exp":int(time.time())+86400}}
p=base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
m=h+"."+p
s=base64.urlsafe_b64encode(hmac.new(secret.encode(),m.encode(),hashlib.sha256).digest()).rstrip(b"=").decode()
print(m+"."+s)
'''
    token = _ssh_exec(f"python3 -c '{getter}'")
    if not token:
        raise RuntimeError("Token 生成失败")
    print("   ✅ Token 已获取 (有效期24h)")
    return token


# ── 上传 ───────────────────────────────────────────────

def _upload(filepath: str, original_name: str = "") -> dict:
    """上传文件到服务器媒体库"""
    import requests
    token = _get_admin_token()
    name = original_name or os.path.basename(filepath)
    with open(filepath, 'rb') as f:
        resp = requests.post(
            MEDIA_LIB_API,
            files={'file': (name, f)},
            headers={'Authorization': f'Bearer {token}'},
            timeout=300
        )
    return resp.json()


# ── FFmpeg ─────────────────────────────────────────────

def run_ffmpeg(args: list, description: str = "FFmpeg"):
    """运行 FFmpeg（Windows 兼容）"""
    print(f"🎬 {description} ...")
    # Windows 上 ffmpeg 可能在 PATH 里
    ffmpeg_exe = "ffmpeg"
    # 使用列表参数避免 shell 转义问题
    cmd = [ffmpeg_exe, "-y"] + args
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ FFmpeg 失败:\n{result.stderr[-500:]}")
        sys.exit(1)
    print(f"   ✅ 完成")


# ── 命令实现 ───────────────────────────────────────────

def cmd_upload(args):
    """直接上传视频/图片"""
    filepath = args.file
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        sys.exit(1)

    size_mb = os.path.getsize(filepath) / 1024 / 1024
    print(f"📤 上传: {os.path.basename(filepath)} ({size_mb:.1f} MB)")

    result = _upload(filepath)
    if result.get('success'):
        d = result['data']
        print(f"✅ 上传成功!")
        print(f"   ID: {d['id']}  文件: {d['original_name']}")
        print(f"   类型: {d['mime_type']}  大小: {d['file_size'] / 1024:.0f} KB")
        print(f"   📋 后台: {SERVER_URL}/admin → 全媒体创作 → 多媒体 → 发布管理")
    else:
        print(f"❌ 失败: {result.get('error', '未知')}")
        sys.exit(1)


def cmd_compress(args):
    """压缩视频后上传"""
    filepath = args.file
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        sys.exit(1)

    size_mb = os.path.getsize(filepath) / 1024 / 1024
    print(f"📥 输入: {os.path.basename(filepath)} ({size_mb:.1f} MB)")

    fd, out_path = tempfile.mkstemp(suffix='.mp4')
    os.close(fd)

    ff_args = ['-i', filepath, '-c:v', 'libx264', '-preset', 'medium']
    if args.width:
        ff_args += ['-vf', f'scale={args.width}:-2']
    if args.bitrate:
        ff_args += ['-b:v', args.bitrate]
    ff_args += ['-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', out_path]
    run_ffmpeg(ff_args, "压缩视频")

    out_mb = os.path.getsize(out_path) / 1024 / 1024
    print(f"   压缩后: {out_mb:.1f} MB")

    result = _upload(out_path, args.title or os.path.basename(filepath))
    os.unlink(out_path)

    if result.get('success'):
        print(f"✅ 已推送到发布管理!")


def cmd_slideshow(args):
    """图片幻灯片 → 视频 → 上传"""
    try:
        from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
    except ImportError:
        print("❌ 需要 MoviePy: pip install moviepy")
        sys.exit(1)

    duration = args.duration or 3
    images = args.images

    for img in images:
        if not os.path.exists(img):
            print(f"❌ 图片不存在: {img}")
            sys.exit(1)

    print(f"🎞️  生成幻灯片 ({len(images)} 张, 每张 {duration}s)")

    clips = []
    for img in images:
        try:
            clip = ImageClip(img).with_duration(duration)
            clip = clip.resized(height=1080)
            clips.append(clip)
        except Exception as e:
            print(f"⚠️  跳过 {img}: {e}")

    if not clips:
        print("❌ 没有有效图片")
        sys.exit(1)

    video = concatenate_videoclips(clips, method="compose")

    if args.audio and os.path.exists(args.audio):
        print(f"🎵 添加音频: {os.path.basename(args.audio)}")
        try:
            audio = AudioFileClip(args.audio)
            if audio.duration < video.duration:
                from moviepy import afx
                audio = audio.with_effects([afx.AudioLoop(duration=video.duration)])
            else:
                audio = audio.subclipped(0, video.duration)
            video = video.with_audio(audio)
        except Exception as e:
            print(f"⚠️  音频失败: {e}")

    fd, out_path = tempfile.mkstemp(suffix='.mp4')
    os.close(fd)
    video.write_videofile(out_path, fps=24, codec='libx264', audio_codec='aac', logger=None)
    print(f"   ✅ 视频: {out_path}")

    result = _upload(out_path, args.title or f"slideshow_{len(images)}imgs.mp4")
    os.unlink(out_path)

    if result.get('success'):
        print(f"✅ 已推送!")


def cmd_watermark(args):
    """添加文字水印"""
    filepath = args.file
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        sys.exit(1)

    text = args.text
    print(f"💧 水印: \"{text}\" → {os.path.basename(filepath)}")

    fd, out_path = tempfile.mkstemp(suffix='.mp4')
    os.close(fd)

    font_size = args.fontsize or 24
    pos = {
        'top-left':     'x=10:y=10',
        'top-right':    'x=w-tw-10:y=10',
        'bottom-left':  'x=10:y=h-th-10',
        'bottom-right': 'x=w-tw-10:y=h-th-10',
        'center':       'x=(w-tw)/2:y=(h-th)/2',
    }.get(args.position or 'bottom-right', 'x=w-tw-10:y=h-th-10')

    # Windows 用 fontfile 或不指定让 FFmpeg 用默认字体
    vf = f"drawtext=text='{text}':fontsize={font_size}:fontcolor=white@0.7:{pos}:box=1:boxcolor=black@0.3:boxborderw=5"
    run_ffmpeg(['-i', filepath, '-vf', vf, '-c:a', 'copy', out_path], "添加水印")

    result = _upload(out_path, args.title or os.path.basename(filepath))
    os.unlink(out_path)

    if result.get('success'):
        print(f"✅ 已推送!")


# ── 主入口 ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="EasyKai 本地媒体生产器 (Windows)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python media_producer.py upload D:\\videos\\demo.mp4
  python media_producer.py compress D:\\videos\\demo.mp4 --width 1080 --bitrate 2M
  python media_producer.py slideshow img1.jpg img2.jpg --audio bgm.mp3
  python media_producer.py watermark D:\\videos\\demo.mp4 --text "EasyKai"
        """
    )
    sub = parser.add_subparsers(dest='cmd', help='命令')

    p_up = sub.add_parser('upload', help='直接上传')
    p_up.add_argument('file')
    p_up.set_defaults(func=cmd_upload)

    p_cp = sub.add_parser('compress', help='压缩上传')
    p_cp.add_argument('file')
    p_cp.add_argument('--width', type=int)
    p_cp.add_argument('--bitrate')
    p_cp.add_argument('--title')
    p_cp.set_defaults(func=cmd_compress)

    p_ss = sub.add_parser('slideshow', help='图片幻灯片')
    p_ss.add_argument('images', nargs='+')
    p_ss.add_argument('--audio')
    p_ss.add_argument('--duration', type=float, default=3)
    p_ss.add_argument('--title')
    p_ss.set_defaults(func=cmd_slideshow)

    p_wm = sub.add_parser('watermark', help='添加水印')
    p_wm.add_argument('file')
    p_wm.add_argument('--text', required=True)
    p_wm.add_argument('--fontsize', type=int, default=24)
    p_wm.add_argument('--position', default='bottom-right',
                       choices=['top-left','top-right','bottom-left','bottom-right','center'])
    p_wm.add_argument('--title')
    p_wm.set_defaults(func=cmd_watermark)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == '__main__':
    main()
