"""
Video Generator Module v3 - Enhanced Visual Effects
=====================================================
Major improvements over v2:
- Fly-in/fly-out animations for lyrics (slide + fade + scale)
- Fly-in/fly-out animations for note cards (directional entry/exit)
- Enhanced background image support with Ken Burns effect
- Improved particle system with more variety
- Smooth cross-fade transitions between lyrics
- Enhanced glow and shadow effects
- Lyric-note alignment using per-line data with token extraction fallback

Uses MoviePy 2.x for video compositing and Pillow for text rendering.
"""

import json
import math
import os
import random
import re
from pathlib import Path
from typing import Optional, List, Tuple

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from rich.console import Console

console = Console()

# 配置 MoviePy 使用系统 ffmpeg（支持 NVENC 硬件编码）
# 系统 ffmpeg 版本更新，支持最新的 NVENC API
import shutil
_system_ffmpeg = shutil.which("ffmpeg")
if _system_ffmpeg:
    try:
        from moviepy.config import change_settings
        change_settings({"FFMPEG_BINARY": _system_ffmpeg})
    except Exception:
        pass

try:
    from moviepy import (
        VideoClip, AudioFileClip, ImageClip, CompositeVideoClip,
        concatenate_videoclips, ColorClip, TextClip, CompositeAudioClip,
    )
    HAS_MOVIEPY = True
except ImportError:
    try:
        from moviepy.editor import (
            VideoClip, AudioFileClip, ImageClip, CompositeVideoClip,
            concatenate_videoclips, ColorClip, TextClip, CompositeAudioClip,
        )
        HAS_MOVIEPY = True
    except ImportError:
        HAS_MOVIEPY = False


# ============================================================
#  Enhanced Easing Functions
# ============================================================

def lerp(a, b, t):
    return a + (b - a) * max(0.0, min(1.0, t))

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1[:3], c2[:3]))

def ease_out_cubic(t):
    return 1 - (1 - t) ** 3

def ease_in_cubic(t):
    return t ** 3

def ease_in_out(t):
    return t * t * (3 - 2 * t)

def ease_in_out_cubic(t):
    return 4 * t * t * t if t < 0.5 else 1 - math.pow(-2 * t + 2, 3) / 2

def ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2

def ease_out_elastic(t):
    if t == 0 or t == 1:
        return t
    return math.pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1

def ease_out_quart(t):
    return 1 - (1 - t) ** 4

def ease_out_expo(t):
    return 1 if t == 1 else 1 - math.pow(2, -10 * t)

def ease_out_quint(t):
    return 1 - (1 - t) ** 5

def ease_in_out_back(t):
    c1 = 1.70158
    c2 = c1 * 1.525
    if t < 0.5:
        return (math.pow(2 * t, 2) * ((c2 + 1) * 2 * t - c2)) / 2
    else:
        return (math.pow(2 * t - 2, 2) * ((c2 + 1) * (t * 2 - 2) + c2) + 2) / 2

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ============================================================
#  Font Management
# ============================================================

def find_japanese_font() -> str:
    # 优先使用支持中日文的字体（微软雅黑），其次才是日文字体
    candidates = [
        "C:/Windows/Fonts/msyh.ttc",         # 微软雅黑（支持中日文）
        "C:/Windows/Fonts/msyhbd.ttc",       # 微软雅黑粗体
        "C:/Windows/Fonts/simhei.ttf",       # 黑体（支持中日文）
        "C:/Windows/Fonts/YuGothB.ttc",      # 游ゴシック Bold
        "C:/Windows/Fonts/YuGothM.ttc",      # 游ゴシック Medium
        "C:/Windows/Fonts/meiryo.ttc",       # Meiryo
        "C:/Windows/Fonts/YuGothR.ttc",      # 游ゴシック Regular
        "C:/Windows/Fonts/msgothic.ttc",     # MS Gothic
        "C:/Windows/Fonts/msmincho.ttc",     # MS Mincho
        "C:/Windows/Fonts/segoeui.ttf",      # Segoe UI
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    import glob
    for pattern in ("C:/Windows/Fonts/*gothic*", "C:/Windows/Fonts/*Yu*", "C:/Windows/Fonts/msyh*"):
        found = glob.glob(pattern)
        if found:
            return found[0]
    return None


def find_japanese_font_bold() -> str:
    candidates = [
        "C:/Windows/Fonts/msyhbd.ttc",       # 微软雅黑粗体
        "C:/Windows/Fonts/YuGothB.ttc",      # 游ゴシック Bold
        "C:/Windows/Fonts/meiryob.ttc",      # Meiryo Bold
        "C:/Windows/Fonts/YuGothM.ttc",      # 游ゴシック Medium
        "C:/Windows/Fonts/msgothic.ttc",     # MS Gothic
        "C:/Windows/Fonts/segoeui.ttf",      # Segoe UI
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return find_japanese_font()


# ============================================================
#  Text Renderer (Enhanced)
# ============================================================

class TextRenderer:
    def __init__(self, font_path=None):
        self.font_path = font_path or find_japanese_font()
        self.bold_font_path = find_japanese_font_bold()
        self._cache = {}
        self._bold_cache = {}
        
        # 验证字体文件
        if self.font_path:
            console.print(f"[dim]使用字体: {self.font_path}[/dim]")
        else:
            console.print("[yellow]警告: 未找到日文字体，将使用默认字体[/yellow]")

    def font(self, size):
        if size not in self._cache:
            try:
                if self.font_path:
                    # 对于 .ttc 文件，明确指定 index=0
                    if self.font_path.endswith('.ttc'):
                        self._cache[size] = ImageFont.truetype(self.font_path, size, index=0)
                    else:
                        self._cache[size] = ImageFont.truetype(self.font_path, size)
                else:
                    self._cache[size] = ImageFont.load_default()
            except Exception as e:
                console.print(f"[yellow]字体加载失败 (size={size}): {e}[/yellow]")
                self._cache[size] = ImageFont.load_default()
        return self._cache[size]

    def bold_font(self, size):
        if size not in self._bold_cache:
            try:
                if self.bold_font_path:
                    if self.bold_font_path.endswith('.ttc'):
                        self._bold_cache[size] = ImageFont.truetype(self.bold_font_path, size, index=0)
                    else:
                        self._bold_cache[size] = ImageFont.truetype(self.bold_font_path, size)
                else:
                    self._bold_cache[size] = self.font(size)
            except Exception as e:
                console.print(f"[yellow]粗体字体加载失败 (size={size}): {e}[/yellow]")
                self._bold_cache[size] = self.font(size)
        return self._bold_cache[size]

    def render(
        self, text, size,
        color=(255, 255, 255),
        max_width=None,
        glow=False, glow_color=(80, 180, 255), glow_radius=14,
        shadow=False, shadow_color=(0, 0, 0), shadow_offset=3,
    ):
        f = self.font(size)
        dummy = Image.new("RGBA", (1, 1))
        d = ImageDraw.Draw(dummy)
        bb = d.textbbox((0, 0), text, font=f)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if max_width and tw > max_width:
            while tw > max_width and len(text) > 1:
                text = text[:-1]
                bb = d.textbbox((0, 0), text + "...", font=f)
                tw = bb[2] - bb[0]
            text += "..."
            bb = d.textbbox((0, 0), text, font=f)
            tw = bb[2] - bb[0]
        pad = (glow_radius * 2 + shadow_offset) if glow else (shadow_offset + 6)
        W, H = tw + pad * 2, th + pad * 2
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

        if shadow:
            sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(sh).text((pad + shadow_offset, pad + shadow_offset), text, font=f, fill=(*shadow_color, 120))
            sh = sh.filter(ImageFilter.GaussianBlur(shadow_offset + 2))
            img = Image.alpha_composite(img, sh)

        if glow:
            gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(gl).text((pad, pad), text, font=f, fill=(*glow_color, 160))
            gl = gl.filter(ImageFilter.GaussianBlur(glow_radius))
            img = Image.alpha_composite(img, gl)
            gl2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(gl2).text((pad, pad), text, font=f, fill=(*glow_color, 100))
            gl2 = gl2.filter(ImageFilter.GaussianBlur(glow_radius // 3))
            img = Image.alpha_composite(img, gl2)

        ImageDraw.Draw(img).text((pad, pad), text, font=f, fill=(*color[:3], 255))
        return img

    def render_sweep(self, text, size, progress,
                     base_color=(200, 200, 220), active_color=(0, 230, 255),
                     glow_color=(60, 180, 255), max_width=None):
        f = self.font(size)
        dummy = Image.new("RGBA", (1, 1))
        d = ImageDraw.Draw(dummy)
        bb = d.textbbox((0, 0), text, font=f)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if max_width and tw > max_width:
            tw = max_width
        pad = 20
        W, H = tw + pad * 2, th + pad * 2

        base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(base).text((pad, pad), text, font=f, fill=(*base_color, 255))

        active = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(active).text((pad, pad), text, font=f, fill=(*active_color, 255))

        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).text((pad, pad), text, font=f, fill=(*glow_color, 140))
        glow = glow.filter(ImageFilter.GaussianBlur(10))

        sweep_x = int(pad + tw * clamp(progress, 0, 1))
        mask = Image.new("L", (W, H), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rectangle([(0, 0), (sweep_x, H)], fill=255)
        mask = mask.filter(ImageFilter.GaussianBlur(4))

        result = base.copy()
        glow_masked = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        glow_masked.paste(glow, mask=mask)
        result = Image.alpha_composite(result, glow_masked)
        active_masked = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        active_masked.paste(active, mask=mask)
        result = Image.alpha_composite(result, active_masked)

        return result

    def wrap(self, text, font_obj, max_w):
        dummy = Image.new("RGBA", (1, 1))
        d = ImageDraw.Draw(dummy)
        lines, cur = [], ""
        for ch in text:
            t = cur + ch
            if d.textbbox((0, 0), t, font=font_obj)[2] > max_w and cur:
                lines.append(cur)
                cur = ch
            else:
                cur = t
        if cur:
            lines.append(cur)
        return lines

    @staticmethod
    def rounded_rect(draw, xy, radius, fill, outline=None, width=0):
        x0, y0, x1, y1 = xy
        r = radius
        draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
        draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
        draw.ellipse([x0, y0, x0 + 2*r, y0 + 2*r], fill=fill)
        draw.ellipse([x1 - 2*r, y0, x1, y0 + 2*r], fill=fill)
        draw.ellipse([x0, y1 - 2*r, x0 + 2*r, y1], fill=fill)
        draw.ellipse([x1 - 2*r, y1 - 2*r, x1, y1], fill=fill)
        if outline and width:
            draw.arc([x0, y0, x0 + 2*r, y0 + 2*r], 180, 270, fill=outline, width=width)
            draw.arc([x1 - 2*r, y0, x1, y0 + 2*r], 270, 360, fill=outline, width=width)
            draw.arc([x0, y1 - 2*r, x0 + 2*r, y1], 90, 180, fill=outline, width=width)
            draw.arc([x1 - 2*r, y1 - 2*r, x1, y1], 0, 90, fill=outline, width=width)
            draw.line([x0 + r, y0, x1 - r, y0], fill=outline, width=width)
            draw.line([x0 + r, y1, x1 - r, y1], fill=outline, width=width)
            draw.line([x0, y0 + r, x0, y1 - r], fill=outline, width=width)
            draw.line([x1, y0 + r, x1, y1 - r], fill=outline, width=width)

    def render_note_card(self, note, width, accent=(0, 200, 255)):
        f_title = self.bold_font(72)
        f_body = self.font(48)
        f_small = self.font(38)
        f_badge = self.bold_font(34)

        ntype = note.get("type", "vocabulary")
        data = note.get("data", {})

        pad_x, pad_y = 24, 16
        elements = []

        if ntype == "vocabulary":
            word = data.get("word", "")
            level = data.get("jlpt_level", "")
            reading = data.get("reading", "")
            meaning = data.get("meaning", "")
            elements.append(("title", word, f_title, accent, level))
            if reading:
                elements.append(("label", f"\u8aad\u307f  {reading}", f_body, (220, 230, 255)))
            if meaning:
                elements.append(("label", f"\u610f\u5473  {meaning}", f_body, (220, 230, 255)))
        else:
            pat = data.get("pattern", "").replace('\u301c', '~')
            level = data.get("level", "")
            meaning = data.get("meaning", "")
            expl = data.get("explanation", "").replace('\u301c', '~')
            ex = data.get("example", "").replace('\u301c', '~')
            elements.append(("title", pat, f_title, accent, level))
            if meaning:
                elements.append(("label", meaning, f_body, (220, 230, 255)))
            if expl:
                for wl in self.wrap(expl, f_small, width - pad_x * 2 - 40):
                    elements.append(("small", wl, f_small, (185, 200, 230)))
            if ex:
                elements.append(("small", f"\u4f8b: {ex}", f_small, (160, 225, 175)))

        dummy = Image.new("RGBA", (1, 1))
        dd = ImageDraw.Draw(dummy)
        total_h = 0
        line_metrics = []
        for item in elements:
            kind, txt, fo = item[0], item[1], item[2]
            bb = dd.textbbox((0, 0), txt, font=fo)
            lh = bb[3] - bb[1]
            lw = bb[2] - bb[0]
            spacing = 18 if kind == "title" else 12
            line_metrics.append((lh, lw, spacing))
            total_h += lh + spacing
        total_h += pad_y

        card_w = width
        card_h = total_h + pad_y

        img = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img, "RGBA")

        y = pad_y
        for idx, item in enumerate(elements):
            kind, txt, fo, col = item[0], item[1], item[2], item[3]
            level_tag = item[4] if len(item) > 4 else ""
            lh, lw, spacing = line_metrics[idx]
            tx = pad_x

            if kind == "title":
                try:
                    d.text((tx, y), txt, font=fo, fill=(*col, 255),
                           stroke_width=3, stroke_fill=(col[0]//4, col[1]//4, col[2]//4, 60))
                except TypeError:
                    d.text((tx, y), txt, font=fo, fill=(*col, 255))

                if level_tag:
                    bb_title = dd.textbbox((0, 0), txt, font=fo)
                    title_w = bb_title[2] - bb_title[0]
                    badge_colors = {
                        "N5": (80, 200, 80), "N4": (60, 170, 220),
                        "N3": (220, 180, 50), "N2": (220, 120, 50), "N1": (200, 65, 65),
                    }
                    bc = badge_colors.get(level_tag, (120, 120, 160))
                    badge_x = tx + title_w + 18
                    badge_y = y + (lh - 34) // 2
                    bb_badge = dd.textbbox((0, 0), level_tag, font=f_badge)
                    bw = bb_badge[2] - bb_badge[0] + 20
                    self.rounded_rect(d, (badge_x, badge_y, badge_x + bw, badge_y + 38),
                                      19, fill=(*bc, 180))
                    d.text((badge_x + 10, badge_y + 2), level_tag, font=f_badge,
                           fill=(255, 255, 255, 230))

                ul_y = y + lh + 4
                ul_w = min(lw + 20, card_w - pad_x * 2)
                for xi in range(ul_w):
                    ratio = xi / max(1, ul_w)
                    a = int(100 * min(ratio * 5, (1 - ratio) * 2, 1))
                    d.point((tx + xi, ul_y), fill=(*col, a))
                    d.point((tx + xi, ul_y + 1), fill=(*col, a // 2))

            elif kind == "label":
                try:
                    d.text((tx + 6, y), txt, font=fo, fill=(*col, 240),
                           stroke_width=1, stroke_fill=(col[0]//5, col[1]//5, col[2]//5, 40))
                except TypeError:
                    d.text((tx + 6, y), txt, font=fo, fill=(*col, 240))

            elif kind == "small":
                d.text((tx + 6, y), txt, font=fo, fill=(*col, 210))

            y += lh + spacing

        return img


# ============================================================
#  Enhanced Particle System
# ============================================================

class ParticleEngine:
    def __init__(self, W, H, n_bokeh=30, n_sakura=15, n_sparkle=20):
        self.W, self.H = W, H
        rng = np.random.RandomState(42)
        self.bokeh = []
        for _ in range(n_bokeh):
            self.bokeh.append({
                "x0": rng.uniform(0, W),
                "y0": rng.uniform(0, H),
                "r": rng.uniform(8, 45),
                "vx": rng.uniform(-8, 8),
                "vy": rng.uniform(-18, -4),
                "phase0": rng.uniform(0, math.pi * 2),
                "speed": rng.uniform(0.15, 0.7),
                "alpha": rng.uniform(0.04, 0.18),
                "color": self._rand_color(rng),
            })
        self.sakura = []
        for _ in range(n_sakura):
            self.sakura.append({
                "x0": rng.uniform(-40, W + 40),
                "spawn_t": rng.uniform(0, 40),
                "vx": rng.uniform(-22, 22),
                "vy": rng.uniform(25, 60),
                "angle0": rng.uniform(0, 360),
                "spin": rng.uniform(-90, 90),
                "size": rng.uniform(4, 10),
                "alpha": rng.uniform(0.1, 0.4),
                "color": (255, rng.randint(150, 200), rng.randint(200, 255)),
                "period": rng.uniform(4, 12),
            })
        self.sparkle = []
        for _ in range(n_sparkle):
            self.sparkle.append({
                "x0": rng.uniform(0, W),
                "y0": rng.uniform(0, H),
                "phase0": rng.uniform(0, math.pi * 2),
                "speed": rng.uniform(1.5, 4.0),
                "size": rng.uniform(1, 3),
                "alpha": rng.uniform(0.2, 0.6),
                "color": (255, 255, rng.randint(200, 255)),
            })

    @staticmethod
    def _rand_color(rng):
        h = rng.uniform(0, 1)
        if h < 0.4:
            return (rng.randint(60, 140), rng.randint(140, 220), 255)
        elif h < 0.7:
            return (255, rng.randint(140, 200), rng.randint(180, 255))
        else:
            return (rng.randint(180, 255), rng.randint(100, 180), 255)

    def render(self, t, img):
        draw = ImageDraw.Draw(img, "RGBA")
        W, H = self.W, self.H

        for p in self.bokeh:
            period = max(8, H / max(1, abs(p["vy"])))
            t_loop = t % period
            x = p["x0"] + p["vx"] * t_loop + math.sin(p["phase0"] + t * p["speed"]) * 15
            y = p["y0"] + p["vy"] * t_loop
            y = y % (H + p["r"] * 2) - p["r"]
            x = x % (W + p["r"] * 2) - p["r"]
            r = p["r"]
            a = int(p["alpha"] * 255)
            if a < 3:
                continue
            col = p["color"]
            for i in range(3):
                ri = int(r * (1 - i * 0.33))
                ai = int(a * (1 - i * 0.4))
                draw.ellipse([int(x)-ri, int(y)-ri, int(x)+ri, int(y)+ri],
                             fill=(*col, ai))

        for p in self.sakura:
            age = (t - p["spawn_t"]) % p["period"]
            if age < 0:
                continue
            x = p["x0"] + p["vx"] * age + math.sin(p["angle0"] * 0.02 + age) * 10
            y = -20 + p["vy"] * age
            if y > H + 20:
                continue
            angle = p["angle0"] + p["spin"] * age
            s = p["size"]
            a = int(p["alpha"] * 255 * clamp(1 - age / p["period"], 0, 1))
            if a < 5:
                continue
            col = p["color"]
            ix, iy = int(x), int(y)
            draw.ellipse([ix - s, iy - s//2, ix + s, iy + s//2], fill=(*col, a))
            draw.ellipse([ix - s//2, iy - s, ix + s//2, iy + s], fill=(*col, int(a*0.7)))

        for p in self.sparkle:
            phase = p["phase0"] + t * p["speed"]
            flicker = (math.sin(phase) + 1) / 2
            a = int(p["alpha"] * 255 * flicker)
            if a < 10:
                continue
            x = p["x0"]
            y = p["y0"]
            s = p["size"]
            col = p["color"]
            draw.ellipse([int(x)-s, int(y)-s, int(x)+s, int(y)+s], fill=(*col, a))
            if flicker > 0.7:
                draw.ellipse([int(x)-s-1, int(y)-s-1, int(x)+s+1, int(y)+s+1], fill=(*col, a//3))


# ============================================================
#  Enhanced Background with Ken Burns Effect
# ============================================================

class EnhancedBackground:
    def __init__(self, W, H, base_color=(10, 10, 22), bottom_color=None,
                 aurora_colors=None, bg_image=None, overlay_darkness=0.45,
                 ken_burns=True, kb_zoom=0.08, kb_pan_x=0.03, kb_pan_y=0.02):
        self.W, self.H = W, H
        self.base = base_color
        self.bottom_color = bottom_color or (base_color[0] + 12, base_color[1] + 8, base_color[2] + 25)
        self._aurora_colors = aurora_colors
        self._bg_image = self._load_bg_image(bg_image) if bg_image else None
        self._overlay_darkness = overlay_darkness
        self._ken_burns = ken_burns and (self._bg_image is not None)
        self._kb_zoom = kb_zoom
        self._kb_pan_x = kb_pan_x
        self._kb_pan_y = kb_pan_y
        self._base_arr = self._make_base()

    def _load_bg_image(self, path):
        try:
            img = Image.open(path).convert("RGBA")
            iw, ih = img.size
            target_ratio = self.W / self.H
            current_ratio = iw / ih
            if current_ratio > target_ratio:
                new_w = int(ih * target_ratio)
                left = (iw - new_w) // 2
                img = img.crop((left, 0, left + new_w, ih))
            else:
                new_h = int(iw / target_ratio)
                top = (ih - new_h) // 2
                img = img.crop((0, top, iw, top + new_h))
            img = img.resize((self.W, self.H), Image.LANCZOS)
            return img
        except Exception as e:
            print(f"  [yellow]Failed to load bg image: {e}[/yellow]")
            return None

    def _make_base(self):
        arr = np.zeros((self.H, self.W, 4), dtype=np.uint8)
        bt = self.base
        bb = self.bottom_color
        for y in range(self.H):
            ratio = y / self.H
            r = int(bt[0] + (bb[0] - bt[0]) * ratio)
            g = int(bt[1] + (bb[1] - bt[1]) * ratio)
            b = int(bt[2] + (bb[2] - bt[2]) * ratio)
            arr[y, :] = [r, g, b, 255]
        return arr

    def _apply_ken_burns(self, img, t):
        if not self._ken_burns:
            return img
        iw, ih = img.size
        zoom = self._kb_zoom * math.sin(t * 0.05)
        pan_x = self._kb_pan_x * math.sin(t * 0.03)
        pan_y = self._kb_pan_y * math.cos(t * 0.04)
        scale = 1.0 + zoom
        new_w = int(iw * scale)
        new_h = int(ih * scale)
        offset_x = int((iw - new_w) / 2 + pan_x * iw)
        offset_y = int((ih - new_h) / 2 + pan_y * ih)
        resized = img.resize((new_w, new_h), Image.LANCZOS)
        crop_box = (
            max(0, -offset_x),
            max(0, -offset_y),
            min(iw, new_w - offset_x),
            min(ih, new_h - offset_y)
        )
        paste_box = (
            max(0, offset_x),
            max(0, offset_y),
            max(0, offset_x) + (crop_box[2] - crop_box[0]),
            max(0, offset_y) + (crop_box[3] - crop_box[1])
        )
        result = Image.new("RGBA", (iw, ih), (0, 0, 0, 255))
        cropped = resized.crop(crop_box)
        result.paste(cropped, paste_box)
        return result

    def render(self, t):
        if self._bg_image:
            img = self._bg_image.copy()
            if self._ken_burns:
                img = self._apply_ken_burns(img, t)
            dark = int(255 * self._overlay_darkness)
            overlay = Image.new("RGBA", (self.W, self.H), (0, 0, 0, dark))
            img = Image.alpha_composite(img, overlay)
            return img

        img = Image.fromarray(self._base_arr.copy(), "RGBA")
        draw = ImageDraw.Draw(img, "RGBA")

        if self._aurora_colors:
            wave_colors = self._aurora_colors
        else:
            wave_colors = [
                (30, 80, 180, 18),
                (60, 40, 160, 14),
                (20, 100, 140, 16),
            ]

        waves = [
            {"y_ratio": 0.25, "amp": 40, "freq": 1.8, "speed": 0.25, "width": 80},
            {"y_ratio": 0.45, "amp": 30, "freq": 2.5, "speed": 0.35, "width": 60},
            {"y_ratio": 0.70, "amp": 50, "freq": 1.2, "speed": 0.18, "width": 100},
        ]
        for idx, w in enumerate(waves):
            col = wave_colors[idx] if idx < len(wave_colors) else wave_colors[-1]
            if isinstance(col, list):
                col = tuple(col)
            base_y = int(self.H * w["y_ratio"])
            pts = []
            for x in range(0, self.W + 1, 6):
                xr = x / self.W
                y = base_y + int(w["amp"] * math.sin(xr * w["freq"] * math.pi + t * w["speed"])
                                 + w["amp"] * 0.4 * math.sin(xr * w["freq"] * 2.3 * math.pi + t * w["speed"] * 1.7))
                pts.append((x, y))
            poly = pts + [(self.W, pts[-1][1] + w["width"]), (0, pts[0][1] + w["width"])]
            draw.polygon(poly, fill=col)

        vig = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vig)
        for i in range(20):
            ratio = i / 20
            alpha = int(60 * (1 - ratio))
            margin = int(min(self.W, self.H) * 0.02 * i)
            vd.rectangle([(0, 0), (margin, self.H)], fill=(0, 0, 0, alpha // 3))
            vd.rectangle([(self.W - margin, 0), (self.W, self.H)], fill=(0, 0, 0, alpha // 3))
            vd.rectangle([(0, 0), (self.W, margin)], fill=(0, 0, 0, alpha // 4))
            vd.rectangle([(0, self.H - margin), (self.W, self.H)], fill=(0, 0, 0, alpha // 2))

        img = Image.alpha_composite(img, vig)
        return img


# ============================================================
#  Theme Presets (Enhanced with background images)
# ============================================================

THEMES = {
    "aurora": {
        "gradient_top": (10, 10, 22),
        "gradient_bottom": (22, 18, 47),
        "aurora_colors": [(30, 80, 180, 18), (60, 40, 160, 14), (20, 100, 140, 16)],
        "note_accent": (0, 200, 255),
        "bg_images": ["assets/backgrounds/anime_night_lake.jpg", "assets/backgrounds/anime_starry_sky.jpg"],
    },
    "sakura": {
        "gradient_top": (18, 8, 16),
        "gradient_bottom": (35, 15, 30),
        "aurora_colors": [(180, 80, 140, 16), (200, 120, 160, 12), (140, 60, 120, 14)],
        "note_accent": (255, 150, 200),
        "bg_images": ["assets/backgrounds/anime_night_lake.jpg"],
    },
    "midnight": {
        "gradient_top": (5, 5, 15),
        "gradient_bottom": (10, 10, 30),
        "aurora_colors": [(20, 40, 100, 14), (30, 30, 80, 10), (15, 50, 90, 12)],
        "note_accent": (100, 180, 255),
        "bg_images": ["assets/backgrounds/anime_starry_sky.jpg", "assets/backgrounds/anime_city_night.jpg"],
    },
    "sunset": {
        "gradient_top": (20, 8, 10),
        "gradient_bottom": (40, 15, 25),
        "aurora_colors": [(180, 80, 30, 16), (200, 60, 50, 12), (160, 100, 40, 14)],
        "note_accent": (255, 160, 60),
        "bg_images": ["assets/backgrounds/anime_sunset_country.jpg"],
    },
    "ocean": {
        "gradient_top": (5, 12, 20),
        "gradient_bottom": (10, 25, 45),
        "aurora_colors": [(20, 80, 160, 18), (30, 120, 180, 14), (15, 60, 140, 16)],
        "note_accent": (60, 220, 255),
        "bg_images": ["assets/backgrounds/anime_city_night.jpg", "assets/backgrounds/anime_shrine_dusk.jpg"],
    },
}


# ============================================================
#  Lyric Animation Engine
# ============================================================

class LyricAnimationEngine:
    """Handles fly-in/fly-out animations for lyrics."""

    ANIMATION_DURATION = 0.6
    EXIT_DURATION = 0.4

    @classmethod
    def get_lyric_transform(cls, line_idx, active_idx, t, line_start, line_end):
        """
        Calculate transform parameters for a lyric line.
        Returns: (offset_x, offset_y, scale, alpha, glow_intensity)
        """
        dist = abs(line_idx - active_idx) if active_idx >= 0 else 3
        is_active = (line_idx == active_idx)

        if is_active:
            time_in_line = t - line_start
            if time_in_line < cls.ANIMATION_DURATION:
                p = clamp(time_in_line / cls.ANIMATION_DURATION, 0, 1)
                ease = ease_out_back(p)
                offset_x = int(lerp(100, 0, ease))
                offset_y = int(lerp(30, 0, ease))
                scale = lerp(0.85, 1.12, ease)
                alpha = lerp(0.3, 1.0, ease)
                glow = lerp(0, 1.0, ease)
            else:
                offset_x, offset_y = 0, 0
                scale, alpha, glow = 1.12, 1.0, 1.0
        else:
            if dist == 1:
                time_since_active = t - line_end if line_idx < active_idx else line_start - t
                if active_idx >= 0 and time_since_active < cls.EXIT_DURATION and time_since_active > 0:
                    p = clamp(time_since_active / cls.EXIT_DURATION, 0, 1)
                    ease = ease_in_cubic(p)
                    offset_x = int(lerp(0, -60, ease)) if line_idx < active_idx else int(lerp(0, 60, ease))
                    offset_y = int(lerp(0, -20, ease))
                    scale = lerp(1.0, 0.92, ease)
                    alpha = lerp(0.85, 0.55, ease)
                    glow = 0
                else:
                    offset_x, offset_y = 0, 0
                    scale, alpha, glow = 1.0, 0.75, 0
            elif dist == 2:
                offset_x, offset_y = 0, 0
                scale, alpha, glow = 0.95, 0.6, 0
            else:
                offset_x, offset_y = 0, 0
                scale, alpha, glow = 0.92, 0.5, 0

        return offset_x, offset_y, scale, alpha, glow


# ============================================================
#  Note Card Animation Engine
# ============================================================

class NoteCardAnimationEngine:
    """Handles fly-in/fly-out animations for note cards."""

    ENTRY_DURATION = 0.8
    EXIT_DURATION = 0.5
    STAGGER_DELAY = 0.25

    @classmethod
    def get_card_transform(cls, card_idx, note_age, direction="bottom"):
        """
        Calculate transform for a note card.
        direction: "bottom", "left", "right", "scale"
        Returns: (offset_x, offset_y, scale, rotation, alpha)
        """
        card_age = max(0, note_age - card_idx * cls.STAGGER_DELAY)

        if card_age < cls.ENTRY_DURATION:
            p = clamp(card_age / cls.ENTRY_DURATION, 0, 1)
            ease = ease_out_back(p)

            if direction == "bottom":
                offset_x = 0
                offset_y = int(lerp(150, 0, ease))
            elif direction == "left":
                offset_x = int(lerp(-200, 0, ease))
                offset_y = 0
            elif direction == "right":
                offset_x = int(lerp(200, 0, ease))
                offset_y = 0
            else:
                offset_x, offset_y = 0, 0

            scale = lerp(0.5, 1.0, ease)
            rotation = lerp(-8, 0, ease)
            alpha = lerp(0, 1, ease_out_quart(p))
        else:
            offset_x, offset_y = 0, 0
            scale, rotation, alpha = 1.0, 0, 1.0

        return offset_x, offset_y, scale, rotation, alpha


# ============================================================
#  Video Generator v3
# ============================================================

class VideoGenerator:
    def __init__(self, config):
        self.config = config
        vc = config.get("video", {})
        self.style = vc.get("style", {})
        self.formats = vc.get("formats", {})
        self.default_format = vc.get("default_format", "tiktok")
        self.max_duration = vc.get("max_duration_seconds", 180)
        self.intro_s = vc.get("intro_seconds", 3)
        self.outro_s = vc.get("outro_seconds", 2)
        self.output_dir = Path(config["paths"]["output_dir"]) / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.R = TextRenderer()
        self._theme = self._resolve_theme(vc)
        self._bg_images = self._collect_bg_images()
        self._current_bg_idx = 0
        if not HAS_MOVIEPY:
            console.print("[red]MoviePy not installed[/red]")

    def _resolve_theme(self, vc):
        theme_name = vc.get("theme", "aurora")
        theme_custom = vc.get("theme_custom", {})
        base = THEMES.get(theme_name, THEMES["aurora"]).copy()

        if theme_custom:
            if "aurora_colors" in theme_custom and theme_custom["aurora_colors"]:
                base["aurora_colors"] = [tuple(c) for c in theme_custom["aurora_colors"]]
            if "gradient_top" in theme_custom:
                base["gradient_top"] = tuple(theme_custom["gradient_top"])
            if "gradient_bottom" in theme_custom:
                base["gradient_bottom"] = tuple(theme_custom["gradient_bottom"])
            if "note_accent" in theme_custom:
                base["note_accent"] = tuple(theme_custom["note_accent"])
            bg_mode = theme_custom.get("background_mode", "aurora")
            base["background_mode"] = bg_mode
            if bg_mode == "image" and theme_custom.get("background_image"):
                bg_path = theme_custom["background_image"]
                if not os.path.isabs(bg_path):
                    project_root = Path(self.config["paths"].get("output_dir", "output")).parent
                    bg_path = str(project_root / bg_path)
                base["background_image"] = bg_path
            base["overlay_darkness"] = theme_custom.get("overlay_darkness", 0.45)

        return base

    def _collect_bg_images(self):
        """Collect available background images from theme and assets."""
        images = []
        project_root = Path(self.config["paths"].get("output_dir", "output")).parent

        # From theme preset
        theme_images = self._theme.get("bg_images", [])
        for img_path in theme_images:
            full_path = project_root / img_path
            if full_path.exists():
                images.append(str(full_path))

        # From bg_dir
        bg_dir = self.config["paths"].get("bg_dir")
        if bg_dir:
            bg_path = Path(bg_dir)
            if bg_path.exists():
                for ext in ("*.jpg", "*.jpeg", "*.png"):
                    images.extend([str(p) for p in bg_path.glob(ext)])

        # From assets/backgrounds
        assets_bg = project_root / "assets" / "backgrounds"
        if assets_bg.exists():
            for ext in ("*.jpg", "*.jpeg", "*.png"):
                images.extend([str(p) for p in assets_bg.glob(ext)])

        return images if images else [None]

    def _get_next_bg_image(self):
        if not self._bg_images or self._bg_images[0] is None:
            return None
        img = self._bg_images[self._current_bg_idx % len(self._bg_images)]
        self._current_bg_idx += 1
        return img

    def _make_bg_engine(self, W, H, specific_bg=None):
        theme = self._theme
        bg_mode = theme.get("background_mode", "aurora")
        bg_image = specific_bg or theme.get("background_image", None)

        if bg_mode == "image" and bg_image and os.path.exists(bg_image):
            return EnhancedBackground(
                W, H,
                base_color=theme.get("gradient_top", (10, 10, 22)),
                bottom_color=theme.get("gradient_bottom", (22, 18, 47)),
                aurora_colors=theme.get("aurora_colors"),
                bg_image=bg_image,
                overlay_darkness=theme.get("overlay_darkness", 0.5),
                ken_burns=True,
            )
        else:
            return EnhancedBackground(
                W, H,
                base_color=theme.get("gradient_top", (10, 10, 22)),
                bottom_color=theme.get("gradient_bottom", (22, 18, 47)),
                aurora_colors=theme.get("aurora_colors"),
                ken_burns=False,
            )

    def _get_note_accent(self):
        return self._theme.get("note_accent", (0, 200, 255))

    def _extract_notes_from_tokens(self, line):
        """Extract vocabulary notes from line tokens when no pre-built notes exist."""
        notes = []
        tokens = line.get("tokens", [])
        seen = set()

        # Interesting POS tags to extract
        interesting_pos = {"名詞", "動詞", "形容詞", "副詞", "助動詞", "接続詞", "感動詞"}
        skip_words = {"", " ", "\u3000", "\u300c", "\u300d", "\u300e", "\u300f",
                      "\uff08", "\uff09", "\u3010", "\u3011", "\u3001", "\u3002",
                      "\uff0c", "\uff0e", "\uff01", "\uff1f", "\u301c"}

        for token in tokens:
            surface = token.get("surface", "")
            pos = token.get("pos", "")
            reading = token.get("reading", "")
            base = token.get("base_form", "")

            if not surface or surface in skip_words:
                continue
            if pos not in interesting_pos:
                continue
            if surface in seen:
                continue
            seen.add(surface)

            # Skip very short or common particles
            if len(surface) == 1 and pos in {"助詞", "助動詞"}:
                continue

            # Build a simple vocabulary note
            note = {
                "type": "vocabulary",
                "data": {
                    "word": surface,
                    "reading": reading if reading and reading != surface else "",
                    "meaning": f"{pos}" + (f" / {token.get('pos_detail', '')}" if token.get('pos_detail') else ""),
                    "jlpt_level": "",
                    "pos": pos
                }
            }
            notes.append(note)

            # Limit to avoid too many cards
            if len(notes) >= 3:
                break

        return notes

    def _fmt(self, name=None):
        f = self.formats.get(name or self.default_format, self.formats.get("tiktok", {}))
        return f.get("width", 1080), f.get("height", 1920), f.get("fps", 30)

    def _find_active(self, lines, t):
        for i, ln in enumerate(lines):
            s = ln.get("start", 0) or 0
            e = ln.get("end", 0) or 0
            if s <= t < e:
                return i
        return -1

    def _render_frame(self, t, W, H, data, bg_engine, particles):
        lines = data.get("analyzed_lines", [])
        title = data.get("title", "")
        artist = data.get("artist", "")
        top_notes = data.get("top_notes", [])

        frame = bg_engine.render(t)
        particles.render(t, frame)
        draw = ImageDraw.Draw(frame, "RGBA")

        # ---- Title area with enhanced animation ----
        intro_p = clamp(t / self.intro_s, 0, 1)
        title_alpha = int(255 * ease_out_cubic(intro_p))
        title_slide = int(30 * (1 - ease_out_cubic(intro_p)))
        title_scale = lerp(0.9, 1.0, ease_out_back(intro_p))

        tf = self.R.font(36)
        af = self.R.font(22)

        tbb = draw.textbbox((0, 0), title, font=tf)
        tw = tbb[2] - tbb[0]
        tx = (W - tw) // 2
        ty = int(H * 0.05) - title_slide

        # Title with glow
        if title_alpha > 10:
            title_img = self.R.render(title, 36, color=(230, 235, 250),
                                      glow=True, glow_color=(100, 180, 255), glow_radius=12)
            if title_scale != 1.0:
                new_w = int(title_img.width * title_scale)
                new_h = int(title_img.height * title_scale)
                title_img = title_img.resize((new_w, new_h), Image.LANCZOS)
            arr = np.array(title_img)
            arr[:, :, 3] = (arr[:, :, 3] * (title_alpha / 255)).astype(np.uint8)
            title_img = Image.fromarray(arr)
            frame.paste(title_img, (tx, ty), title_img)

        # Artist
        abb = draw.textbbox((0, 0), artist, font=af)
        aw = abb[2] - abb[0]
        ax = (W - aw) // 2
        ay = ty + 48
        draw.text((ax, ay), artist, font=af, fill=(160, 170, 200, title_alpha // 2))

        # Animated decorative line
        line_w_max = min(W // 2, tw + 60)
        line_progress = ease_out_cubic(clamp((t - 0.5) / 1.5, 0, 1))
        line_w = int(line_w_max * line_progress)
        if line_w > 2:
            ly = ay + 32
            lx0 = (W - line_w) // 2
            for xi in range(line_w):
                ratio = xi / max(1, line_w)
                edge_fade = min(ratio * 4, (1 - ratio) * 4, 1)
                a = int(120 * edge_fade * line_progress)
                r = int(lerp(60, 0, ratio))
                g = int(lerp(140, 200, ratio))
                b = int(lerp(220, 255, ratio))
                draw.point((lx0 + xi, ly), fill=(r, g, b, a))
                draw.point((lx0 + xi, ly + 1), fill=(r, g, b, a // 2))

        # ---- Lyrics area with fly-in/fly-out animations ----
        active_idx = self._find_active(lines, t)
        visible_count = 5
        start_idx = max(0, active_idx - 2) if active_idx >= 0 else 0
        end_idx = min(len(lines), start_idx + visible_count)

        lyric_size = self.style.get("lyric_font_size", 50)
        romaji_size = self.style.get("romaji_font_size", 28)
        active_col = tuple(self.style.get("lyric_active_color", [0, 220, 255]))
        inactive_col = tuple(self.style.get("lyric_inactive_color", [210, 215, 235]))
        min_fade = self.style.get("lyric_inactive_min_fade", 0.55)
        romaji_col = (160, 170, 200)
        translation_col = (180, 210, 180)  # 淡绿色中文翻译

        base_spacing = lyric_size + romaji_size + 28 + 24  # +24 为中文翻译留空间
        lyric_top = int(H * 0.175)
        y_cursor = lyric_top

        for i in range(start_idx, end_idx):
            ln = lines[i]
            text = ln.get("text", "")
            romaji = ln.get("romaji", "")
            translation = ln.get("translation")
            is_active = (i == active_idx)

            line_start = ln.get("start", 0) or 0
            line_end = ln.get("end", 0) or line_start + 1

            # Get animation transforms
            offset_x, offset_y, scale, alpha, glow = LyricAnimationEngine.get_lyric_transform(
                i, active_idx, t, line_start, line_end
            )

            cur_size = max(16, int(lyric_size * scale))

            if is_active:
                progress = clamp((t - line_start) / max(0.1, line_end - line_start), 0, 1)
                lyric_img = self.R.render_sweep(
                    text, cur_size, progress,
                    base_color=inactive_col, active_color=active_col,
                    glow_color=(active_col[0]//2, active_col[1]//2, active_col[2]),
                    max_width=W - 80,
                )
            else:
                col = tuple(int(c * alpha) for c in inactive_col)
                if glow > 0:
                    lyric_img = self.R.render(
                        text, cur_size, color=col, max_width=W - 80,
                        glow=True, glow_color=(active_col[0]//3, active_col[1]//3, active_col[2]//2), glow_radius=8,
                        shadow=True, shadow_color=(0, 0, 0),
                    )
                else:
                    lyric_img = self.R.render(
                        text, cur_size, color=col, max_width=W - 80,
                        shadow=True, shadow_color=(0, 0, 0),
                    )

            lx = (W - lyric_img.width) // 2 + offset_x
            frame.paste(lyric_img, (lx, y_cursor + offset_y), lyric_img)

            if is_active and romaji:
                r_img = self.R.render(romaji, romaji_size, color=romaji_col, max_width=W - 80)
                rx = (W - r_img.width) // 2 + offset_x
                frame.paste(r_img, (rx, y_cursor + cur_size + 6 + offset_y), r_img)

            # 中文翻译显示在罗马音下方（仅活跃行）
            if is_active and translation:
                tr_size = max(20, int(lyric_size * 0.72 * scale))
                tr_img = self.R.render(translation, tr_size, color=translation_col, max_width=W - 80)
                tr_x = (W - tr_img.width) // 2 + offset_x
                tr_y = y_cursor + cur_size + 6
                if romaji:
                    tr_y += romaji_size + 4
                frame.paste(tr_img, (tr_x, tr_y + offset_y), tr_img)

            y_cursor += int(base_spacing * scale)

        # ---- Progress indicator ----
        if lines:
            first_s = lines[0].get("start", 0) or 0
            last_e = max((l.get("end", 0) or 0) for l in lines)
            overall = clamp((t - first_s) / max(0.1, last_e - first_s), 0, 1)

            bar_y = int(H * 0.635)
            bar_x, bar_w, bar_h = 50, W - 100, 3

            draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)],
                                   radius=1, fill=(40, 45, 70, 140))
            fill_w = int(bar_w * overall)
            if fill_w > 2:
                for xi in range(fill_w):
                    ratio = xi / max(1, bar_w)
                    r = int(lerp(active_col[0], 255, ratio))
                    g = int(lerp(active_col[1], 255, ratio))
                    b = int(lerp(active_col[2], 255, ratio))
                    draw.line([(bar_x + xi, bar_y), (bar_x + xi, bar_y + bar_h)],
                              fill=(r, g, b, 200))
                dot_x = bar_x + fill_w
                dot_r = 6
                draw.ellipse([dot_x - dot_r - 3, bar_y - dot_r + bar_h//2 - 3,
                              dot_x + dot_r + 3, bar_y + dot_r + bar_h//2 + 3],
                             fill=(*active_col, 50))
                draw.ellipse([dot_x - dot_r, bar_y - dot_r + bar_h//2,
                              dot_x + dot_r, bar_y + dot_r + bar_h//2],
                             fill=(*active_col, 220))
                draw.ellipse([dot_x - dot_r + 2, bar_y - dot_r + bar_h//2 + 2,
                              dot_x + dot_r - 2, bar_y + dot_r + bar_h//2 - 2],
                             fill=(255, 255, 255, 200))

        # ---- Knowledge Notes Section with fly-in animation ----
        note_accent = self._get_note_accent()
        current_notes = []

        # Priority 1: Use per-line vocabulary/grammar data for exact alignment
        if active_idx >= 0 and active_idx < len(lines):
            active_line = lines[active_idx]
            # Build notes from line's own vocabulary and grammar data
            for vocab in active_line.get("vocabulary", []):
                note = {
                    "type": "vocabulary",
                    "data": vocab
                }
                current_notes.append(note)
            for gram in active_line.get("grammar", []):
                note = {
                    "type": "grammar",
                    "data": gram
                }
                current_notes.append(note)

            # Priority 2: If line has no notes but has tokens, extract interesting ones
            if not current_notes:
                current_notes = self._extract_notes_from_tokens(active_line)

        # Priority 3: Fallback to top_notes line_indices matching
        if not current_notes and active_idx >= 0:
            for note in top_notes:
                if active_idx in note.get("line_indices", []):
                    current_notes.append(note)

        # Priority 4: Cycle through notes if no match
        if not current_notes and top_notes:
            cyc = 8
            ni = max(0, int((t - self.intro_s) / cyc)) % len(top_notes)
            current_notes = [top_notes[ni]]

        if current_notes:
            notes_y = int(H * 0.665)

            backdrop = Image.new("RGBA", (W, H - notes_y + 20), (0, 0, 0, 0))
            bd_draw = ImageDraw.Draw(backdrop)
            for row in range(H - notes_y + 20):
                ratio = row / max(1, H - notes_y + 20)
                alpha = int(140 * (1 - ratio * 0.4))
                bd_draw.line([(0, row), (W, row)], fill=(0, 0, 0, alpha))
            backdrop = backdrop.filter(ImageFilter.GaussianBlur(8))
            frame.paste(backdrop, (0, notes_y - 20), backdrop)
            draw = ImageDraw.Draw(frame, "RGBA")

            hf = self.R.bold_font(24)
            icon_x, icon_y = 52, notes_y - 34
            pulse = 0.9 + 0.1 * math.sin(t * 2.5)
            ds = int(9 * pulse)
            draw.polygon([(icon_x, icon_y + ds), (icon_x + ds, icon_y),
                          (icon_x + 2 * ds, icon_y + ds), (icon_x + ds, icon_y + 2 * ds)],
                         fill=(*note_accent, 200))
            draw.text((icon_x + 2 * ds + 10, notes_y - 36),
                      "JP Notes / \u65e5\u672c\u8a9e\u30ce\u30fc\u30c8",
                      font=hf, fill=(180, 195, 230, 255),
                      stroke_width=1, stroke_fill=(10, 10, 30, 80))

            sep_y = notes_y - 10
            for xi in range(52, W - 52):
                ratio = (xi - 52) / max(1, W - 104)
                a = int(70 * min(ratio * 3, (1 - ratio) * 3, 1))
                r = int(lerp(note_accent[0] * 0.6, 80, ratio))
                g = int(lerp(note_accent[1] * 0.6, 110, ratio))
                b = int(lerp(note_accent[2] * 0.6, 180, ratio))
                draw.point((xi, sep_y), fill=(r, g, b, a))

            if active_idx >= 0:
                note_start = lines[active_idx].get("start", 0) or 0
            else:
                note_start = t - 3
            note_age = t - note_start

            card_w = W - 60
            y_cursor = notes_y + 4
            max_cards = 2

            directions = ["bottom", "left"]

            for ni, note in enumerate(current_notes[:max_cards]):
                offset_x, offset_y, scale_val, rotation, alpha_p = NoteCardAnimationEngine.get_card_transform(
                    ni, note_age, direction=directions[ni % len(directions)]
                )

                if scale_val < 0.05 or alpha_p < 0.01:
                    continue

                card = self.R.render_note_card(note, width=int(card_w * 0.97), accent=note_accent)

                if abs(scale_val - 1.0) > 0.01:
                    new_w = max(1, int(card.width * scale_val))
                    new_h = max(1, int(card.height * scale_val))
                    card = card.resize((new_w, new_h), Image.LANCZOS)

                if abs(rotation) > 0.1:
                    card = card.rotate(rotation, resample=Image.BICUBIC, expand=True)

                if alpha_p < 1.0:
                    arr = np.array(card)
                    arr[:, :, 3] = (arr[:, :, 3] * alpha_p).astype(np.uint8)
                    card = Image.fromarray(arr)

                cx = 30 + offset_x
                cx += (card_w - card.width) // 2

                frame.paste(card, (cx, y_cursor + offset_y), card)
                y_cursor += card.height + 16

        # ---- Outro fade ----
        total_dur = 0
        if lines:
            total_dur = max((l.get("end", 0) or 0) for l in lines) + self.outro_s
        if total_dur > 0 and t > total_dur - self.outro_s:
            fp = clamp((t - (total_dur - self.outro_s)) / self.outro_s, 0, 1)
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fp)))
            frame = Image.alpha_composite(frame, overlay)

        return np.array(frame.convert("RGB"))

    def generate_video(self, analyzed_data, audio_path=None, format_name=None, output_name=None):
        if not HAS_MOVIEPY:
            console.print("[red]MoviePy required[/red]")
            return None

        W, H, fps = self._fmt(format_name)
        title = analyzed_data.get("title", "Unknown")
        artist = analyzed_data.get("artist", "Unknown")
        safe = re.sub(r'[^\w\-\u3000-\u9fff\uff00-\uffef]', '_', f"{title}_{artist}")
        output_name = output_name or safe

        lines = analyzed_data.get("analyzed_lines", [])
        if lines:
            duration = max((l.get("end", 0) or 0) for l in lines) + self.outro_s + 1
        else:
            duration = 30
        duration = min(duration, self.max_duration)

        console.print(f"\n[bold cyan]=== Generating Video v3 (Enhanced) ===[/bold cyan]")
        console.print(f"  {title} - {artist}")
        console.print(f"  {W}x{H} @ {fps}fps, {duration:.1f}s")

        # Use a background image if available
        bg_image = self._get_next_bg_image()
        if bg_image:
            console.print(f"  Background: {Path(bg_image).name}")

        bg_engine = self._make_bg_engine(W, H, specific_bg=bg_image)
        particles = ParticleEngine(W, H)

        def make_frame(t):
            return self._render_frame(t, W, H, analyzed_data, bg_engine, particles)

        video = VideoClip(make_frame, duration=duration)

        if audio_path and os.path.exists(audio_path):
            try:
                audio = AudioFileClip(audio_path)
                max_audio = min(duration, audio.duration)
                audio = audio.subclip(0, max_audio) if hasattr(audio, 'subclip') else audio.subclipped(0, max_audio)
                video = video.set_audio(audio) if hasattr(video, 'set_audio') else video.with_audio(audio)
                console.print(f"  Audio: {audio_path}")
            except Exception as e:
                console.print(f"  [yellow]Audio: {e}[/yellow]")

        out = self.output_dir / f"{output_name}_{format_name or self.default_format}.mp4"
        console.print("  Rendering (GPU: NVENC)...")
        try:
            # 使用 NVIDIA NVENC 硬件编码加速
            # 注意：NVENC 不支持 threads 参数，使用 ffmpeg_params 传递编码参数
            try:
                video.write_videofile(str(out), fps=fps, codec="h264_nvenc",
                                      audio_codec="aac", bitrate="6000k",
                                      verbose=False,
                                      ffmpeg_params=["-cq", "25", "-preset", "slow"])
            except TypeError:
                video.write_videofile(str(out), fps=fps, codec="h264_nvenc",
                                      audio_codec="aac", bitrate="6000k",
                                      logger=None,
                                      ffmpeg_params=["-cq", "25", "-preset", "slow"])
            console.print(f"  [green]Saved: {out}[/green]")
            return str(out)
        except Exception as e:
            console.print(f"  [red]Failed: {e}[/red]")
            return None

    def generate_multi_format(self, analyzed_data, audio_path=None):
        results = {}
        for name in self.formats:
            p = self.generate_video(analyzed_data, audio_path, name)
            if p:
                results[name] = p
        return results

    def generate_preview_frame(self, analyzed_data, time=None, format_name=None):
        W, H, _ = self._fmt(format_name)
        lines = analyzed_data.get("analyzed_lines", [])
        if time is None:
            time = (lines[5].get("start", 10) or 10) if len(lines) > 5 else 5

        bg_image = self._get_next_bg_image()
        bg = self._make_bg_engine(W, H, specific_bg=bg_image)
        pe = ParticleEngine(W, H)

        frame = self._render_frame(time, W, H, analyzed_data, bg, pe)
        img = Image.fromarray(frame)

        title = analyzed_data.get("title", "preview")
        safe = re.sub(r'[^\w\-\u3000-\u9fff\uff00-\uffef]', '_', title)
        out = self.output_dir / f"preview_v3_{safe}.png"
        img.save(str(out))
        console.print(f"  [green]Preview: {out}[/green]")
        return str(out)
