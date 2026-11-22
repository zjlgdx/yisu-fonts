"""python tools/hz_sheet.py OUT.jpg [--batch A.py,B.py] [CHARS] [--size N] [--mainland]

A contact sheet for drawing: each character in Yinni, Huasha
and Louhen Bold, with Huasha again at twice the size. With no CHARS,
every character the batches define (C[...] = ...).
"""
import argparse
import re
from pathlib import Path
import _repo
from PIL import Image, ImageDraw, ImageFont

ap = argparse.ArgumentParser()
ap.add_argument('out')
ap.add_argument('chars', nargs='?', default='')
ap.add_argument('--batch', default='')
ap.add_argument('--size', type=int, default=80)
ap.add_argument('--per', type=int, default=12, help='characters per row')
ap.add_argument('--mainland', action='store_true', help="draw the mainland's form where a character has one")
a = ap.parse_args()

hs = _repo.load(a.batch)
if a.mainland:
    hs.C.update(hs.ZHS)
import build
import hanzi

chars = a.chars
if not chars:
    src = ''.join(Path(f).read_text(encoding='utf-8') for f in a.batch.split(',') if f)
    chars = ''.join(dict.fromkeys(re.findall(r"^C\['(.)'\]\s*=", src, re.M)))


def tile(St, ch, size, bold=False):
    s = St(bold)
    em = hanzi.CUTS[s.key]['em']
    img = build.canvas(s, ch)
    s.draw(ch, img)
    w = em / build.K * build.S
    cx0 = -build.X0 * build.S
    cy = (400 - build.Y0) * build.S
    c = img.crop((int(cx0), int(cy - w / 2), int(cx0 + w), int(cy + w / 2)))
    return c.resize((int(size * em / 1000), int(size * em / 1000)), Image.LANCZOS)


def label_font():
    for p in ('/System/Library/Fonts/Hiragino Sans GB.ttc', '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc'):
        if Path(p).exists():
            return ImageFont.truetype(p, 16)
    return ImageFont.load_default()


fams = [(build.Yinni, False), (build.Huasha, False), (build.Louhen, True)]
cells = []
skip = [ch for ch in chars if ch not in hs.C]
if skip:
    print('not characters (only components or undrawn), skipped:', ''.join(skip))
for ch in [c for c in chars if c in hs.C]:
    ts = [tile(St, ch, a.size, b) for St, b in fams]
    big = tile(build.Huasha, ch, a.size * 2)
    cell = Image.new('L', (max(sum(t.width for t in ts), big.width) + 10, big.height + ts[0].height + 26), 0)
    x = 0
    for t in ts:
        cell.paste(t, (x, 0))
        x += t.width
    cell.paste(big, ((cell.width - 10 - big.width) // 2, ts[0].height + 4))   # centred, so it can't look shifted
    cells.append((ch, cell))
cw = max(c.width for _, c in cells)
chh = max(c.height for _, c in cells)
nrows = -(-len(cells) // a.per)
im = Image.new('RGB', (cw * min(a.per, len(cells)) + 20, nrows * (chh + 24) + 20), (251, 248, 240))
d = ImageDraw.Draw(im)
lab = label_font()
for i, (ch, c) in enumerate(cells):
    x, y = 10 + (i % a.per) * cw, 10 + (i // a.per) * (chh + 24)
    d.rectangle((x, y + 22, x + c.width - 10, y + 22 + c.height - 26), outline=(230, 220, 205))
    im.paste(Image.new('RGB', c.size, (43, 58, 85)), (x, y + 22), c)
    d.text((x + 2, y + 18), f'{ch} U+{ord(ch):04X}', font=lab, fill=(150, 130, 110), anchor='ls')
im.save(a.out, quality=85)
print(a.out, im.size, len(cells))
