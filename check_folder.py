#!/usr/bin/env python3
"""检查夸克网盘文件夹结构"""
import json
from pathlib import Path
from quark_client import QuarkClient

COOKIE_FILE = Path(__file__).parent / 'cookie.txt'

lines = COOKIE_FILE.read_text(encoding='utf-8').splitlines()
cookie_str = ''
for line in lines:
    line = line.strip()
    if line and not line.startswith('#'):
        cookie_str = line
        break

client = QuarkClient(cookies=cookie_str, auto_login=False)

# 列出根目录
print("=== 根目录 ===")
root = client.list_files(folder_id='0', page=1, size=100)
for item in root.get('data', {}).get('list', []):
    ftype = 'folder' if item.get('file') == False or item.get('dir') else 'file'
    # Check actual structure
    is_dir = item.get('file', True) == False
    print(f"  {item.get('file_name')} | fid={item.get('fid')} | file={item.get('file')} | dir={item.get('dir')} | type={item.get('obj_category', '?')}")

# 查找"日语歌曲下载"文件夹
target_fid = None
for item in root.get('data', {}).get('list', []):
    if item.get('file_name') == '日语歌曲下载':
        target_fid = item.get('fid')
        break

if target_fid:
    print(f"\n=== 日语歌曲下载 文件夹内容 (fid={target_fid}) ===")
    folder = client.list_files(folder_id=target_fid, page=1, size=100)
    items = folder.get('data', {}).get('list', [])
    print(f"共 {len(items)} 项")
    for item in items[:20]:
        is_file = item.get('file', False)
        print(f"  {item.get('file_name')} | fid={item.get('fid')} | file={is_file}")
        if is_file:
            print(f"    -> size={item.get('size', 0)}, format={item.get('format_type', '?')}, category={item.get('obj_category', '?')}")
    
    # 如果有子文件夹，递归查看
    for item in items:
        if not item.get('file'):
            sub_fid = item.get('fid')
            print(f"\n  === 子文件夹: {item.get('file_name')} (fid={sub_fid}) ===")
            sub = client.list_files(folder_id=sub_fid, page=1, size=20)
            sub_items = sub.get('data', {}).get('list', [])
            print(f"  共 {len(sub_items)} 项")
            for si in sub_items[:10]:
                print(f"    {si.get('file_name')} | fid={si.get('fid')} | file={si.get('file')}")

client.close()
