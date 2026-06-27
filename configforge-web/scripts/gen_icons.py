from PIL import Image, ImageDraw
import math

def draw_icon(size, filepath, maskable=False):
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    bg_color = (79, 70, 229, 255)
    radius = size * 96 // 512
    if maskable:
        draw.rectangle([0, 0, size - 1, size - 1], fill=bg_color)
    else:
        draw.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=bg_color)
    cx, cy = size // 2, size // 2
    white = (255, 255, 255, 255)
    outer_r = size * 64 // 512
    ring_w = size * 24 // 512
    draw.ellipse([cx - outer_r, cy - outer_r, cx + outer_r, cy + outer_r], outline=white, width=ring_w)
    center_r = size * 20 // 512
    draw.ellipse([cx - center_r, cy - center_r, cx + center_r, cy + center_r], fill=white)
    tooth_w = size * 28 // 512
    inner = outer_r + ring_w // 2
    outer = outer_r + size * 32 // 512
    for i in range(8):
        angle = i * math.pi / 4
        x1 = cx + inner * math.cos(angle)
        y1 = cy + inner * math.sin(angle)
        x2 = cx + outer * math.cos(angle)
        y2 = cy + outer * math.sin(angle)
        draw.line([x1, y1, x2, y2], fill=white, width=tooth_w)
    dot_r = size * 14 // 512
    dot_y = size * 416 // 512
    for idx, dx in enumerate([96, 160, 224]):
        alpha = [230, 153, 102][idx]
        dot_color = (255, 255, 255, alpha)
        dot_x = size * dx // 512
        draw.ellipse([dot_x - dot_r, dot_y - dot_r, dot_x + dot_r, dot_y + dot_r], fill=dot_color)
    img.save(filepath, 'PNG')
    print(f"Saved {filepath} ({size}x{size})")

draw_icon(192, 'public/icon-192.png')
draw_icon(512, 'public/icon-512.png')
draw_icon(512, 'public/icon-512-maskable.png', maskable=True)
draw_icon(180, 'public/apple-touch-icon.png')
