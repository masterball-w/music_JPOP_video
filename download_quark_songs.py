#!/usr/bin/env python3
"""
批量下载夸克网盘中的日语歌曲
流程：从cookie.txt读取Cookie → 批量转存 → 批量下载
"""
import json
import os
import re
import time
from pathlib import Path

from quark_client import QuarkClient

COOKIE_FILE = Path(__file__).parent / 'cookie.txt'
SONGS_FILE = Path(__file__).parent / 'data' / 'songs' / 'higequ_riyu_songs.json'
SAVE_DIR = Path(__file__).parent / 'assets' / 'audio' / 'jp_songs'
TARGET_FOLDER_NAME = '日语歌曲下载'


def load_cookie():
    """从cookie.txt读取Cookie字符串"""
    if not COOKIE_FILE.exists():
        print(f"❌ 找不到 {COOKIE_FILE}")
        print("请先按说明获取夸克网盘Cookie并保存到 cookie.txt")
        return None

    lines = COOKIE_FILE.read_text(encoding='utf-8').splitlines()
    # 过滤注释行和空行，取第一行有效内容
    cookie_str = ''
    for line in lines:
        line = line.strip()
        if line and not line.startswith('#'):
            cookie_str = line
            break

    if not cookie_str:
        print("❌ cookie.txt 为空或只有注释，请填入Cookie字符串")
        return None

    # 简单验证
    if '__kps' not in cookie_str or '__uid' not in cookie_str:
        print("⚠️  Cookie中缺少 __kps 或 __uid 字段，可能不正确")
        print(f"   Cookie前100字符: {cookie_str[:100]}...")
        confirm = input("   是否继续？(y/n): ").strip().lower()
        if confirm != 'y':
            return None

    print(f"✓ Cookie已读取（长度: {len(cookie_str)}）")
    return cookie_str


def load_songs():
    """加载歌曲数据，返回有夸克网盘链接的歌曲列表"""
    if not SONGS_FILE.exists():
        print(f"❌ 找不到歌曲数据文件: {SONGS_FILE}")
        return []

    with open(SONGS_FILE, 'r', encoding='utf-8') as f:
        songs = json.load(f)

    songs_with_links = [s for s in songs if s.get('music_url') and 'quark' in s['music_url']]
    print(f"✓ 加载了 {len(songs)} 首歌曲，其中 {len(songs_with_links)} 首有夸克网盘链接")
    return songs_with_links


def find_or_create_folder(client, folder_name):
    """在根目录查找或创建指定文件夹，返回文件夹ID"""
    root_files = client.list_files(folder_id='0', page=1, size=100)
    for item in root_files.get('data', {}).get('list', []):
        if item.get('file_name') == folder_name and not item.get('file'):
            fid = item['fid']
            print(f"✓ 文件夹已存在: {folder_name} (ID: {fid})")
            return fid

    # 文件夹不存在，创建它
    try:
        result = client.create_folder(folder_name, parent_id='0')
        fid = result['data']['fid']
        print(f"✓ 文件夹已创建: {folder_name} (ID: {fid})")
        return fid
    except Exception as e:
        if '同名冲突' in str(e) or '23008' in str(e):
            # 同名文件夹已存在，重新查找
            root_files = client.list_files(folder_id='0', page=1, size=100)
            for item in root_files.get('data', {}).get('list', []):
                if item.get('file_name') == folder_name:
                    fid = item['fid']
                    print(f"✓ 文件夹已存在: {folder_name} (ID: {fid})")
                    return fid
        raise


def batch_save(client, songs, target_folder_id):
    """批量转存分享链接到目标文件夹"""
    urls = [s['music_url'] for s in songs]
    print(f"\n=== 批量转存 {len(urls)} 个分享链接 ===")

    success_count = 0
    fail_count = 0

    def progress(current, total, url, result):
        nonlocal success_count, fail_count
        title = next((s['title'] for s in songs if s['music_url'] == url), url)
        if result.get('success'):
            success_count += 1
            print(f"  [{current}/{total}] ✓ {title}")
        else:
            fail_count += 1
            err = result.get('error', '未知错误')
            print(f"  [{current}/{total}] ✗ {title}: {err}")

    results = client.shares.batch_save_shares(
        share_urls=urls,
        target_folder_id=target_folder_id,
        save_all=True,
        wait_for_completion=False,
        progress_callback=progress
    )

    print(f"\n转存完成: 成功 {success_count}, 失败 {fail_count}")
    # 等待转存任务处理
    print("等待转存任务处理...")
    time.sleep(10)
    return results


def collect_all_files(client, folder_id):
    """递归收集文件夹中所有文件（包括子文件夹）"""
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
                # 递归进入子文件夹
                sub_files = collect_all_files(client, item['fid'])
                all_files.extend(sub_files)
        total = resp.get('data', {}).get('_total', 0)
        if len(items) * page >= total:
            break
        page += 1
    return all_files


def download_all_files(client, target_folder_id, save_dir):
    """下载目标文件夹中的所有mp3文件"""
    save_dir = Path(save_dir)
    save_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n=== 扫描文件夹并下载文件到 {save_dir} ===")

    # 递归收集所有文件
    all_files = collect_all_files(client, target_folder_id)
    print(f"找到 {len(all_files)} 个文件")

    # 优先下载mp3，如果同一首歌已有flac则跳过mp3
    # 按歌曲名分组，优先选mp3
    mp3_files = [f for f in all_files if f.get('file_name', '').lower().endswith('.mp3')]
    flac_files = [f for f in all_files if f.get('file_name', '').lower().endswith('.flac')]

    # 只下载mp3
    files_to_download = mp3_files
    print(f"其中 MP3: {len(mp3_files)}, FLAC: {len(flac_files)}")
    print(f"将下载 {len(files_to_download)} 个 MP3 文件")

    success = 0
    fail = 0
    skip = 0

    for i, file_info in enumerate(files_to_download, 1):
        fid = file_info['fid']
        fname = file_info['file_name']
        output_path = save_dir / fname

        # 跳过已存在的文件
        if output_path.exists() and output_path.stat().st_size > 0:
            print(f"  [{i}/{len(files_to_download)}] ⊘ 已存在，跳过: {fname}")
            skip += 1
            continue

        print(f"  [{i}/{len(files_to_download)}] ↓ {fname} ...", end='', flush=True)
        try:
            client.download.download_file(fid, str(output_path))
            size_mb = output_path.stat().st_size / (1024 * 1024)
            print(f" ✓ ({size_mb:.1f} MB)")
            success += 1
        except Exception as e:
            print(f" ✗ {e}")
            fail += 1

        # 避免请求过快
        time.sleep(0.5)

    print(f"\n下载完成: 成功 {success}, 跳过 {skip}, 失败 {fail}")


def main():
    print("=" * 60)
    print("日语歌曲批量下载工具（夸克网盘）")
    print("=" * 60)

    # 1. 读取Cookie
    cookie_str = load_cookie()
    if not cookie_str:
        return

    # 2. 加载歌曲数据
    songs = load_songs()
    if not songs:
        return

    # 3. 创建客户端
    print("\n=== 连接夸克网盘 ===")
    client = QuarkClient(cookies=cookie_str, auto_login=False)

    # 验证登录状态
    try:
        files = client.list_files(folder_id='0', page=1, size=1)
        if files.get('status') == 200 or files.get('data'):
            print("✓ 登录成功")
        else:
            print(f"⚠️  登录状态异常: {files}")
            print("Cookie可能已过期，请重新获取")
            return
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("Cookie可能已过期，请重新获取")
        return

    # 4. 创建目标文件夹
    target_folder_id = find_or_create_folder(client, TARGET_FOLDER_NAME)

    # 5. 批量转存
    batch_save(client, songs, target_folder_id)

    # 6. 批量下载
    download_all_files(client, target_folder_id, SAVE_DIR)

    client.close()
    print("\n" + "=" * 60)
    print("全部完成！")
    print(f"歌曲保存在: {SAVE_DIR.absolute()}")
    print("=" * 60)


if __name__ == '__main__':
    main()
