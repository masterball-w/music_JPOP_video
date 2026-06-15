# JP Music Video Generator - 日语流行歌曲歌词学习短视频生成工具

将热门日语流行歌曲的歌词转化为带有动态美感的日语学习短视频。

## 功能特性

- **歌曲发现**: 从 Spotify 日语排行榜获取热门歌曲（内置 100 首精选歌曲兜底）
- **歌词爬取**: 支持 Uta-Net、歌詞ナビ、UtaMap 等日语歌词网站
- **时间轴序列化**: 自动将歌词按句拆分并估算时间起止点（支持 LRC 文件导入）
- **日语知识解析**: 使用 Janome 分词器分析歌词中的 N5~N1 词汇和语法知识点
- **视频生成**: 使用 MoviePy 生成带有动态歌词滚动 + Romaji 注音 + 知识笔记的多平台短视频

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 完整流水线

```bash
python main.py                      # 默认运行完整流水线
python main.py --max 5              # 只处理前 5 首歌
python main.py --format youtube     # 输出 YouTube 16:9 格式
python main.py --preview            # 只生成预览截图（不渲染视频）
```

### 3. 单首歌处理

```bash
# 提供歌词文本
python main.py --song "夜に駆ける" --artist "YOASOBI" --lyrics-text "沈むように 溶けてゆくように..."

# 提供 LRC 文件（带时间戳）
python main.py --song "Lemon" --artist "米津玄師" --lrc "path/to/lemon.lrc"

# 自动爬取歌词
python main.py --song "Pretender" --artist "Official髭男dism"
```

### 4. 分步执行

```bash
python main.py --songs-only     # 只获取歌曲列表
python main.py --lyrics-only    # 只爬取歌词
python main.py --analyze-only   # 只分析知识点
python main.py --video-only     # 只生成视频（使用缓存数据）
```

## 项目结构

```
JPmusic/
├── main.py                  # 主控流水线 CLI
├── demo_test.py             # 演示测试脚本
├── config.yaml              # 配置文件
├── requirements.txt         # Python 依赖
├── modules/
│   ├── spotify_fetcher.py   # Spotify 热门歌曲获取
│   ├── lyrics_scraper.py    # 歌词爬取（Uta-Net / KashiNavi / UtaMap）
│   ├── lyrics_serializer.py # 歌词序列化 + Romaji 转换
│   ├── jp_analyzer.py       # 日语知识点分析（词汇 + 语法）
│   └── video_generator.py   # 视频合成引擎（MoviePy + Pillow）
├── data/
│   ├── songs/               # 歌曲列表 JSON
│   ├── lyrics/              # 原始歌词 JSON
│   ├── serialized/          # 序列化歌词 JSON（含时间轴）
│   └── analysis/            # 知识点分析 JSON
├── output/
│   └── videos/              # 生成的视频和预览图
└── assets/
    ├── fonts/               # 自定义字体
    └── backgrounds/         # 背景素材
```

## 视频输出格式

| 平台 | 分辨率 | 比例 | 帧率 |
|------|--------|------|------|
| TikTok/抖音 | 1080×1920 | 9:16 | 30fps |
| YouTube/B站 | 1920×1080 | 16:9 | 30fps |
| Instagram/小红书 | 1080×1080 | 1:1 | 30fps |

## 视频画面布局

- **顶部**: 歌曲标题 + 艺术家名称
- **中部**: 动态歌词流动 + 当前行高亮 + Romaji 注音
- **底部**: 日语知识笔记面板（词汇释义 / 语法解析，标注 JLPT 等级）

## 配置 Spotify API（可选）

编辑 `config.yaml`，填入你的 Spotify API 凭据：

```yaml
spotify:
  client_id: "your_client_id"
  client_secret: "your_client_secret"
```

获取方式: https://developer.spotify.com/dashboard

未配置时将使用内置的 100 首精选日语歌曲列表。

## 使用 LRC 歌词文件

如果你有带时间戳的 LRC 歌词文件，可以直接导入以获得精确的歌词同步：

```bash
python main.py --song "夜に駆ける" --artist "YOASOBI" --lrc "lyrics/yoru.lrc"
```

LRC 格式示例：
```
[00:15.20]沈むように 溶けてゆくように
[00:22.50]二人だけの空が広がる夜に
```

## 注意事项

- 歌词爬取功能依赖目标网站的页面结构，网站更新可能需要调整爬虫
- 时间轴估算基于字符数量，如需精确同步请提供 LRC 文件或手动调整
- 视频生成耗时较长，30 秒视频约需 2-5 分钟（取决于 CPU 性能）
- 建议先使用 `--preview` 生成预览图确认效果后再渲染完整视频
