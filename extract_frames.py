"""提取视频关键帧用于检查显示效果"""
import os
from moviepy.editor import VideoFileClip

video_path = 'output/videos/夜に駆ける_YOASOBI_tiktok.mp4'
out_dir = 'output/frames_check'
os.makedirs(out_dir, exist_ok=True)

clip = VideoFileClip(video_path)
# 提取多个时间点的帧：开头(标题显示)、中段(歌词滚动)、长歌词可能换行处
times = [2.0, 10.0, 30.0, 60.0, 90.0, 120.0, 150.0, 180.0, 210.0, 240.0]
for t in times:
    if t < clip.duration:
        frame = clip.get_frame(t)
        from PIL import Image
        img = Image.fromarray(frame)
        img.save(os.path.join(out_dir, f'frame_{int(t):03d}.png'))
        print(f'Saved frame at t={t}s')

clip.close()
print('Done')
