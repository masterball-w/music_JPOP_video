#!/usr/bin/env python3
"""
生成一个实际的视频帧并保存为图片，检查渲染效果
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from modules.video_generator_v3 import VideoGenerator, TextRenderer

# 加载配置
from batch_process import load_config
config = load_config()

# 创建 VideoGenerator
generator = VideoGenerator(config)

# 加载分析数据
analysis_file = Path("data/analysis/YOASOBI_夜に駆ける.json")
with open(analysis_file, 'r', encoding='utf-8') as f:
    analysis = json.load(f)

# 渲染一个实际帧
W, H = 1080, 1920
from modules.video_generator_v3 import EnhancedBackground, ParticleEngine

bg_engine = generator._make_bg_engine(W, H)
particles = ParticleEngine(W, H)

# 测试多个时间点
for t in [5.0, 15.0, 30.0, 60.0]:
    frame = generator._render_frame(t, W, H, analysis, bg_engine, particles)
    
    # frame 是 numpy array，转为 PIL Image
    if isinstance(frame, np.ndarray):
        frame_img = Image.fromarray(frame)
    else:
        frame_img = frame
    
    frame_img.save(f"data/test_frame_t{int(t)}.png")
    print(f"已保存帧 t={t}s: data/test_frame_t{int(t)}.png")

# 也测试 note card 的渲染
print("\n=== 测试 Note Card ===")
top_notes = analysis.get('top_notes', [])
for i, note in enumerate(top_notes[:5]):
    card = generator.R.render_note_card(note, width=900)
    card.save(f"data/test_card_v3_{i}.png")
    print(f"Note {i}: {note.get('type')} - {note.get('data', {}).get('word', '')}")

print("\n完成！请查看 data/ 目录下的图片")
