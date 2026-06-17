#!/usr/bin/env python3
"""
自定义下载脚本 - 绕过夸克网盘反爬虫机制
"""
import json
import time
import requests
from pathlib import Path
from quark_client import QuarkClient

COOKIE_FILE = Path(__file__).parent / 'cookie.txt'
SAVE_DIR = Path(__file__).parent / 'assets' / 'audio' / 'jp_songs'
TARGET_FOLDER_NAME = '日语歌曲下载'


def load_cookie():
    """从cookie.txt读取Cookie"""
    lines = COOKIE_FILE.read_text(encoding='utf-8').splitlines()
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            return line
    return None


def collect_all_files(client, folder_id):
    """递归收集所有文件"""
    all_files = []
    page = 1
    while True:
        resp = client.list_files(folder_id=folder_id, page=page, size=100)
        items = resp.get('data', {}).get('list', [])
        if not items:
            break
        for item in items:
            if item.get('file'):
                all_files.append(item)
            else:
                sub_files = collect_all_files(client, item['fid'])
                all_files.extend(sub_files)
        total = resp.get('data', {}).get('_total', 0)
        if len(items) * page >= total:
            break
        page += 1
    return all_files


def download_with_requests(download_url, save_path, cookie_str):
    """使用requests下载，设置完整的浏览器headers"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Referer': 'https://pan.quark.cn/',
        'Origin': 'https://pan.quark.cn',
        'Connection': 'keep-alive',
        'Cookie': cookie_str,
        'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Upgrade-Insecure-Requests': '1',
    }
    
    response = requests.get(download_url, headers=headers, stream=True, timeout=120)
    response.raise_for_status()
    
    with open(save_path, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    
    return save_path


def main():
    print("=" * 60)
    print("日语歌曲下载（自定义下载方法）")
    print("=" * 60)
    
    cookie_str = load_cookie()
    if not cookie_str:
        print("❌ 无法读取Cookie")
        return
    
    SAVE_DIR.mkdir(parents=True, exist_ok=True)
    
    client = QuarkClient(cookies=cookie_str, auto_login=False)
    
    # 查找目标文件夹
    print("\n查找目标文件夹...")
    root = client.list_files(folder_id='0', page=1, size=100)
    target_fid = None
    for item in root.get('data', {}).get('list', []):
        if item.get('file_name') == TARGET_FOLDER_NAME:
            target_fid = item['fid']
            break
    
    if not target_fid:
        print(f"❌ 找不到文件夹: {TARGET_FOLDER_NAME}")
        print("请先运行转存脚本")
        return
    
    print(f"✓ 找到文件夹: {TARGET_FOLDER_NAME} (ID: {target_fid})")
    
    # 收集所有文件
    print("\n扫描文件...")
    all_files = collect_all_files(client, target_fid)
    mp3_files = [f for f in all_files if f.get('file_name', '').lower().endswith('.mp3')]
    print(f"找到 {len(mp3_files)} 个MP3文件")
    
    # 下载
    success = 0
    fail = 0
    skip = 0
    
    for i, file_info in enumerate(mp3_files, 1):
        fid = file_info['fid']
        fname = file_info['file_name']
        output_path = SAVE_DIR / fname
        
        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"  [{i}/{len(mp3_files)}] ⊘ 已存在: {fname}")
            skip += 1
            continue
        
        print(f"  [{i}/{len(mp3_files)}] ↓ {fname} ...", end='', flush=True)
        
        try:
            # 获取下载链接
            download_info = client.download.get_download_url(fid)
            
            # 使用自定义方法下载
            download_with_requests(download_info, str(output_path), cookie_str)
            
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f" ✓ ({size_mb:.1f} MB)")
            success += 1
            
        except Exception as e:
            print(f" ✗ {e}")
            fail += 1
        
        time.sleep(1)
    
    client.close()
    
    print(f"\n{'=' * 60}")
    print(f"下载完成: 成功 {success}, 跳过 {skip}, 失败 {fail}")
    print(f"文件保存在: {SAVE_DIR.absolute()}")
    print("=" * 60)


if __name__ == '__main__':
    main()
