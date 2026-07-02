#!/usr/bin/env python3
"""
本地媒体生产器 — FFmpeg/MoviePy 本地渲染 + 自动推送到 easykai 服务器

用法:
  # 直接上传视频
  python3 media_producer.py upload /path/to/video.mp4

  # 视频压缩后上传（指定分辨率/码率）
  python3 media_producer.py compress /path/to/video.mp4 --width 1080 --bitrate 2M

  # 从图片生成幻灯片视频 + 音频
  python3 media_producer.py slideshow image1.jpg image2.jpg --audio bgm.mp3 --duration 3

  # 添加水印后上传
  python3 media_producer.py watermark /path/to/video.mp4 --text "EasyKai"

环境变量:
  ADMIN_TOKEN   管理后台 JWT token（会自动生成，手动指定可跳过登录）

依赖:
  pip3 install --break-system-packages moviepy pillow requests
"""

import argparse
import os
import sys
import subprocess
import tempfile
import shutil
import json
from pathlib import Path

# ── 配置 ──────────────────────────────────────────────
SERVER = deploy.url('agent') + ':8084'"
MEDIA_LIB_API = f"{SERVER}/admin/media-library/upload"

# ── Token 管理 ─────────────────────────────────────────

def _get_admin_token():
    """从环境变量读取或自动生成 admin JWT token"""
    token = os.environ.get("ADMIN_TOKEN")
    if token:
        return token

    print("🔑 生成 admin JWT token ...")

    # 获取 admin 进程 PID
    PID = subprocess.run(
        "sshpass -p '***REMOVED***' ssh -o StrictHostKeyChecking=no easykai@100.124.0.103 "
        "\"pgrep -f 'python3 -B app.py 8084' | head -1\"",
        shell=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()
    if not PID:
        raise RuntimeError("找不到 admin 进程 (8084)")

    # 本地写脚本 → scp 到服务器 → 执行
    script = f'''import os,json,time,hmac,hashlib,base64,sqlite3
pid="{PID}"
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
    # Write locally
    with open("/tmp/gentoken.py", "w") as f:
        f.write(script)
    # SCP to server
    subprocess.run(
        f"sshpass -p '***REMOVED***' scp -o StrictHostKeyChecking=no "
        f"/tmp/gentoken.py easykai@100.124.0.103:/tmp/gentoken.py",
        shell=True, capture_output=True, timeout=10
    )
    # Execute on server
    token = subprocess.run(
        "sshpass -p '***REMOVED***' ssh -o StrictHostKeyChecking=no easykai@100.124.0.103 python3 /tmp/gentoken.py",
        shell=True, capture_output=True, text=True, timeout=10
    ).stdout.strip()

    if not token:
        raise RuntimeError("Token 生成失败")
    print(f"   ✅ Token 已生成 (有效期24h)")
    return token


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
            timeout=120
        )
    return resp.json()


# ── FFmpeg 工具 ────────────────────────────────────────

def run_ffmpeg(args: list, description: str = "FFmpeg"):
    """运行 FFmpeg，显示进度"""
    print(f"🎬 {description} ...")
    result = subprocess.run(['ffmpeg', '-y'] + args, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"❌ FFmpeg 失败:\n{result.stderr[-500:]}")
        sys.exit(1)
    print(f"   ✅ 完成")


def generate_thumbnail(video_path: str, thumb_path: str, time_sec: float = 1.0):
    """提取视频缩略图"""
    run_ffmpeg([
        '-i', video_path,
        '-ss', str(time_sec),
        '-vframes', '1',
        '-q:v', '2',
        thumb_path
    ], f"生成缩略图 → {os.path.basename(thumb_path)}")


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
        print(f"   ID: {d['id']}")
        print(f"   文件名: {d['original_name']}")
        print(f"   类型: {d['mime_type']}")
        print(f"   大小: {d['file_size'] / 1024:.0f} KB")
        print(f"   📋 后台查看: {SERVER}/admin#l_media_library")
    else:
        print(f"❌ 上传失败: {result.get('error', '未知错误')}")
        sys.exit(1)


def cmd_compress(args):
    """压缩视频后上传"""
    filepath = args.file
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        sys.exit(1)

    size_mb = os.path.getsize(filepath) / 1024 / 1024
    print(f"📥 输入: {os.path.basename(filepath)} ({size_mb:.1f} MB)")

    out = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    out.close()
    ffmpeg_args = ['-i', filepath, '-c:v', 'libx264', '-preset', 'medium']
    if args.width:
        ffmpeg_args += ['-vf', f'scale={args.width}:-2']
    if args.bitrate:
        ffmpeg_args += ['-b:v', args.bitrate]
    ffmpeg_args += ['-c:a', 'aac', '-b:a', '128k', '-movflags', '+faststart', out.name]
    run_ffmpeg(ffmpeg_args, f"压缩视频")

    out_size = os.path.getsize(out.name) / 1024 / 1024
    print(f"   压缩后: {out_size:.1f} MB ({(1 - out_size/size_mb)*100:.0f}% 减小)")

    result = _upload(out.name, args.title or os.path.basename(filepath))
    os.unlink(out.name)

    if result.get('success'):
        print(f"✅ 已推送到发布管理!")
        print(f"   📋 {SERVER}/admin  → 全媒体创作 → 多媒体 → 发布管理")
    else:
        print(f"❌ 上传失败: {result.get('error')}")


def cmd_slideshow(args):
    """图片幻灯片 + 音频 → 视频 → 上传"""
    try:
        from moviepy import ImageClip, AudioFileClip, concatenate_videoclips
    except ImportError:
        print("❌ 需要 MoviePy: pip3 install --break-system-packages moviepy")
        sys.exit(1)

    duration = args.duration or 3
    images = args.images

    for img in images:
        if not os.path.exists(img):
            print(f"❌ 图片不存在: {img}")
            sys.exit(1)

    print(f"🎞️  生成幻灯片 ({len(images)} 张图片, 每张 {duration}s)")

    clips = []
    for img in images:
        try:
            clip = ImageClip(img).with_duration(duration)
            # 居中缩放
            clip = clip.resized(height=1080)
            clips.append(clip)
        except Exception as e:
            print(f"⚠️  跳过 {img}: {e}")

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
            print(f"⚠️  音频处理失败: {e}")

    out = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    out.close()
    video.write_videofile(out.name, fps=24, codec='libx264', audio_codec='aac', logger=None)
    print(f"   ✅ 视频生成: {out.name}")

    title = args.title or f"slideshow_{len(images)}imgs.mp4"
    result = _upload(out.name, title)
    os.unlink(out.name)

    if result.get('success'):
        print(f"✅ 已推送到发布管理!")


def cmd_watermark(args):
    """添加文字水印后上传"""
    filepath = args.file
    if not os.path.exists(filepath):
        print(f"❌ 文件不存在: {filepath}")
        sys.exit(1)

    text = args.text
    print(f"💧 添加水印: \"{text}\" → {os.path.basename(filepath)}")

    out = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
    out.close()

    # 用 FFmpeg drawtext 加水印
    font_size = args.fontsize or 24
    position = args.position or 'bottom-right'
    pos_map = {
        'top-left': 'x=10:y=10',
        'top-right': 'x=w-tw-10:y=10',
        'bottom-left': 'x=10:y=h-th-10',
        'bottom-right': 'x=w-tw-10:y=h-th-10',
        'center': 'x=(w-tw)/2:y=(h-th)/2',
    }
    pos = pos_map.get(position, 'x=w-tw-10:y=h-th-10')

    fontfile = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    if not os.path.exists(fontfile):
        # fallback: try to find any ttf
        import glob as _g
        fonts = _g.glob('/usr/share/fonts/**/*.ttf', recursive=True)
        fontfile = fonts[0] if fonts else ''

    vf = f"drawtext=text='{text}':fontfile={fontfile}:fontsize={font_size}:fontcolor=white@0.7:{pos}:box=1:boxcolor=black@0.3:boxborderw=5"
    run_ffmpeg(['-i', filepath, '-vf', vf, '-c:a', 'copy', out.name], f"添加水印")
    
    result = _upload(out.name, args.title or os.path.basename(filepath))
    os.unlink(out.name)

    if result.get('success'):
        print(f"✅ 已推送到发布管理!")


# ── 主入口 ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="EasyKai 本地媒体生产器 (FFmpeg/MoviePy → 上传服务器)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 media_producer.py upload video.mp4
  python3 media_producer.py compress video.mp4 --width 1080 --bitrate 2M
  python3 media_producer.py slideshow img1.jpg img2.jpg --audio bgm.mp3
  python3 media_producer.py watermark video.mp4 --text "EasyKai"
        """
    )
    sub = parser.add_subparsers(dest='cmd', help='命令')

    # upload
    p_up = sub.add_parser('upload', help='直接上传文件')
    p_up.add_argument('file', help='文件路径')
    p_up.set_defaults(func=cmd_upload)

    # compress
    p_cp = sub.add_parser('compress', help='压缩视频并上传')
    p_cp.add_argument('file', help='视频文件路径')
    p_cp.add_argument('--width', type=int, help='目标宽度 (如 1080)')
    p_cp.add_argument('--bitrate', help='目标码率 (如 2M)')
    p_cp.add_argument('--title', help='上传标题')
    p_cp.set_defaults(func=cmd_compress)

    # slideshow
    p_ss = sub.add_parser('slideshow', help='图片幻灯片生成视频')
    p_ss.add_argument('images', nargs='+', help='图片文件列表')
    p_ss.add_argument('--audio', help='背景音频文件')
    p_ss.add_argument('--duration', type=float, default=3, help='每张图片时长(秒), 默认3')
    p_ss.add_argument('--title', help='上传标题')
    p_ss.set_defaults(func=cmd_slideshow)

    # watermark
    p_wm = sub.add_parser('watermark', help='添加文字水印并上传')
    p_wm.add_argument('file', help='视频文件路径')
    p_wm.add_argument('--text', required=True, help='水印文字')
    p_wm.add_argument('--fontsize', type=int, default=24, help='字体大小')
    p_wm.add_argument('--position', default='bottom-right',
                       choices=['top-left','top-right','bottom-left','bottom-right','center'])
    p_wm.add_argument('--title', help='上传标题')
    p_wm.set_defaults(func=cmd_watermark)

    args = parser.parse_args()
    if not args.cmd:
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == '__main__':
    main()
