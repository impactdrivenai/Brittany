"""Designed overlays with Pillow: end card, CTA button, cover image, text cards (carousel/stories).
Everything is a transparent PNG composited after the grade, so brand colours stay exact."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from .util import FONTS_DIR, hex_to_rgb, W, H

_SYS_FALLBACKS = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]


def font(file_name, size):
    p = FONTS_DIR / (file_name or "")
    if p.exists():
        return ImageFont.truetype(str(p), int(size))
    for fb in _SYS_FALLBACKS:
        if Path(fb).exists():
            return ImageFont.truetype(fb, int(size))
    return ImageFont.load_default()


def text_w(draw, text, f):
    l, t, r, b = draw.textbbox((0, 0), text, font=f)
    return r - l, b - t


def wrap(draw, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        test = (cur + " " + w).strip()
        if text_w(draw, test, f)[0] <= max_w or not cur:
            cur = test
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def rgba(hex_color, a=255):
    return hex_to_rgb(hex_color) + (a,)


def end_card(style, out_png):
    ec, c, fo = style["end_card"], style["colors"], style["fonts"]
    img = Image.new("RGB", (W, H), hex_to_rgb(c[ec.get("bg", "light")]))
    d = ImageDraw.Draw(img)
    fg = hex_to_rgb(c[ec.get("fg", "dark")])
    f1 = font(fo["title_file"], 104); f2 = font(fo["caption_file"], 40)
    l1, l2 = ec.get("line1", ""), ec.get("line2", "")
    w1, h1 = text_w(d, l1, f1); w2, h2 = text_w(d, l2, f2)
    d.text(((W - w1) / 2, H / 2 - h1 - 18), l1, font=f1, fill=fg)
    d.text(((W - w2) / 2, H / 2 + 22), l2, font=f2, fill=fg)
    img.save(out_png, quality=95)
    return out_png


def cta_button(style, text, keyword, out_png):
    """Transparent full-frame PNG with a rounded button bar in the last-2.5-seconds position (above the IG UI)."""
    c, fo, cta = style["colors"], style["fonts"], style["cta"]
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    f_small = font(fo["caption_bold_file"] if "caption_bold_file" in fo else fo["caption_file"], 54)
    f_key = font(fo["hero_file"], 66)
    if cta.get("style") == "spread" and keyword:
        # words spread wide across the centre of the frame, keyword in accent
        parts = text.replace(keyword, "").split() + [keyword]
        y = H // 2 - 60
        total = sum(text_w(d, p, f_key if p == keyword else f_small)[0] for p in parts) + 60 * (len(parts) - 1)
        x = (W - total) / 2
        for p in parts:
            f = f_key if p == keyword else f_small
            col = rgba(c["accent"]) if p == keyword else rgba(c["light"])
            d.text((x + 3, y + 4), p, font=f, fill=(0, 0, 0, 140))
            d.text((x, y), p, font=f, fill=col)
            x += text_w(d, p, f)[0] + 60
        img.save(out_png); return out_png
    pre = text.replace(keyword, "").strip() if keyword else text
    w_pre, h_pre = text_w(d, pre, f_small) if pre else (0, 0)
    w_key, h_key = text_w(d, keyword, f_key) if keyword else (0, 0)
    pad_x, gap = 56, 18 if (pre and keyword) else 0
    bw = w_pre + gap + w_key + pad_x * 2
    bh = 132
    x0 = (W - bw) / 2; y0 = 1390 - bh / 2
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle((x0, y0 + 10, x0 + bw, y0 + bh + 10), radius=bh / 2, fill=(0, 0, 0, 110))
    shadow = shadow.filter(ImageFilter.GaussianBlur(14))
    img = Image.alpha_composite(img, shadow)
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=bh / 2, fill=rgba(c[cta.get("bg", "accent")]))
    fg = rgba(c[cta.get("fg", "light")])
    x = x0 + pad_x
    if pre:
        d.text((x, y0 + (bh - h_pre) / 2 - 8), pre, font=f_small, fill=fg); x += w_pre + gap
    if keyword:
        d.text((x, y0 + (bh - h_key) / 2 - 10), keyword, font=f_key, fill=fg)
    img.save(out_png)
    return out_png


def cover(frame_path, hook_text, style, out_path):
    """Hook frame + the hook line as an editorial caption = a cover people stop on."""
    c, fo = style["colors"], style["fonts"]
    img = Image.open(frame_path).convert("RGB").resize((W, H))
    # gentle darkening so the words read
    shade = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shade).rectangle((0, 0, W, H), fill=(0, 0, 0, 70))
    img = Image.alpha_composite(img.convert("RGBA"), shade)
    d = ImageDraw.Draw(img)
    f_small = font(fo["caption_file"], 64); f_hero = font(fo["hero_file"], 128)
    words = hook_text.split()
    if not words:
        img.convert("RGB").save(out_path, quality=92); return out_path
    from .captions import _hero
    h, _ = _hero(words)
    before, hero, after = " ".join(words[:h]), words[h], " ".join(words[h + 1:])
    blocks = []
    for txt, f in ((before, f_small), (hero, f_hero), (after, f_small)):
        if txt:
            for ln in wrap(d, txt, f, W - 160):
                blocks.append((ln, f))
    total_h = sum(text_w(d, ln, f)[1] + 18 for ln, f in blocks)
    y = H * 0.30 - total_h / 2
    for ln, f in blocks:
        w, hh = text_w(d, ln, f)
        col = rgba(c["accent"]) if f is f_hero else rgba(c["light"])
        d.text(((W - w) / 2 + 3, y + 5), ln, font=f, fill=(0, 0, 0, 150))
        d.text(((W - w) / 2, y), ln, font=f, fill=col)
        y += hh + 18
    img.convert("RGB").save(out_path, quality=92)
    return out_path


def text_card(style, title, body, out_path, size=(1080, 1350), bg="light", fg="dark", accent_word=None, footer=None, number=None):
    """Carousel / story card: eyebrow number, big serif title with one accent word, body in sans."""
    c, fo = style["colors"], style["fonts"]
    cw, ch = size
    img = Image.new("RGB", size, hex_to_rgb(c[bg]))
    d = ImageDraw.Draw(img)
    fgc = hex_to_rgb(c[fg]); acc = hex_to_rgb(c["accent"])
    margin = 96
    y = margin + 40
    if number is not None:
        f_n = font(fo["caption_file"], 40)
        d.text((margin, y), f"{number:02d}", font=f_n, fill=acc)
        d.line((margin, y + 58, margin + 56, y + 58), fill=acc, width=4)
        y += 110
    f_t = font(fo["title_file"], 92 if len(title) < 60 else 74)
    for ln in wrap(d, title, f_t, cw - 2 * margin):
        x = margin
        for word in ln.split():
            col = acc if accent_word and word.strip(".,!?").lower() == accent_word.lower() else fgc
            d.text((x, y), word, font=f_t, fill=col)
            x += text_w(d, word + " ", f_t)[0]
        y += text_w(d, ln, f_t)[1] + 22
    if body:
        y += 40
        f_b = font(fo["caption_file"], 44)
        for ln in wrap(d, body, f_b, cw - 2 * margin):
            d.text((margin, y), ln, font=f_b, fill=fgc); y += text_w(d, ln, f_b)[1] + 16
    if footer:
        f_f = font(fo["caption_file"], 34)
        d.text((margin, ch - margin - 20), footer, font=f_f, fill=fgc)
    img.save(out_path, quality=95)
    return out_path
