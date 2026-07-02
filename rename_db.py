"""重命名数据库文件 site.db -> verorun.db"""
import os, shutil

files = [
    os.path.join('F:\\Sites', 'site.db'),
    os.path.join('F:\\Sites\\VeroRun', 'site.db'),
    os.path.join('F:\\Sites\\VeroRun', 'data', 'site.db'),
]

for f in files:
    if os.path.isfile(f):
        new = f.replace('site.db', 'verorun.db')
        os.rename(f, new)
        print(f'已改名: {f} -> {new}')
    else:
        print(f'不存在: {f}')
