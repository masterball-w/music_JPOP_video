"""
Video Generator Module v2
==========================
Generates visually stunning short videos combining:
- Karaoke-style lyrics with sweep-fill animation
- Dynamic bokeh / aurora / sakura background
- Smooth slide transitions for lyrics and note cards
- Glass-morphism knowledge note cards with JLPT badges
- Glowing progress indicator

Uses MoviePy 2.x for video compositing and Pillow for text rendering.
"""

import json
import math
import os
import re
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from rich.console import Console

console = Console()

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
#  Utility Functions
# ============================================================

def lerp(a, b, t):
    return a + (b - a) * max(0.0, min(1.0, t))

def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1[:3], c2[:3]))

def ease_out_cubic(t):
    return 1 - (1 - t) ** 3

def ease_in_out(t):
    return t * t * (3 - 2 * t)

def ease_out_back(t):
    c1 = 1.70158
    c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2

def ease_out_elastic(t):
    """Spring-like bounce for dramatic entrances."""
    if t == 0 or t == 1:
        return t
    return math.pow(2, -10 * t) * math.sin((t * 10 - 0.75) * (2 * math.pi / 3)) + 1

def ease_out_quart(t):
    return 1 - (1 - t) ** 4

def clamp(v, lo, hi):
    return max(lo, min(hi, v))


# ============================================================
#  Font Management
# ============================================================

def find_japanese_font() -> str:
    """Find the best available Japanese font, preferring bolder/cleaner ones."""
    candidates = [
        "C:/Windows/Fonts/YuGothB.ttc",    # Yu Gothic Bold - bolder, rounder feel
        "C:/Windows/Fonts/YuGothM.ttc",    # Yu Gothic Medium
        "C:/Windows/Fonts/meiryo.ttc",     # Meiryo
        "C:/Windows/Fonts/YuGothR.ttc",    # Yu Gothic Regular
        "C:/Windows/Fonts/msgothic.ttc",   # MS Gothic
        "C:/Windows/Fonts/msmincho.ttc",   # MS Mincho
        "C:/Windows/Fonts/segoeui.ttf",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    import glob
    for pattern in ("C:/Windows/Fonts/*gothic*", "C:/Windows/Fonts/*Yu*"):
        found = glob.glob(pattern)
        if found:
            return found[0]
    return None


def find_japanese_font_bold() -> str:
    """Find a bold Japanese font for titles and emphasis."""
    candidates = [
        "C:/Windows/Fonts/YuGothB.ttc",
        "C:/Windows/Fonts/meiryob.ttc",
        "C:/Windows/Fonts/YuGothM.ttc",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/segoeui.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return find_japanese_font()


# ============================================================
#  Text Renderer
# ============================================================

class TextRenderer:
    def __init__(self, font_path=None):
        self.font_path = font_path or find_japanese_font()
        self.bold_font_path = find_japanese_font_bold()
        self._cache = {}
        self._bold_cache = {}

    def font(self, size):
        if size not in self._cache:
            try:
                self._cache[size] = ImageFont.truetype(self.font_path, size) if self.font_path else ImageFont.load_default()
            except Exception:
                self._cache[size] = ImageFont.load_default()
        return self._cache[size]

    def bold_font(self, size):
        if size not in self._bold_cache:
            try:
                self._bold_cache[size] = ImageFont.truetype(self.bold_font_path, size) if self.bold_font_path else self.font(size)
            except Exception:
                self._bold_cache[size] = self.font(size)
        return self._bold_cache[size]

    # ----- core text rendering with multi-layer glow -----
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

        # Shadow layer
        if shadow:
            sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(sh).text((pad + shadow_offset, pad + shadow_offset), text, font=f, fill=(*shadow_color, 120))
            sh = sh.filter(ImageFilter.GaussianBlur(shadow_offset + 2))
            img = Image.alpha_composite(img, sh)

        # Glow layer
        if glow:
            gl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(gl).text((pad, pad), text, font=f, fill=(*glow_color, 160))
            gl = gl.filter(ImageFilter.GaussianBlur(glow_radius))
            img = Image.alpha_composite(img, gl)
            # second, tighter glow pass
            gl2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
            ImageDraw.Draw(gl2).text((pad, pad), text, font=f, fill=(*glow_color, 100))
            gl2 = gl2.filter(ImageFilter.GaussianBlur(glow_radius // 3))
            img = Image.alpha_composite(img, gl2)

        # Main text
        ImageDraw.Draw(img).text((pad, pad), text, font=f, fill=(*color[:3], 255))
        return img

    # ----- karaoke sweep text: left portion in active color -----
    def render_sweep(self, text, size, progress,
                     base_color=(200, 200, 220), active_color=(0, 230, 255),
                     glow_color=(60, 180, 255), max_width=None):
        """Render text with a left-to-right sweep fill based on progress 0..1."""
        f = self.font(size)
        dummy = Image.new("RGBA", (1, 1))
        d = ImageDraw.Draw(dummy)
        bb = d.textbbox((0, 0), text, font=f)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        if max_width and tw > max_width:
            tw = max_width
        pad = 20
        W, H = tw + pad * 2, th + pad * 2

        # Render base (inactive) text
        base = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(base).text((pad, pad), text, font=f, fill=(*base_color, 255))

        # Render active (swept) text
        active = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(active).text((pad, pad), text, font=f, fill=(*active_color, 255))

        # Glow layer for active portion
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).text((pad, pad), text, font=f, fill=(*glow_color, 140))
        glow = glow.filter(ImageFilter.GaussianBlur(10))

        # Create sweep mask: white on left, black on right
        sweep_x = int(pad + tw * clamp(progress, 0, 1))
        mask = Image.new("L", (W, H), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rectangle([(0, 0), (sweep_x, H)], fill=255)
        # Soft edge on the sweep boundary
        mask = mask.filter(ImageFilter.GaussianBlur(4))

        # Composite: glow under active text, then active over base using mask
        result = base.copy()
        # Add glow only where active
        glow_masked = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        glow_masked.paste(glow, mask=mask)
        result = Image.alpha_composite(result, glow_masked)
        active_masked = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        active_masked.paste(active, mask=mask)
        result = Image.alpha_composite(result, active_masked)

        return result

    # ----- wrap text to pixel width -----
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

    # ----- rounded rectangle helper -----
    @staticmethod
    def rounded_rect(draw, xy, radius, fill, outline=None, width=0):
        x0, y0, x1, y1 = xy
        r = radius
        # Main body
        draw.rectangle([x0 + r, y0, x1 - r, y1], fill=fill)
        draw.rectangle([x0, y0 + r, x1, y1 - r], fill=fill)
        # Corners
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

    # ----- note card with glass-morphism (v3: large, bold, beautiful) -----
    def render_note_card(self, note, width, accent=(0, 200, 255)):
        """Render a large, visually rich knowledge note card."""
        # Significantly larger fonts
        f_title = self.bold_font(44)       # word / pattern
        f_body = self.font(30)             # reading, meaning
        f_small = self.font(24)            # explanation, examples
        f_badge = self.bold_font(22)       # JLPT level badge

        ntype = note.get("type", "vocabulary")
        data = note.get("data", {})

        # ---- build content lines ----
        if ntype == "vocabulary":
            word = data.get("word", "")
            level = data.get("jlpt_level", "")
            reading = data.get("reading", "")
            meaning = data.get("meaning", "")
            content = [
                ("title", word, f_title, accent),
                ("body", f"読み: {reading}", f_body, (220, 230, 255)),
                ("body", f"意味: {meaning}", f_body, (220, 230, 255)),
            ]
            badge_text = level
        else:
            pat = data.get("pattern", "").replace('\u301c', '~')
            level = data.get("level", "")
            meaning = data.get("meaning", "")
            expl = data.get("explanation", "").replace('\u301c', '~')
            ex = data.get("example", "").replace('\u301c', '~')
            content = [
                ("title", pat, f_title, accent),
                ("body", meaning, f_body, (220, 230, 255)),
            ]
            if expl:
                for wl in self.wrap(expl, f_small, width - 100):
                    content.append(("small", wl, f_small, (180, 195, 225)))
            if ex:
                content.append(("small", f"例: {ex}", f_small, (150, 220, 170)))
            badge_text = level

        # ---- measure card dimensions ----
        dummy = Image.new("RGBA", (1, 1))
        dd = ImageDraw.Draw(dummy)
        total_h = 0
        line_heights = []
        for kind, txt, fo, _ in content:
            bb = dd.textbbox((0, 0), txt, font=fo)
            lh = (bb[3] - bb[1])
            line_heights.append(lh)
            total_h += lh + 14  # 14px spacing between lines

        pad_x, pad_y = 36, 28
        card_w = width
        card_h = total_h + pad_y * 2 + 8
        radius = 24

        # ---- create card image ----
        card = Image.new("RGBA", (card_w, card_h), (0, 0, 0, 0))
        cd = ImageDraw.Draw(card)

        # Frosted glass background with slight gradient
        for row in range(card_h):
            ratio = row / max(1, card_h)
            r = int(18 + 8 * ratio)
            g = int(20 + 6 * ratio)
            b = int(42 + 15 * ratio)
            a = 210
            cd.line([(0, row), (card_w, row)], fill=(r, g, b, a))

        # Mask to rounded rect shape
        mask = Image.new("L", (card_w, card_h), 0)
        md = ImageDraw.Draw(mask)
        self.rounded_rect(md, (0, 0, card_w - 1, card_h - 1), radius, fill=255)
        # Apply mask
        card.putalpha(mask)
        cd = ImageDraw.Draw(card, "RGBA")

        # Glowing border
        for bw in range(3):
            alpha = int(60 - bw * 18)
            self.rounded_rect(cd, (bw, bw, card_w - 1 - bw, card_h - 1 - bw),
                              max(1, radius - bw), fill=None,
                              outline=(accent[0], accent[1], accent[2], max(0, alpha)), width=1)

        # Left accent bar (thicker, with glow)
        bar_x = 10
        bar_w = 5
        for glow_i in range(4):
            ga = max(0, 120 - glow_i * 30)
            cd.rectangle([(bar_x - glow_i, pad_y - glow_i),
                          (bar_x + bar_w + glow_i, card_h - pad_y + glow_i)],
                         fill=(*accent, ga))
        cd.rectangle([(bar_x, pad_y), (bar_x + bar_w, card_h - pad_y)],
                     fill=(*accent, 240))

        # JLPT badge (top-right, pill-shaped)
        badge_colors = {"N5": (80, 190, 80), "N4": (60, 160, 210),
                        "N3": (210, 170, 50), "N2": (210, 110, 50), "N1": (190, 60, 60)}
        bc = badge_colors.get(badge_text, (110, 110, 150))
        bb_badge = dd.textbbox((0, 0), badge_text, font=f_badge)
        badge_tw = bb_badge[2] - bb_badge[0]
        badge_w = badge_tw + 24
        badge_h = 32
        bx = card_w - badge_w - 20
        by = 14
        self.rounded_rect(cd, (bx, by, bx + badge_w, by + badge_h), badge_h // 2,
                          fill=(*bc, 220))
        cd.text((bx + 12, by + 4), badge_text, font=f_badge, fill=(255, 255, 255, 250))

        # ---- Draw content with stroke for rounder look ----
        y = pad_y
        for idx, (kind, txt, fo, col) in enumerate(content):
            tx = pad_x + 16
            stroke_w = 2 if kind == "title" else 1
            stroke_col = (col[0]//3, col[1]//3, col[2]//3, 80)
            # Draw with stroke for bolder, rounder text appearance
            try:
                cd.text((tx, y), txt, font=fo, fill=(*col, 255),
                        stroke_width=stroke_w, stroke_fill=(*stroke_col[:3], stroke_col[3]))
            except TypeError:
                # Fallback for PIL versions without stroke support
                cd.text((tx, y), txt, font=fo, fill=(*col, 255))
            lh = line_heights[idx] if idx < len(line_heights) else 30
            y += lh + 14

        return card


# ============================================================
#  Particle System  (Stateless / Deterministic per-frame)
# ============================================================
#  Key design: every particle's position at time t is computed
#  from its seed parameters + t, so the same t always yields
#  the same frame regardless of render order.
# ============================================================

class ParticleEngine:
    def __init__(self, W, H, n_bokeh=22, n_sakura=12):
        self.W, self.H = W, H
        rng = np.random.RandomState(42)  # fixed seed for reproducibility
        # Pre-generate bokeh parameters
        self.bokeh = []
        for _ in range(n_bokeh):
            self.bokeh.append({
                "x0": rng.uniform(0, W),
                "y0": rng.uniform(0, H),
                "r": rng.uniform(10, 38),
                "vx": rng.uniform(-6, 6),
                "vy": rng.uniform(-14, -3),
                "phase0": rng.uniform(0, math.pi * 2),
                "speed": rng.uniform(0.2, 0.6),
                "alpha": rng.uniform(0.05, 0.16),
                "color": self._rand_color(rng),
            })
        # Pre-generate sakura petal parameters
        self.sakura = []
        for _ in range(n_sakura):
            self.sakura.append({
                "x0": rng.uniform(-40, W + 40),
                "spawn_t": rng.uniform(0, 40),   # time offset when petal appears
                "vx": rng.uniform(-18, 18),
                "vy": rng.uniform(22, 55),
                "angle0": rng.uniform(0, 360),
                "spin": rng.uniform(-80, 80),
                "size": rng.uniform(4, 9),
                "alpha": rng.uniform(0.12, 0.35),
                "color": (255, rng.randint(150, 200), rng.randint(200, 255)),
                "period": rng.uniform(4, 10),    # recycling period
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
        """Render all particles at time t onto img (RGBA PIL Image)."""
        draw = ImageDraw.Draw(img, "RGBA")
        W, H = self.W, self.H

        # --- Bokeh circles (always present, looping positions) ---
        for p in self.bokeh:
            period = max(8, H / max(1, abs(p["vy"])))
            t_loop = t % period
            x = p["x0"] + p["vx"] * t_loop + math.sin(p["phase0"] + t * p["speed"]) * 15
            y = p["y0"] + p["vy"] * t_loop
            # Wrap vertically
            y = y % (H + p["r"] * 2) - p["r"]
            x = x % (W + p["r"] * 2) - p["r"]
            r = p["r"]
            a = int(p["alpha"] * 255)
            if a < 3:
                continue
            col = p["color"]
            # Draw soft concentric circles
            for i in range(3):
                ri = int(r * (1 - i * 0.33))
                ai = int(a * (1 - i * 0.4))
                draw.ellipse([int(x)-ri, int(y)-ri, int(x)+ri, int(y)+ri],
                             fill=(*col, ai))

        # --- Sakura petals (appear/disappear based on time) ---
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


# ============================================================
#  Aurora Background
# ============================================================

class AuroraBackground:
    """Renders a dark gradient with animated aurora-like light waves."""

    def __init__(self, W, H, base_color=(10, 10, 22)):
        self.W, self.H = W, H
        self.base = base_color
        # Pre-compute a vertical gradient base (numpy)
        self._base_arr = self._make_base()

    def _make_base(self):
        arr = np.zeros((self.H, self.W, 4), dtype=np.uint8)
        for y in range(self.H):
            ratio = y / self.H
            r = int(self.base[0] + 12 * ratio)
            g = int(self.base[1] + 8 * ratio)
            b = int(self.base[2] + 25 * ratio)
            arr[y, :] = [r, g, b, 255]
        return arr

    def render(self, t):
        img = Image.fromarray(self._base_arr.copy(), "RGBA")
        draw = ImageDraw.Draw(img, "RGBA")

        # Aurora waves: 3 layered sine bands
        waves = [
            {"y_ratio": 0.25, "amp": 40, "freq": 1.8, "speed": 0.25,
             "color": (30, 80, 180, 18), "width": 80},
            {"y_ratio": 0.45, "amp": 30, "freq": 2.5, "speed": 0.35,
             "color": (60, 40, 160, 14), "width": 60},
            {"y_ratio": 0.70, "amp": 50, "freq": 1.2, "speed": 0.18,
             "color": (20, 100, 140, 16), "width": 100},
        ]
        for w in waves:
            base_y = int(self.H * w["y_ratio"])
            pts = []
            for x in range(0, self.W + 1, 6):
                xr = x / self.W
                y = base_y + int(w["amp"] * math.sin(xr * w["freq"] * math.pi + t * w["speed"])
                                 + w["amp"] * 0.4 * math.sin(xr * w["freq"] * 2.3 * math.pi + t * w["speed"] * 1.7))
                pts.append((x, y))
            # Draw as a filled polygon band
            poly = pts + [(self.W, pts[-1][1] + w["width"]), (0, pts[0][1] + w["width"])]
            draw.polygon(poly, fill=w["color"])

        # Subtle vignette overlay
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
#  Video Generator (main class)
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
        if not HAS_MOVIEPY:
            console.print("[red]MoviePy not installed[/red]")

    # ---------- helpers ----------
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

    # ---------- main frame renderer ----------
    def _render_frame(self, t, W, H, data, bg_engine, particles):
        lines = data.get("analyzed_lines", [])
        title = data.get("title", "")
        artist = data.get("artist", "")
        top_notes = data.get("top_notes", [])

        # ---- 1. Background ----
        frame = bg_engine.render(t)
        particles.render(t, frame)
        draw = ImageDraw.Draw(frame, "RGBA")

        # ---- 2. Title area ----
        intro_p = clamp(t / self.intro_s, 0, 1)
        title_alpha = int(255 * ease_out_cubic(intro_p))
        title_slide = int(20 * (1 - ease_out_cubic(intro_p)))

        tf = self.R.font(32)
        af = self.R.font(20)

        # Title
        tbb = draw.textbbox((0, 0), title, font=tf)
        tw = tbb[2] - tbb[0]
        tx = (W - tw) // 2
        ty = int(H * 0.055) - title_slide
        draw.text((tx, ty), title, font=tf, fill=(230, 235, 250, title_alpha))

        # Artist
        abb = draw.textbbox((0, 0), artist, font=af)
        aw = abb[2] - abb[0]
        ax = (W - aw) // 2
        ay = ty + 40
        draw.text((ax, ay), artist, font=af, fill=(160, 170, 200, title_alpha // 2))

        # Animated decorative line under title
        line_w_max = min(W // 2, tw + 60)
        line_progress = ease_out_cubic(clamp((t - 0.5) / 1.5, 0, 1))
        line_w = int(line_w_max * line_progress)
        if line_w > 2:
            ly = ay + 30
            lx0 = (W - line_w) // 2
            # Gradient line
            for xi in range(line_w):
                ratio = xi / max(1, line_w)
                # Fade at edges
                edge_fade = min(ratio * 4, (1 - ratio) * 4, 1)
                a = int(100 * edge_fade * line_progress)
                r = int(lerp(60, 0, ratio))
                g = int(lerp(140, 200, ratio))
                b = int(lerp(220, 255, ratio))
                draw.point((lx0 + xi, ly), fill=(r, g, b, a))
                draw.point((lx0 + xi, ly + 1), fill=(r, g, b, a // 2))

        # ---- 3. Lyrics area ----
        active_idx = self._find_active(lines, t)
        visible_count = 5
        start_idx = max(0, active_idx - 2) if active_idx >= 0 else 0
        end_idx = min(len(lines), start_idx + visible_count)

        lyric_size = self.style.get("lyric_font_size", 50)
        romaji_size = self.style.get("romaji_font_size", 28)
        active_col = tuple(self.style.get("lyric_active_color", [0, 220, 255]))
        inactive_col = (180, 185, 210)
        romaji_col = (150, 160, 190)

        # Compute vertical positions with active-line scale
        base_spacing = lyric_size + romaji_size + 28
        active_scale = 1.12  # active line is 12% bigger
        lyric_top = int(H * 0.175)
        y_cursor = lyric_top

        for i in range(start_idx, end_idx):
            ln = lines[i]
            text = ln.get("text", "")
            romaji = ln.get("romaji", "")
            is_active = (i == active_idx)

            # Distance-based fade & scale
            if active_idx >= 0:
                dist = abs(i - active_idx)
                fade = clamp(1.0 - dist * 0.22, 0.15, 1.0)
                scale = active_scale if is_active else lerp(1.0, 0.92, min(dist, 3) / 3)
            else:
                fade, scale = 0.25, 0.92

            cur_size = max(16, int(lyric_size * scale))

            if is_active:
                # Karaoke sweep fill
                s = ln.get("start", 0) or 0
                e = ln.get("end", 0) or s + 1
                progress = clamp((t - s) / max(0.1, e - s), 0, 1)
                lyric_img = self.R.render_sweep(
                    text, cur_size, progress,
                    base_color=inactive_col, active_color=active_col,
                    glow_color=(active_col[0]//2, active_col[1]//2, active_col[2]),
                    max_width=W - 80,
                )
            else:
                col = tuple(int(c * fade) for c in inactive_col)
                lyric_img = self.R.render(
                    text, cur_size, color=col, max_width=W - 80,
                    shadow=True, shadow_color=(0, 0, 0),
                )

            lx = (W - lyric_img.width) // 2
            # Slight vertical slide for active line
            v_offset = -8 if is_active else 0
            frame.paste(lyric_img, (lx, y_cursor + v_offset), lyric_img)

            # Romaji under active line
            if is_active and romaji:
                r_img = self.R.render(romaji, romaji_size, color=romaji_col, max_width=W - 80)
                rx = (W - r_img.width) // 2
                frame.paste(r_img, (rx, y_cursor + cur_size + 6 + v_offset), r_img)

            y_cursor += int(base_spacing * scale)

        # ---- 4. Progress indicator ----
        if lines:
            first_s = lines[0].get("start", 0) or 0
            last_e = max((l.get("end", 0) or 0) for l in lines)
            overall = clamp((t - first_s) / max(0.1, last_e - first_s), 0, 1)

            bar_y = int(H * 0.635)
            bar_x, bar_w, bar_h = 50, W - 100, 3

            # Track
            draw.rounded_rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)],
                                   radius=1, fill=(40, 45, 70, 140))
            # Filled portion with gradient
            fill_w = int(bar_w * overall)
            if fill_w > 2:
                for xi in range(fill_w):
                    ratio = xi / max(1, bar_w)
                    r = int(lerp(active_col[0], 255, ratio))
                    g = int(lerp(active_col[1], 255, ratio))
                    b = int(lerp(active_col[2], 255, ratio))
                    draw.line([(bar_x + xi, bar_y), (bar_x + xi, bar_y + bar_h)],
                              fill=(r, g, b, 200))
                # Glowing dot at the head
                dot_x = bar_x + fill_w
                dot_r = 6
                # Outer glow
                draw.ellipse([dot_x - dot_r - 3, bar_y - dot_r + bar_h//2 - 3,
                              dot_x + dot_r + 3, bar_y + dot_r + bar_h//2 + 3],
                             fill=(*active_col, 50))
                draw.ellipse([dot_x - dot_r, bar_y - dot_r + bar_h//2,
                              dot_x + dot_r, bar_y + dot_r + bar_h//2],
                             fill=(*active_col, 220))
                draw.ellipse([dot_x - dot_r + 2, bar_y - dot_r + bar_h//2 + 2,
                              dot_x + dot_r - 2, bar_y + dot_r + bar_h//2 - 2],
                             fill=(255, 255, 255, 200))

        # ---- 5. Knowledge Notes Section ----
        current_notes = []
        if active_idx >= 0:
            for note in top_notes:
                if active_idx in note.get("line_indices", []):
                    current_notes.append(note)
        if not current_notes and top_notes:
            cyc = 8
            ni = max(0, int((t - self.intro_s) / cyc)) % len(top_notes)
            current_notes = [top_notes[ni]]

        if current_notes:
            notes_y = int(H * 0.665)

            # ---- Section header ----
            hf = self.R.bold_font(22)
            icon_x, icon_y = 52, notes_y - 34
            # Animated diamond icon (slow rotation effect via scale)
            pulse = 0.9 + 0.1 * math.sin(t * 2.5)
            ds = int(9 * pulse)
            draw.polygon([(icon_x, icon_y + ds), (icon_x + ds, icon_y),
                          (icon_x + 2 * ds, icon_y + ds), (icon_x + ds, icon_y + 2 * ds)],
                         fill=(*active_col, 200))
            draw.text((icon_x + 2 * ds + 10, notes_y - 36),
                      "JP Notes / 日本語ノート",
                      font=hf, fill=(160, 175, 215, 240),
                      stroke_width=1, stroke_fill=(10, 10, 30, 80))

            # Gradient separator line
            sep_y = notes_y - 10
            for xi in range(52, W - 52):
                ratio = (xi - 52) / max(1, W - 104)
                a = int(70 * min(ratio * 3, (1 - ratio) * 3, 1))
                r = int(lerp(active_col[0] * 0.6, 80, ratio))
                g = int(lerp(active_col[1] * 0.6, 110, ratio))
                b = int(lerp(active_col[2] * 0.6, 180, ratio))
                draw.point((xi, sep_y), fill=(r, g, b, a))

            # ---- Calculate timing for entrance animation ----
            if active_idx >= 0:
                note_start = lines[active_idx].get("start", 0) or 0
            else:
                note_start = t - 3  # assume notes have been showing
            note_age = t - note_start

            # Pre-determined tilt angles for each card slot (deterministic)
            tilt_angles = [-2.5, 3.0, -1.5]  # degrees
            # Horizontal stagger offsets
            x_offsets = [0, 20, 10]

            # ---- Render tilted cards with dramatic entrance ----
            card_w = W - 60
            y_cursor = notes_y + 4
            max_cards = 2

            for ni, note in enumerate(current_notes[:max_cards]):
                card_delay = ni * 0.3
                card_age = max(0, note_age - card_delay)

                # ---- Entrance animation progress ----
                # Scale: 0.2 -> 1.0 with elastic overshoot
                scale_p = ease_out_elastic(clamp(card_age / 0.7, 0, 1))
                scale_val = lerp(0.2, 1.0, scale_p)

                # Rotation: starts rotated more, settles to target tilt
                target_tilt = tilt_angles[ni % len(tilt_angles)]
                start_tilt = target_tilt - 12  # start 12° more rotated
                rot_p = ease_out_quart(clamp(card_age / 0.6, 0, 1))
                current_tilt = lerp(start_tilt, target_tilt, rot_p)

                # Opacity: fast fade in
                alpha_p = clamp(card_age / 0.3, 0, 1)

                if scale_val < 0.05 or alpha_p < 0.01:
                    continue  # not visible yet

                # Render the base card
                card = self.R.render_note_card(note, width=int(card_w * 0.97), accent=active_col)

                # ---- Apply scale (resize) ----
                if abs(scale_val - 1.0) > 0.01:
                    new_w = max(1, int(card.width * scale_val))
                    new_h = max(1, int(card.height * scale_val))
                    card = card.resize((new_w, new_h), Image.LANCZOS)

                # ---- Apply rotation (tilt) ----
                if abs(current_tilt) > 0.1:
                    card = card.rotate(current_tilt, resample=Image.BICUBIC, expand=True)

                # ---- Apply opacity ----
                if alpha_p < 1.0:
                    arr = np.array(card)
                    arr[:, :, 3] = (arr[:, :, 3] * alpha_p).astype(np.uint8)
                    card = Image.fromarray(arr)

                # ---- Position on frame ----
                # Center the tilted card horizontally with stagger
                cx = 30 + x_offsets[ni % len(x_offsets)]
                # Adjust for rotation expansion (keep visually centered)
                cx += (card_w - card.width) // 2

                frame.paste(card, (cx, y_cursor), card)
                y_cursor += card.height + 16

        # ---- 6. Outro fade ----
        total_dur = 0
        if lines:
            total_dur = max((l.get("end", 0) or 0) for l in lines) + self.outro_s
        if total_dur > 0 and t > total_dur - self.outro_s:
            fp = clamp((t - (total_dur - self.outro_s)) / self.outro_s, 0, 1)
            overlay = Image.new("RGBA", (W, H), (0, 0, 0, int(255 * fp)))
            frame = Image.alpha_composite(frame, overlay)

        return np.array(frame.convert("RGB"))

    # =========================================================
    #  Public API
    # =========================================================

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

        console.print(f"\n[bold cyan]=== Generating Video v2 ===[/bold cyan]")
        console.print(f"  {title} - {artist}")
        console.print(f"  {W}x{H} @ {fps}fps, {duration:.1f}s")

        bg_engine = AuroraBackground(W, H)
        particles = ParticleEngine(W, H)

        def make_frame(t):
            return self._render_frame(t, W, H, analyzed_data, bg_engine, particles)

        video = VideoClip(make_frame, duration=duration)

        if audio_path and os.path.exists(audio_path):
            try:
                audio = AudioFileClip(audio_path)
                max_audio = min(duration, audio.duration)
                # MoviePy 1.x: subclip()  /  2.x: subclipped()
                audio = audio.subclip(0, max_audio) if hasattr(audio, 'subclip') else audio.subclipped(0, max_audio)
                # MoviePy 1.x: set_audio()  /  2.x: with_audio()
                video = video.set_audio(audio) if hasattr(video, 'set_audio') else video.with_audio(audio)
                console.print(f"  Audio: {audio_path}")
            except Exception as e:
                console.print(f"  [yellow]Audio: {e}[/yellow]")

        out = self.output_dir / f"{output_name}_{format_name or self.default_format}.mp4"
        console.print("  Rendering...")
        try:
            # MoviePy 1.x uses verbose=False; 2.x uses logger=None
            try:
                video.write_videofile(str(out), fps=fps, codec="libx264",
                                      audio_codec="aac", bitrate="6000k",
                                      threads=4, verbose=False)
            except TypeError:
                video.write_videofile(str(out), fps=fps, codec="libx264",
                                      audio_codec="aac", bitrate="6000k",
                                      threads=4, logger=None)
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

        bg = AuroraBackground(W, H)
        pe = ParticleEngine(W, H)

        frame = self._render_frame(time, W, H, analyzed_data, bg, pe)
        img = Image.fromarray(frame)

        title = analyzed_data.get("title", "preview")
        safe = re.sub(r'[^\w\-\u3000-\u9fff\uff00-\uffef]', '_', title)
        out = self.output_dir / f"preview_v2_{safe}.png"
        img.save(str(out))
        console.print(f"  [green]Preview: {out}[/green]")
        return str(out)
