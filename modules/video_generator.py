"""
Video Generator Module
=======================
Generates beautiful short videos combining:
- Dynamic flowing lyrics (karaoke-style)
- Romaji readings
- Japanese knowledge notes (vocabulary + grammar)
- Visual effects (glow, particles, gradients)

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

# MoviePy 2.x imports
try:
    from moviepy import (
        VideoClip, AudioFileClip, ImageClip, CompositeVideoClip,
        concatenate_videoclips, ColorClip, TextClip, CompositeAudioClip,
    )
    from moviepy.video.fx import FadeIn, FadeOut
    HAS_MOVIEPY = True
except ImportError:
    try:
        # Fallback for older MoviePy versions
        from moviepy.editor import (
            VideoClip, AudioFileClip, ImageClip, CompositeVideoClip,
            concatenate_videoclips, ColorClip, TextClip, CompositeAudioClip,
        )
        HAS_MOVIEPY = True
    except ImportError:
        HAS_MOVIEPY = False


# ========== Color Utility Functions ==========

def hex_to_rgb(hex_color: str) -> tuple:
    """Convert hex color to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: tuple) -> str:
    """Convert RGB tuple to hex color."""
    return "#{:02x}{:02x}{:02x}".format(*rgb[:3])


def lerp_color(c1: tuple, c2: tuple, t: float) -> tuple:
    """Linearly interpolate between two colors."""
    t = max(0, min(1, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


def ease_in_out(t: float) -> float:
    """Smooth easing function."""
    return t * t * (3 - 2 * t)


def ease_out_cubic(t: float) -> float:
    """Cubic ease-out function."""
    return 1 - (1 - t) ** 3


# ========== Font Management ==========

def find_japanese_font() -> str:
    """Find a suitable Japanese font on the system."""
    # Common Japanese font paths on Windows (prioritize those with good Latin+CJK)
    font_candidates = [
        "C:/Windows/Fonts/YuGothM.ttc",      # Yu Gothic Medium (best for JP+Latin)
        "C:/Windows/Fonts/YuGothB.ttc",      # Yu Gothic Bold
        "C:/Windows/Fonts/meiryo.ttc",       # Meiryo
        "C:/Windows/Fonts/YuGothR.ttc",      # Yu Gothic Regular
        "C:/Windows/Fonts/YuGothL.ttc",      # Yu Gothic Light
        "C:/Windows/Fonts/msgothic.ttc",     # MS Gothic
        "C:/Windows/Fonts/msmincho.ttc",     # MS Mincho
        "C:/Windows/Fonts/segoeui.ttf",      # Segoe UI (fallback)
        # macOS
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        # Linux
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    ]

    for font_path in font_candidates:
        if os.path.exists(font_path):
            return font_path

    # Try to find any CJK font
    import glob
    cjk_fonts = glob.glob("C:/Windows/Fonts/*gothic*") + \
                glob.glob("C:/Windows/Fonts/*mincho*") + \
                glob.glob("C:/Windows/Fonts/*Yu*")
    if cjk_fonts:
        return cjk_fonts[0]

    return None


# ========== Text Rendering ==========

class TextRenderer:
    """Render text with effects using Pillow."""

    def __init__(self, font_path: str = None):
        self.font_path = font_path or find_japanese_font()
        self._font_cache = {}

    def get_font(self, size: int) -> ImageFont.FreeTypeFont:
        """Get a cached font at the given size."""
        if size not in self._font_cache:
            try:
                if self.font_path:
                    self._font_cache[size] = ImageFont.truetype(self.font_path, size)
                else:
                    self._font_cache[size] = ImageFont.load_default()
            except Exception:
                self._font_cache[size] = ImageFont.load_default()
        return self._font_cache[size]

    def render_text(
        self,
        text: str,
        size: int,
        color: tuple = (255, 255, 255),
        max_width: int = None,
        glow: bool = False,
        glow_color: tuple = (100, 180, 255),
        glow_radius: int = 8,
    ) -> Image.Image:
        """
        Render text to a Pillow Image with optional glow effect.
        """
        font = self.get_font(size)

        # Measure text
        dummy_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if max_width and text_w > max_width:
            # Truncate with ellipsis
            while text_w > max_width and len(text) > 1:
                text = text[:-1]
                bbox = draw.textbbox((0, 0), text + "...", font=font)
                text_w = bbox[2] - bbox[0]
            text += "..."
            bbox = draw.textbbox((0, 0), text, font=font)
            text_w = bbox[2] - bbox[0]

        # Add padding for glow
        pad = glow_radius * 2 if glow else 4
        img_w = text_w + pad * 2
        img_h = text_h + pad * 2

        img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if glow:
            # Render glow layer
            glow_img = Image.new("RGBA", (img_w, img_h), (0, 0, 0, 0))
            glow_draw = ImageDraw.Draw(glow_img)
            glow_draw.text((pad, pad), text, font=font, fill=(*glow_color, 180))
            glow_img = glow_img.filter(ImageFilter.GaussianBlur(radius=glow_radius))
            img = Image.alpha_composite(img, glow_img)
            draw = ImageDraw.Draw(img)

        # Render main text
        draw.text((pad, pad), text, font=font, fill=(*color, 255))

        return img

    def render_rich_line(
        self,
        text: str,
        size: int,
        color: tuple = (255, 255, 255),
        highlight_chars: set = None,
        highlight_color: tuple = (0, 220, 255),
    ) -> Image.Image:
        """
        Render text with character-level highlighting.
        """
        font = self.get_font(size)
        dummy_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy_img)

        # Measure total width
        total_w = 0
        max_h = 0
        char_widths = []
        for ch in text:
            bbox = draw.textbbox((0, 0), ch, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
            char_widths.append(w)
            total_w += w
            max_h = max(max_h, h)

        pad = 4
        img = Image.new("RGBA", (total_w + pad * 2, max_h + pad * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        x = pad
        for i, ch in enumerate(text):
            c = highlight_color if (highlight_chars and ch in highlight_chars) else color
            draw.text((x, pad), ch, font=font, fill=(*c, 255))
            x += char_widths[i]

        return img

    def _wrap_text(self, text: str, font: ImageFont.FreeTypeFont, max_width: int) -> list:
        """Wrap text to fit within max_width pixels."""
        dummy = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy)
        lines = []
        current = ""
        for char in text:
            test = current + char
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] > max_width and current:
                lines.append(current)
                current = char
            else:
                current = test
        if current:
            lines.append(current)
        return lines

    def render_note_card(
        self,
        note: dict,
        width: int,
        bg_color: tuple = (25, 25, 50, 220),
        text_color: tuple = (220, 230, 255),
        accent_color: tuple = (0, 200, 255),
    ) -> Image.Image:
        """
        Render a knowledge note card (vocabulary or grammar explanation).
        """
        font_title = self.get_font(24)
        font_body = self.get_font(20)
        font_small = self.get_font(16)

        note_type = note.get("type", "vocabulary")
        data = note.get("data", {})

        # Build card content
        if note_type == "vocabulary":
            word = data.get('word', '')
            level = data.get('jlpt_level', '')
            title = f"{word}  [{level}]"
            reading = data.get("reading", "")
            meaning = data.get("meaning", "")
            lines_text = [
                (title, font_title, accent_color),
                (f"du yin: {reading}", font_body, text_color),
                (f"yi yi: {meaning}", font_body, text_color),
            ]
        else:  # grammar
            pattern = data.get('pattern', '').replace('\u301c', '~')
            level = data.get('level', '')
            title = f"{pattern}  [{level}]"
            meaning = data.get("meaning", "")
            explanation = data.get("explanation", "").replace('\u301c', '~')
            example = data.get("example", "").replace('\u301c', '~')
            lines_text = [
                (title, font_title, accent_color),
                (meaning, font_body, text_color),
            ]
            # Wrap long explanation using pixel width
            if explanation:
                max_text_w = width - 60  # available width
                wrapped_lines = self._wrap_text(explanation, font_small, max_text_w)
                for wl in wrapped_lines:
                    lines_text.append((wl, font_small, (180, 190, 220)))
            if example:
                lines_text.append((f"li: {example}", font_small, (160, 200, 160)))

        # Measure height
        dummy_img = Image.new("RGBA", (1, 1))
        draw = ImageDraw.Draw(dummy_img)
        total_h = 0
        for text, font, color in lines_text:
            bbox = draw.textbbox((0, 0), text, font=font)
            total_h += (bbox[3] - bbox[1]) + 8

        # Add padding
        pad_x, pad_y = 16, 12
        card_h = total_h + pad_y * 2
        card_w = width

        # Draw card background
        img = Image.new("RGBA", (card_w, card_h), bg_color)
        draw = ImageDraw.Draw(img)

        # Accent line on left
        draw.rectangle([(0, 0), (4, card_h)], fill=(*accent_color, 255))

        # Draw text lines
        y = pad_y
        for text, font, color in lines_text:
            draw.text((pad_x + 8, y), text, font=font, fill=(*color, 255))
            bbox = draw.textbbox((0, 0), text, font=font)
            y += (bbox[3] - bbox[1]) + 8

        return img


# ========== Particle System ==========

class Particle:
    """A simple particle for background effects."""
    def __init__(self, x, y, vx, vy, size, color, life):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.size = size
        self.color = color
        self.life = life
        self.max_life = life

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt

    @property
    def alpha(self):
        return max(0, int(255 * (self.life / self.max_life)))


class ParticleSystem:
    """Simple particle system for ambient effects."""

    def __init__(self, width, height, max_particles=50):
        self.width = width
        self.height = height
        self.max_particles = max_particles
        self.particles = []

    def emit(self, count=5):
        """Emit new particles."""
        for _ in range(count):
            if len(self.particles) >= self.max_particles:
                break
            self.particles.append(Particle(
                x=np.random.randint(0, self.width),
                y=self.height + 10,
                vx=np.random.uniform(-15, 15),
                vy=np.random.uniform(-60, -20),
                size=np.random.randint(2, 6),
                color=(
                    np.random.randint(100, 200),
                    np.random.randint(150, 255),
                    255,
                ),
                life=np.random.uniform(2, 6),
            ))

    def update(self, dt):
        """Update all particles."""
        self.emit(count=2)
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]

    def render(self, img: Image.Image):
        """Render particles onto an image."""
        draw = ImageDraw.Draw(img, "RGBA")
        for p in self.particles:
            alpha = p.alpha
            if alpha > 10:
                x, y = int(p.x), int(p.y)
                s = p.size
                draw.ellipse(
                    [(x - s, y - s), (x + s, y + s)],
                    fill=(*p.color, alpha),
                )


# ========== Video Generator ==========

class VideoGenerator:
    """Generate beautiful lyrics videos with knowledge notes."""

    def __init__(self, config: dict):
        self.config = config
        self.video_cfg = config.get("video", {})
        self.style = self.video_cfg.get("style", {})
        self.formats = self.video_cfg.get("formats", {})
        self.default_format = self.video_cfg.get("default_format", "tiktok")
        self.max_duration = self.video_cfg.get("max_duration_seconds", 180)
        self.intro_seconds = self.video_cfg.get("intro_seconds", 3)
        self.outro_seconds = self.video_cfg.get("outro_seconds", 2)

        self.output_dir = Path(config["paths"]["output_dir"]) / "videos"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize text renderer
        self.renderer = TextRenderer()

        if not HAS_MOVIEPY:
            console.print("[red]MoviePy not installed! Video generation will not work.[/red]")
            console.print("[yellow]Install with: pip install moviepy[/yellow]")

    def _get_format(self, format_name: str = None) -> dict:
        """Get video format dimensions."""
        fmt_name = format_name or self.default_format
        fmt = self.formats.get(fmt_name, self.formats.get("tiktok", {}))
        return {
            "width": fmt.get("width", 1080),
            "height": fmt.get("height", 1920),
            "fps": fmt.get("fps", 30),
        }

    def _create_background(self, width: int, height: int, t: float) -> Image.Image:
        """Create animated gradient background."""
        bg_color = tuple(self.style.get("background_color", [15, 15, 25]))

        img = Image.new("RGBA", (width, height), (*bg_color, 255))
        draw = ImageDraw.Draw(img)

        # Animated gradient overlay
        phase = t * 0.3
        for y in range(0, height, 4):
            ratio = y / height
            # Subtle color wave
            r_offset = int(15 * math.sin(phase + ratio * 3))
            g_offset = int(10 * math.sin(phase + ratio * 2 + 1))
            b_offset = int(20 * math.sin(phase + ratio * 4 + 2))

            r = max(0, min(255, bg_color[0] + r_offset))
            g = max(0, min(255, bg_color[1] + g_offset))
            b = max(0, min(255, bg_color[2] + b_offset))

            draw.rectangle([(0, y), (width, y + 4)], fill=(r, g, b, 255))

        return img

    def _render_frame(
        self,
        t: float,
        width: int,
        height: int,
        analyzed_data: dict,
        particles: ParticleSystem,
    ) -> np.ndarray:
        """
        Render a single video frame.
        
        Layout (vertical / 9:16):
        - Top 25%: Title & Song info
        - Middle 45%: Active lyrics + romaji
        - Bottom 30%: Knowledge notes panel
        """
        lines = analyzed_data.get("analyzed_lines", [])
        title = analyzed_data.get("title", "")
        artist = analyzed_data.get("artist", "")
        top_notes = analyzed_data.get("top_notes", [])

        # Create background
        bg = self._create_background(width, height, t)

        # Update and render particles
        particles.update(1.0 / 30)  # Assuming 30fps
        particles.render(bg)

        draw = ImageDraw.Draw(bg, "RGBA")

        # ===== Title Section (Top) =====
        title_font = self.renderer.get_font(28)
        artist_font = self.renderer.get_font(20)

        # Title with fade-in during intro
        title_alpha = min(255, int(255 * min(1, t / self.intro_seconds)))
        title_color = (200, 210, 230, title_alpha)

        # Center title
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_w = title_bbox[2] - title_bbox[0]
        title_x = (width - title_w) // 2
        draw.text((title_x, int(height * 0.06)), title, font=title_font, fill=title_color)

        artist_bbox = draw.textbbox((0, 0), artist, font=artist_font)
        artist_w = artist_bbox[2] - artist_bbox[0]
        artist_x = (width - artist_w) // 2
        draw.text((artist_x, int(height * 0.10)), artist, font=artist_font, fill=(*title_color[:3], title_alpha // 2))

        # Decorative line
        line_y = int(height * 0.135)
        line_w = min(width // 2, title_w + 40)
        line_x = (width - line_w) // 2
        draw.line([(line_x, line_y), (line_x + line_w, line_y)], fill=(80, 120, 180, 120), width=2)

        # ===== Lyrics Section (Middle) =====
        # Find current active line based on time
        active_idx = -1
        for i, line in enumerate(lines):
            start = line.get("start", 0) or 0
            end = line.get("end", 0) or 0
            if start <= t < end:
                active_idx = i
                break

        # Show surrounding lines context (3 lines above, 1 below active)
        lyric_start_idx = max(0, active_idx - 3) if active_idx >= 0 else 0
        lyric_end_idx = min(len(lines), lyric_start_idx + 6)

        lyric_font_size = self.style.get("lyric_font_size", 48)
        romaji_font_size = self.style.get("romaji_font_size", 28)
        inactive_color = tuple(self.style.get("lyric_font_color", [255, 255, 255]))
        active_color = tuple(self.style.get("lyric_active_color", [0, 200, 255]))
        romaji_color = tuple(self.style.get("romaji_color", [180, 180, 200]))

        lyric_y = int(height * 0.18)
        line_spacing = lyric_font_size + romaji_font_size + 20

        for i in range(lyric_start_idx, lyric_end_idx):
            line = lines[i]
            text = line.get("text", "")
            romaji = line.get("romaji", "")
            is_active = (i == active_idx)

            # Calculate fade based on distance from active
            if active_idx >= 0:
                distance = abs(i - active_idx)
                fade = max(0.2, 1.0 - distance * 0.2)
            else:
                fade = 0.3

            # Active line glow effect
            if is_active:
                current_color = active_color
                glow = self.style.get("glow_effect", True)
            else:
                current_color = tuple(int(c * fade) for c in inactive_color[:3])
                glow = False

            # Render lyrics
            lyric_img = self.renderer.render_text(
                text,
                lyric_font_size,
                color=current_color,
                max_width=width - 80,
                glow=glow,
                glow_color=active_color,
                glow_radius=12 if is_active else 0,
            )

            # Paste lyrics
            lx = (width - lyric_img.width) // 2
            bg.paste(lyric_img, (lx, lyric_y), lyric_img)

            # Render romaji below active line
            if is_active and romaji:
                romaji_img = self.renderer.render_text(
                    romaji, romaji_font_size, color=romaji_color, max_width=width - 80
                )
                rx = (width - romaji_img.width) // 2
                bg.paste(romaji_img, (rx, lyric_y + lyric_font_size + 4), romaji_img)

            lyric_y += line_spacing

        # ===== Karaoke progress bar =====
        if lines and active_idx >= 0:
            line = lines[active_idx]
            start = line.get("start", 0) or 0
            end = line.get("end", 0) or start + 1
            progress = (t - start) / max(0.1, end - start)
            progress = max(0, min(1, progress))

            bar_y = int(height * 0.63)
            bar_w = width - 80
            bar_h = 4
            bar_x = 40

            # Background bar
            draw.rectangle([(bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h)], fill=(40, 40, 80, 150))
            # Progress bar
            prog_w = int(bar_w * progress)
            if prog_w > 0:
                draw.rectangle([(bar_x, bar_y), (bar_x + prog_w, bar_y + bar_h)], fill=(*active_color, 200))

        # ===== Knowledge Notes Section (Bottom) =====
        note_font_size = self.style.get("note_font_size", 24)
        note_bg_color = tuple(self.style.get("note_bg_color", [30, 30, 60, 180]))

        # Find notes relevant to current line
        current_notes = []
        if active_idx >= 0:
            for note in top_notes:
                if active_idx in note.get("line_indices", []):
                    current_notes.append(note)

        # Always show some notes
        if not current_notes and top_notes:
            # Show notes based on time cycling
            cycle_time = 8  # seconds per note
            note_idx = int((t - self.intro_seconds) / cycle_time) % len(top_notes)
            current_notes = [top_notes[note_idx]]

        if current_notes:
            notes_y = int(height * 0.67)

            # Section header
            header_font = self.renderer.get_font(18)
            draw.text((40, notes_y - 28), "[*] JP Notes / \u65e5\u672c\u8a9e\u30ce\u30fc\u30c8", font=header_font, fill=(150, 170, 200, 200))

            # Separator
            draw.line([(40, notes_y - 8), (width - 40, notes_y - 8)], fill=(60, 70, 100, 150), width=1)

            # Render note cards
            for note in current_notes[:3]:  # Max 3 notes visible
                card = self.renderer.render_note_card(
                    note, width=width - 80,
                    bg_color=note_bg_color,
                    accent_color=active_color,
                )
                bg.paste(card, (40, notes_y), card)
                notes_y += card.height + 10

        # ===== Outro fade =====
        total_duration = 0
        if lines:
            last_line = lines[-1]
            total_duration = (last_line.get("end", 0) or 0) + self.outro_seconds

        if total_duration > 0 and t > total_duration - self.outro_seconds:
            fade_progress = (t - (total_duration - self.outro_seconds)) / self.outro_seconds
            fade_alpha = int(255 * min(1, fade_progress))
            overlay = Image.new("RGBA", (width, height), (0, 0, 0, fade_alpha))
            bg = Image.alpha_composite(bg, overlay)

        return np.array(bg)

    def generate_video(
        self,
        analyzed_data: dict,
        audio_path: str = None,
        format_name: str = None,
        output_name: str = None,
    ) -> Optional[str]:
        """
        Generate a complete lyrics video.
        
        Args:
            analyzed_data: Analysis result dict from JPAnalyzer
            audio_path: Path to audio file (optional)
            format_name: Video format name (e.g., 'tiktok', 'youtube')
            output_name: Output filename (without extension)
            
        Returns:
            Path to generated video file, or None on failure
        """
        if not HAS_MOVIEPY:
            console.print("[red]MoviePy is required for video generation[/red]")
            return None

        fmt = self._get_format(format_name)
        width = fmt["width"]
        height = fmt["height"]
        fps = fmt["fps"]

        title = analyzed_data.get("title", "Unknown")
        artist = analyzed_data.get("artist", "Unknown")
        safe_title = re.sub(r'[^\w\-\u3000-\u9fff\uff00-\uffef]', '_', f"{title}_{artist}")
        output_name = output_name or safe_title

        # Calculate duration
        lines = analyzed_data.get("analyzed_lines", [])
        if lines:
            last_end = max((l.get("end", 0) or 0) for l in lines)
            duration = last_end + self.outro_seconds + 1
        else:
            duration = 30  # Default

        duration = min(duration, self.max_duration)

        console.print(f"\n[bold cyan]=== Generating Video ===[/bold cyan]")
        console.print(f"  Song: {title} - {artist}")
        console.print(f"  Format: {format_name or self.default_format} ({width}x{height} @ {fps}fps)")
        console.print(f"  Duration: {duration:.1f}s")
        console.print(f"  Lines: {len(lines)}")

        # Create particle system
        particles = ParticleSystem(width, height)

        # Create video clip using make_frame
        def make_frame(t):
            return self._render_frame(t, width, height, analyzed_data, particles)

        video = VideoClip(make_frame, duration=duration)

        # Add audio if available
        if audio_path and os.path.exists(audio_path):
            try:
                audio = AudioFileClip(audio_path)
                audio = audio.subclipped(0, min(duration, audio.duration))
                video = video.with_audio(audio)
                console.print(f"  Audio: {audio_path}")
            except Exception as e:
                console.print(f"  [yellow]Audio loading failed: {e}[/yellow]")

        # Output path
        output_path = self.output_dir / f"{output_name}_{format_name or self.default_format}.mp4"

        # Write video
        console.print(f"  Rendering video... (this may take a while)")
        try:
            video.write_videofile(
                str(output_path),
                fps=fps,
                codec="libx264",
                audio_codec="aac",
                bitrate="5000k",
                threads=4,
                logger=None,  # Suppress MoviePy progress bar
            )
            console.print(f"  [green]Video saved: {output_path}[/green]")
            return str(output_path)
        except Exception as e:
            console.print(f"  [red]Video generation failed: {e}[/red]")
            return None

    def generate_multi_format(
        self,
        analyzed_data: dict,
        audio_path: str = None,
    ) -> dict:
        """
        Generate videos in all configured formats.
        Returns dict mapping format_name -> output_path.
        """
        results = {}
        for fmt_name in self.formats:
            console.print(f"\n  Generating {fmt_name} format...")
            path = self.generate_video(
                analyzed_data,
                audio_path=audio_path,
                format_name=fmt_name,
            )
            if path:
                results[fmt_name] = path

        return results

    def generate_preview_frame(
        self,
        analyzed_data: dict,
        time: float = None,
        format_name: str = None,
    ) -> Optional[str]:
        """
        Generate a single preview frame as an image.
        Useful for previewing before full video render.
        """
        fmt = self._get_format(format_name)
        width = fmt["width"]
        height = fmt["height"]

        # Pick a time that shows lyrics
        if time is None:
            lines = analyzed_data.get("analyzed_lines", [])
            if len(lines) > 5:
                time = lines[5].get("start", 10) or 10
            else:
                time = 5

        particles = ParticleSystem(width, height)
        particles.emit(20)

        frame = self._render_frame(time, width, height, analyzed_data, particles)
        img = Image.fromarray(frame)

        title = analyzed_data.get("title", "preview")
        safe_title = re.sub(r'[^\w\-\u3000-\u9fff\uff00-\uffef]', '_', title)
        output_path = self.output_dir / f"preview_{safe_title}.png"
        img.save(str(output_path))
        console.print(f"  [green]Preview saved: {output_path}[/green]")
        return str(output_path)
