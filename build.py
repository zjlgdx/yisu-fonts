"""Build the 一粟 (Yisu) fonts from the pen skeletons in skeleton.py.

Each glyph's centre line is written with a pen on a large bitmap, traced
back to curves with potrace, spaced from its own shape, kerned, and
assembled into an OpenType (CFF) font and a WOFF2 copy in out/. Each
family comes in Regular and Bold: the Bold is the same skeletons written
with a wider pen (and, for the handwriting, a little wider), then spaced
and kerned afresh.

    .venv/bin/python build.py            # all fonts
    .venv/bin/python build.py louhen     # one family, both weights

The pens (the key, and the nickname the fonts had up to 0.730):
  huasha  the Ballpoint: a fine round pen leaning 9 degrees, with light pressure changes
  louhen  the Marker: a chisel nib held at 35 degrees, upright
  yinni   the Typewriter: a round pen with slab serifs, monospaced, struck through an
          inked ribbon: uneven ink, dry patches, letters a little off line

What follows the usual type-design rules (see README.md for sources):
  - round shapes overshoot the baseline, x-height, cap height and figure
    height by about 2% so they look as tall as flat ones
  - the round pens are a little flatter than round, so horizontal strokes
    come out slightly lighter than vertical ones
  - sidebearings come from each letter's own profile: straight sides get
    the full space, round sides less, open and diagonal sides least
  - kerning is measured from the same profiles for every letter pair
  - the two handwriting fonts carry two alternates of each lowercase letter
    and cycle them (`calt`), so a double letter is never drawn twice alike
  - an accented letter is its base letter's drawing plus a mark, placed
    clear of the letter for the pen in use; it keeps the base's spacing
    and kerning class, with its own pair wherever the accent would collide
  - combining marks are zero-width GDEF marks, attached by anchors taken
    from the same placement (mark, mkmk), with ccmp for dotless i and j and
    for the flatter capital forms of marks above
  - Yinni's box drawing and block elements are made to the cell,
    not with a pen, so they join across columns and rows
  - curves get points at their extremes; outer contours run
    counter-clockwise, as CFF expects
  - flat strokes stand on the baseline: the skeleton's lines are the pen's
    centre, so each font is lifted by how far its ink reaches below them,
    and the x-height and cap height are the ink's own
  - vertical metrics follow the Google Fonts guide: typo metrics in use,
    a 1.24 em line, caps centred in it, win metrics at the font's bounds
  - hinted by AFDKO's otfautohint from alignment zones and stems measured
    here (box drawing and blocks excepted, so they keep the cell's edges)
  - the .otf is subroutinized; the .woff2 is not, as Brotli packs plain
    charstrings smaller
"""

import hashlib
import io
import math
import os
import pickle
import random
import re
import unicodedata
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from fontTools.agl import UV2AGL
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.misc.bezierTools import splitCubicAtT
from fontTools.pens.basePen import BasePen
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.roundingPen import RoundingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.pens.pointInsidePen import PointInsidePen
from fontTools.pens.transformPen import TransformPen
from fontTools.svgLib.path import parse_path
from fontTools.ttLib import TTFont

import cells
import cffsubr
import hanzi
from skeleton import (ACCENTED, ALL, ANCHOR, COMBINING_MARKS, KEEP_SHAPE, base_anchors, base_of, cells as wide_cells,
                      charset, mark_anchors, parts)

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
# Each glyph's traced outline is kept in work/cache/ and used again while nothing that
# draws it has changed: its own strokes (hashed per glyph) and the drawing code. Any edit
# to the code files below throws the whole cache away, so a pen or tracing change can never
# leave old outlines behind. The stroke tables are hashed per glyph instead, so editing a
# few characters redraws only those. A release is built with --no-cache all the same.
CACHE_DIR = HERE / 'work' / 'cache'
CODE = ('build.py', 'cells.py', 'hanzi.py', 'outline.py', 'skeleton.py', 'spacing.py')

VERSION = 0.994         # head.fontRevision; nameID 5 says the same

S = 2.0                 # bitmap pixels per skeleton unit
X0, Y0 = -200, -300     # bitmap origin, in skeleton units: room above for capital accents
W, H = 1100, 1450       # bitmap size, in skeleton units
K = 0.86                # skeleton unit -> font unit
BASE = 750              # skeleton baseline: where the pen's centre runs, not the ink's edge

# Skeleton lines that round shapes overshoot, and by how much.
LOWER_LINES = (40, 250, 750, 960)   # ascender, x-height, baseline, descender
UPPER_LINES = (50, 750)             # cap height and figure height, baseline
OVERSHOOT = 12                      # skeleton units: ~10 font units, 2.4% of x-height

# Vertical metrics: a 1.24 em line with the caps centred in it
# (ascender - cap height = |descender|), worked out per font.
LINE = 1240

# The underscore's top edge, and so the underline's, in font units: clear of
# the round letters' overshoot (about -15) in every pen, Bold included.
UNDERSCORE_TOP = -40

# ---------------------------------------------------------------- paths

TOKEN = re.compile(r'[MLCZFmlczf]|-?(?:\d+\.?\d*|\.\d+)')


def subpaths(d):
    """Flatten an SVG path (M L C Z, absolute or relative) into polylines of
    (x, y, on_curve) points; on_curve marks points sampled from a curve.
    F closes a path like Z and also fills it (closed == 'fill')."""
    toks = TOKEN.findall(d)
    out, pts, closed = [], None, False
    i, cmd = 0, None
    cx = cy = sx = sy = 0.0

    def num():
        nonlocal i
        i += 1
        return float(toks[i - 1])

    def flush():
        if pts and len(pts) > 1:
            out.append((pts, closed))

    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            if cmd in 'ZzFf':
                if pts:
                    pts.append((sx, sy, pts[0][2]))
                closed = 'fill' if cmd in 'Ff' else True
                flush()
                pts, closed = None, False
                cx, cy = sx, sy
                continue
        rel = cmd.islower()
        if cmd in 'Mm':
            flush()
            x, y = num(), num()
            if rel:
                x, y = cx + x, cy + y
            cx, cy, sx, sy = x, y, x, y
            pts, closed = [(x, y, False)], False
            cmd = 'l' if rel else 'L'
        elif cmd in 'Ll':
            x, y = num(), num()
            if rel:
                x, y = cx + x, cy + y
            pts.append((x, y, False))
            cx, cy = x, y
        elif cmd in 'Cc':
            c = [num() for _ in range(6)]
            if rel:
                c = [c[k] + (cx if k % 2 == 0 else cy) for k in range(6)]
            p0, p1, p2, p3 = (cx, cy), (c[0], c[1]), (c[2], c[3]), (c[4], c[5])
            if len(pts) == 1:
                pts[0] = (pts[0][0], pts[0][1], True)
            for k in range(1, 41):
                t = k / 40
                u = 1 - t
                pts.append((
                    u**3 * p0[0] + 3*u*u*t * p1[0] + 3*u*t*t * p2[0] + t**3 * p3[0],
                    u**3 * p0[1] + 3*u*u*t * p1[1] + 3*u*t*t * p2[1] + t**3 * p3[1],
                    True,
                ))
            cx, cy = p3
        else:
            raise ValueError(f'unsupported path command {cmd!r}')
    flush()
    return out


def kind(ch):
    """'lower', 'upper', 'figure' or 'other', from the Unicode category (so
    a superior ª, which Python calls lowercase, is spaced as a mark)."""
    cat = unicodedata.category(ch) if len(ch) == 1 else ''
    return {'Ll': 'lower', 'Lu': 'upper', 'Nd': 'figure'}.get(cat, 'other')


def overshoot(ch):
    """Push the round parts of a letter or figure past the lines they meet."""
    k = kind(ch)
    if k == 'lower':
        lines = LOWER_LINES
    elif k in ('upper', 'figure'):
        lines = UPPER_LINES
    else:
        return lambda x, y, curved: (x, y)
    reach = 70

    def push(x, y, curved):
        if not curved:
            return x, y
        for line in lines:
            d = abs(y - line)
            if d < reach:
                f = 0.5 + 0.5 * math.cos(math.pi * d / reach)
                # Above the middle of the letter "outward" is up (y down).
                outward = -1 if line < 500 else 1
                y += outward * OVERSHOOT * f
        return x, y
    return push


def resample(pts, step):
    """Points every `step` units along a polyline, with t from 0 to 1."""
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total = sum(seg)
    if total < 1e-6:
        return [(pts[0][0], pts[0][1], 0.0)], 0.0
    n = max(2, int(total / step) + 1)
    res, j, acc = [], 0, 0.0
    for k in range(n):
        d = total * k / (n - 1)
        while j < len(seg) - 1 and acc + seg[j] < d:
            acc += seg[j]
            j += 1
        f = 0 if seg[j] == 0 else (d - acc) / seg[j]
        a, b = pts[j], pts[j + 1]
        res.append((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, d / total))
    return res, total


def prepare(ch, d, step, warp, weight=1.0):
    strokes = []
    push = overshoot(ch)
    for pts, closed in subpaths(d):
        pts = [warp(*push(x, y, c)) for x, y, c in pts]
        res, length = resample(pts, step)
        strokes.append((res, closed, length, weight))
    return strokes


def skeleton_points(d):
    return [(x, y) for pts, _ in subpaths(d) for x, y, _c in pts]


def centre_x(d):
    xs = [x for x, _ in skeleton_points(d)]
    return (min(xs) + max(xs)) / 2


# ---------------------------------------------------------------- pens

def px(x, y):
    return (x - X0) * S, (y - Y0) * S


def fill(draw, pts):
    """Ink inside a closed stroke marked F (a solid dot, square or arrowhead)."""
    draw.polygon([px(x, y) for x, y, _t in pts], fill=255)


def round_pen(draw, strokes, radius, taper=0.0, dot=1.25, flat=0.93):
    """A round pen, slightly flatter than round: horizontal strokes come
    out a few percent lighter than vertical ones, which reads as even."""
    for pts, closed, length, weight in strokes:
        if closed == 'fill':
            fill(draw, pts)
        r0 = radius * weight * (dot if length < 30 else 1.0)
        for x, y, t in pts:
            # Ink is lighter where the pen lands and lifts.
            f = 1.0 if closed else 1 - taper * (1 - math.sin(math.pi * t)) ** 2
            rx = r0 * f * S
            ry = rx * flat
            cx, cy = px(x, y)
            draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)


def stroke_pen(draw, strokes, radius, nib=(1.0, 0.93), cut='kai'):
    """The round pen along Chinese strokes: its radius follows each stroke's
    kind (hanzi.profile), heavier where it lands, lighter where it lifts.
    `nib` is its reach across and down against the radius."""
    for (pts, closed, length, weight), kind in strokes:
        if closed == 'fill':
            fill(draw, pts)
        for x, y, t in pts:
            f = 1.25 if length < 30 else (1.0 if closed else hanzi.profile(kind, t, cut))
            r = radius * weight * f * S
            rx, ry = r * nib[0], r * nib[1]
            cx, cy = px(x, y)
            draw.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), fill=255)


def nib_pen(draw, strokes, half_w, half_t, angle):
    a = math.radians(angle)
    u = (math.cos(a), -math.sin(a))     # along the nib edge
    v = (math.sin(a), math.cos(a))      # across it
    # A rectangle with softened corners: a felt tip, not a steel blade.
    shape = []
    for k in range(24):
        th = 2 * math.pi * k / 24
        c, s = math.cos(th), math.sin(th)
        e = 0.3
        sx = math.copysign(abs(c) ** e, c) * half_w
        sy = math.copysign(abs(s) ** e, s) * half_t
        shape.append((u[0] * sx + v[0] * sy, u[1] * sx + v[1] * sy))
    for pts, closed, _length, weight in strokes:
        if closed == 'fill':
            fill(draw, pts)
        for x, y, _t in pts:
            cx, cy = px(x, y)
            draw.polygon([(cx + dx * S * weight, cy + dy * S * weight) for dx, dy in shape], fill=255)


# ---------------------------------------------------------------- styles

def seed_for(name, ch):
    return sum((i + 1) * ord(c) for i, c in enumerate(name + ch))


def noise(rng, shape, cells):
    small = rng.random((cells, cells)).astype(np.float32)
    img = Image.fromarray((small * 255).astype(np.uint8)).resize(
        (shape[1], shape[0]), Image.BICUBIC)
    a = np.asarray(img, dtype=np.float32) / 255
    return (a - a.mean()) / (a.std() + 1e-6)


class Style:
    """What every pen shares: the glyph's strokes from its skeleton parts,
    and a Bold made by a wider pen on the same skeleton."""
    mono = False
    widen = 1.0

    def __init__(self, bold=False):
        self.bold = bold
        self.weight = 'Bold' if bold else 'Regular'

    def parts(self, ch, variant=0):
        return parts(ch, self.reach, self.mono, self.ring, self.hook, variant)

    def strokes(self, ch, step, warp, variant=0):
        out = []
        for role, d, w in self.parts(ch, variant):
            out += prepare(role, self.ink_dots(d), step, warp, w)
        return out

    def anchors(self, ch, variant=0):
        """GPOS anchors in skeleton units, before the hand's warp:
        (own, stack). A letter has only `stack` (where marks attach to it); a
        combining mark has `own` (its attachment point) and, above, `stack`."""
        if ch in COMBINING_MARKS:
            return mark_anchors(ch, self.reach, self.ring, self.hook, variant == 1)
        return {}, base_anchors(ch, self.reach, self.ring, self.hook)

    def draw(self, ch, img, variant=0):
        if ch in hanzi.C:
            return self.draw_hanzi(ch, img, variant)
        warp, _rng = self.warp(ch, variant)
        self.pen(ImageDraw.Draw(img), self.strokes(ch, 1.0, warp, variant))
        return img

    def draw_hanzi(self, ch, img, variant=0):
        """Chinese in this family's cut (hanzi.CUTS): the family's own pen,
        or its own nib, along the character's strokes. Variant 1 is the
        form mainland China sets in a line (hanzi.ZHS), 2 in a column (hanzi.VZHS);
        for kana, 1 is its form in a column (hanzi.VERT_ALT: ー upright, small kana
        up and to the right)."""
        cut = hanzi.CUTS[self.key]
        form = 3 if (variant == 1 and ch in hanzi.VERT_ALT) else variant
        strokes, warp, rng = hanzi.placed(ch, self.key, cut['em'] / K, K, seed_for(self.seed, ch), form=form)
        pen = cut['pen'][1 if self.bold else 0] * hanzi.density_scale(ch, strokes, self.bold)
        draw = ImageDraw.Draw(img)
        if cut['nib'] is None:
            # A broad nib makes its own thick and thin; dots are its short dabs.
            self.pen(draw, [st for _kind, d in strokes for st in prepare('', self.ink_dots(d), 2.0, warp, pen)])
        else:
            stroke_pen(draw, [(st, kind) for kind, d in strokes for st in prepare('', d, 2.0, warp)],
                       self.radius * pen, cut['nib'], cut['cut'])
        for _ in range(cut['inked']):
            img = self.ink(img, rng)
        return img

    def ink_dots(self, d):
        return d

    def widen_about(self, ch):
        """A bold pen fills the counters, so a Bold letter is drawn a little
        wider about its own centre (the base letter's, for an accented one)."""
        if self.widen == 1.0:
            return lambda x: x
        cx = centre_x(self.parts(ch)[0][1])
        return lambda x: cx + (x - cx) * self.widen


class Huasha(Style):
    family = 'Yisu Huasha'        # 畫沙: 如錐畫沙
    family_zh = ('一粟畫沙', '一粟画沙')
    key = 'huasha'
    seed = 'ballpoint'            # the jitter's seed keeps the pen's first name, so no glyph moves
    alternates = 2
    # Degrees of lean, part of the handwriting as in other script fonts: the
    # font stays a Regular with post.italicAngle 0, but is spaced upright.
    lean = 9
    space = 250
    panose = (3, 0, 0, 0, 0, 0, 0, 0, 0, 0)     # Latin hand written
    speck = 24
    smooth = (3.0, '1.2')       # blur in pixels before tracing, potrace -O

    def __init__(self, bold=False):
        super().__init__(bold)
        # A straight lowercase stem's sidebearing: about a third of n's counter.
        self.radius = 44 if bold else 27
        self.lower_side, self.upper_side = (70, 88) if bold else (64, 80)
        self.widen = 1.08 if bold else 1.0
        self.reach = self.radius * 0.93         # how far ink reaches up and down from the line
        # A ring's radius and a cedilla's size: their eye and curl stay open under a heavier pen.
        self.ring, self.hook = (76, 1.3) if bold else (50, 1.0)

    def warp(self, ch, variant=0):
        rng = random.Random(seed_for(self.seed, base_of(ch) + '#' * variant))
        # Each letter leans, sits and sizes a little differently, kept small
        # enough that no one letter jumps out of a word.
        k = math.tan(math.radians(self.lean + rng.uniform(-1.5, 1.5)))
        dy = rng.uniform(-3, 3)
        sz = rng.uniform(0.99, 1.01)
        ax, ay = rng.uniform(0, 6), rng.uniform(0, 6)
        wide = self.widen_about(ch)

        def warp(x, y):
            x = wide(x)
            x += 8 * math.sin(y * 0.012 + ax)
            y += 3 * math.sin(x * 0.010 + ay)
            y = BASE + (y - BASE) * sz + dy
            return x + (BASE - y) * k, y
        return warp, rng

    def pen(self, draw, strokes):
        round_pen(draw, strokes, radius=self.radius, taper=0.15)


class Louhen(Style):
    family = 'Yisu Louhen'        # 漏痕: 如屋漏痕
    family_zh = ('一粟漏痕', '一粟漏痕')
    key = 'louhen'
    seed = 'marker'
    alternates = 2
    lean = 0
    space = 270
    panose = (3, 0, 0, 0, 0, 0, 0, 0, 0, 0)
    speck = 24
    smooth = (2.5, '1.2')

    def __init__(self, bold=False):
        super().__init__(bold)
        self.half_w, self.half_t = (78, 20) if bold else (56, 13)
        self.lower_side, self.upper_side = (62, 76) if bold else (56, 70)
        self.widen = 1.08 if bold else 1.0
        a = math.radians(35)
        self.reach = self.half_w * math.sin(a) + self.half_t * math.cos(a)
        self.ring, self.hook = (86, 1.15) if bold else (72, 1.0)     # the nib is broad

    def ink_dots(self, d):
        # A chisel dot is a short dab, not a touch.
        return d.replace('l2 8', 'l16 26')

    def strokes(self, ch, step, warp, variant=0):
        out = []
        for role, d, w in self.parts(ch, variant):
            if role == 'mark' and 'l2 8' in d:
                # Two nib-shaped dabs side by side read as a double acute (ű):
                # an accent's dots are finer and pulled square across the nib.
                out += prepare(role, d.replace('l2 8', 'l26 38'), step, warp, w * 0.72)
            else:
                out += prepare(role, self.ink_dots(d), step, warp, w)
        return out

    def warp(self, ch, variant=0):
        rng = random.Random(seed_for(self.seed, base_of(ch) + '#' * variant))
        ax = rng.uniform(0, 6)
        dy = rng.uniform(-3, 3)
        rot = math.radians(rng.uniform(-0.8, 0.8))
        cr, sr = math.cos(rot), math.sin(rot)
        wide = self.widen_about(ch)

        def warp(x, y):
            x = wide(x)
            x += 4 * math.sin(y * 0.01 + ax)
            x, y = x - 300, y - 450
            x, y = x * cr - y * sr, x * sr + y * cr
            return x + 300, y + 450 + dy
        return warp, rng

    def pen(self, draw, strokes):
        nib_pen(draw, strokes, half_w=self.half_w, half_t=self.half_t, angle=35)


SERIF = re.compile(r'M(-?[\d.]+) (-?[\d.]+) L(-?[\d.]+) (-?[\d.]+)')


class Yinni(Style):
    family = 'Yisu Yinni'         # 印泥: 如印印泥
    family_zh = ('一粟印泥', '一粟印泥')
    key = 'yinni'
    seed = 'typewriter'
    mono = True
    alternates = 0
    lean = 0
    advance = 600               # font units, every glyph
    space = 600
    panose = (2, 0, 0, 9, 0, 0, 0, 0, 0, 0)     # Latin text; proportion 9 = monospaced
    # Specks and dry patches smaller than ~20 x 20 font units would only cost
    # outline points: they vanish at any size the font is read at.
    speck = 2200
    smooth = (1.2, '0.8')

    def __init__(self, bold=False):
        super().__init__(bold)
        self.radius = 56 if bold else 36
        self.dot = 1.35 if bold else 1.6
        self.reach = self.radius * 0.93
        self.ring, self.hook = (78, 1.25) if bold else (54, 1.0)

    def serifs(self, d):
        """A heavier slab would close the gaps between m's feet: in Bold
        each serif gives back a little at both ends."""
        if not self.bold:
            return d
        def shorter(m):
            x0, y0, x1, y1 = map(float, m.groups())
            n = math.hypot(x1 - x0, y1 - y0)
            t = min(25, n * 0.3) / n
            return (f'M{x0 + (x1 - x0) * t:.1f} {y0 + (y1 - y0) * t:.1f} '
                    f'L{x1 - (x1 - x0) * t:.1f} {y1 - (y1 - y0) * t:.1f}')
        return SERIF.sub(shorter, d)

    def parts(self, ch, variant=0):
        return [(role, self.serifs(d) if role == 'serif' else d, w)
                for role, d, w in parts(ch, self.reach, True, self.ring, self.hook, variant)]

    def warp(self, ch, variant=0):
        # Keys don't vary: a variant is only ever a combining mark's capital form.
        rng = random.Random(seed_for(self.seed, base_of(ch)))
        ps = self.parts(ch, variant)
        # An accent doesn't change how its letter fills the cell.
        body = [d for role, d, _w in ps if role != 'mark'] or [d for _r, d, _w in ps]
        raw = [p for d in body for p in skeleton_points(d)]
        lo = min(p[0] for p in raw)
        hi = max(p[0] for p in raw)
        mid = (lo + hi) / 2
        # The cell (two for a Wide character), less the pen and a gap.
        room = wide_cells(ch) * self.advance / K - 160 - 2 * (self.radius - 36)
        if ch in KEEP_SHAPE:
            # Symbols keep their proportions: shrink both ways if too wide.
            sq = sy = min(1.0, room / max(hi - lo, 1))
        else:
            # Yinni's letters fill their cell: narrow ones widen, wide ones squeeze.
            sq = min(1.45 if hi - lo > 150 else 1.0, room / max(hi - lo, 1))
            sy = 1.0
        # Each key strikes a little off: a touch high or low, a hair rotated.
        dy = rng.uniform(-10, 10)
        rot = math.radians(rng.uniform(-1.1, 1.1))
        cr, sr = math.cos(rot), math.sin(rot)

        def warp(x, y):
            x = mid + (x - mid) * sq
            y = 460 + (y - 460) * sy
            x, y = x - mid, y - 400
            x, y = x * cr - y * sr, x * sr + y * cr
            return x + mid, y + 400 + dy
        return warp, rng

    def draw(self, ch, img, variant=0):
        if ch in hanzi.C:
            return self.draw_hanzi(ch, img, variant)
        warp, rng = self.warp(ch, variant)
        strokes = []
        for role, d, w in self.parts(ch, variant):
            strokes += prepare(role, d, 2.0, warp, w)
        round_pen(ImageDraw.Draw(img), strokes, radius=self.radius, dot=self.dot)
        return self.ink(img, rng)

    def ink(self, img, rng):
        nrng = np.random.default_rng(rng.randrange(1 << 30))
        shape = (img.height, img.width)
        soft = np.asarray(img.filter(ImageFilter.GaussianBlur(4 * S)), np.float32) / 255
        low = noise(nrng, shape, 10)
        mid = noise(nrng, shape, 36)
        strike = rng.uniform(-0.05, 0.05)       # some keys hit harder
        level = 0.5 + strike + 0.10 * low + 0.05 * mid
        ink = soft > level
        # Where the ribbon is dry, small patches don't take ink.
        dry = noise(nrng, shape, 40)
        ink &= ~((dry > 1.7) & (low > -0.3))
        return Image.fromarray((ink * 255).astype(np.uint8))


STYLES = {'huasha': Huasha, 'louhen': Louhen, 'yinni': Yinni}

# ---------------------------------------------------------------- tracing

TRANSFORM = re.compile(r'translate\(([-\d.]+),([-\d.]+)\)\s*scale\(([-\d.]+),([-\d.]+)\)')
D_ATTR = re.compile(r'\sd="([^"]+)"')


def trace(img, tmp=None, speck=24, smooth=(3.0, '1.2')):
    """Bitmap (white ink on black) -> RecordingPen in font units."""
    # A light blur before the threshold smooths the stamped pen's edge, so
    # potrace fits long curves instead of many short ones.
    soft = np.asarray(img.filter(ImageFilter.GaussianBlur(smooth[0])))
    bw = Image.fromarray(np.where(soft > 127, 0, 255).astype(np.uint8)).convert('1')
    buf = io.BytesIO()
    bw.save(buf, format='PPM')
    proc = subprocess.run(['potrace', '-b', 'svg', '-t', str(speck), '-a', '1.0', '-O', smooth[1], '-o', '-'],
                          input=buf.getvalue(), stdout=subprocess.PIPE, check=True)
    text = proc.stdout.decode('utf-8')
    rec = RecordingPen()
    m = TRANSFORM.search(text)
    if not m:
        return rec
    tx, ty, sx, sy = map(float, m.groups())
    # svg (x, y) = (tx + sx*X, ty + sy*Y); skeleton = svg/S + origin;
    # font = (x * K, (BASE - y) * K)
    pen = TransformPen(rec, (sx / S * K, 0, 0, -sy / S * K,
                             (tx / S + X0) * K, (BASE - Y0 - ty / S) * K))
    for d in D_ATTR.findall(text):
        parse_path(d, pen)
    return rec


def bounds(rec):
    bp = BoundsPen(None)
    rec.replay(bp)
    return bp.bounds


def moved(rec, dx=0, dy=0):
    out = RecordingPen()
    rec.replay(TransformPen(out, (1, 0, 0, 1, dx, dy)))
    return out


def ink_runs(rec, fixed, lo, hi, vertical=False, step=1.0):
    """Lengths of ink along a line: across x at height `fixed`, or (vertical)
    down y at x = `fixed`, between lo and hi."""
    runs, start, t = [], None, lo
    while t <= hi:
        pen = PointInsidePen(None, (fixed, t) if vertical else (t, fixed))
        rec.replay(pen)
        if pen.getResult():
            start = t if start is None else start
        elif start is not None:
            runs.append(t - start)
            start = None
        t += step
    return runs


# The letters whose flat feet stand on the baseline.
FLAT_FEET = 'xzHEILTnmhu'

# The zones a hinting rasteriser aligns, each measured from the ink: flat
# letters give its edge, round ones its overshoot.
ZONES = {
    'baseline': (FLAT_FEET + 'vw', 'oceOCS03', 1),
    'x-height': ('xzvwuyn', 'oces', 3),
    'cap': ('HEFTZ157', 'OCGQS0368', 3),
    'ascender': ('bdhkl', '', 3),
    'descender': ('pq', 'gy', 1),
}


def private_dict(by_char):
    """CFF hinting values: alignment zones (BlueValues, OtherBlues) and the
    standard stems, measured from the drawn glyphs, as the Type 1 spec asks.
    A hand's jitter spreads a zone, so BlueScale shrinks to keep the largest
    zone legal (BlueScale x height < 1); overshoots are then suppressed up to
    a slightly smaller size."""
    def edge(c, i):
        return bounds(by_char[c]['rec'])[i]

    zones = {}
    for name, (flat, rnd, i) in ZONES.items():
        f = sorted(edge(c, i) for c in flat)
        r = sorted(edge(c, i) for c in rnd)
        if i == 1:      # a bottom zone: from the lowest overshoot (one outlier spared) up to the flat edges
            lo = min(f + r[1:2] if r else f)
            hi = max(f)
        else:           # a top zone: from the flat edges up to the highest overshoot
            lo = min(f)
            hi = max(f + r[-2:-1] if r else f)
        zones[name] = [math.floor(lo), math.ceil(hi)]
    # Top zones that touch (cap height and ascenders) are one zone.
    tops = sorted([zones['x-height'], zones['cap'], zones['ascender']])
    merged = [tops[0]]
    for z in tops[1:]:
        if z[0] <= merged[-1][1] + 3:
            merged[-1] = [merged[-1][0], max(merged[-1][1], z[1])]
        else:
            merged.append(z)
    blues = zones['baseline'] + [v for z in merged for v in z]
    tallest = max(b - a for a, b in zip(blues[::2], blues[1::2]))

    def median(xs):
        xs = sorted(xs)
        return round(xs[len(xs) // 2])
    xh = zones['x-height'][0]
    cap = zones['cap'][0]
    base = zones['baseline'][1]
    vw = []
    for c, y in (('l', xh / 2), ('n', xh / 2), ('H', base + (cap - base) * 0.25), ('I', cap / 2), ('h', xh / 2)):
        g = by_char[c]['rec']
        xmin, _, xmax, _ = bounds(g)
        vw += ink_runs(g, y, xmin - 2, xmax + 2)[:1]
    hw = []
    for c, xf in (('H', 0.5), ('E', 0.75), ('z', 0.5), ('Z', 0.5)):
        g = by_char[c]['rec']
        xmin, ymin, xmax, ymax = bounds(g)
        hw += ink_runs(g, xmin + (xmax - xmin) * xf, ymin - 2, ymax + 2, vertical=True)
    std_vw, std_hw = median(vw), median(hw)
    return {
        'BlueValues': blues,
        'OtherBlues': zones['descender'],
        'BlueScale': min(0.039625, round(0.99 / tallest, 6)),
        'BlueShift': 7,
        'BlueFuzz': 0,
        'StdVW': std_vw, 'StdHW': std_hw,
        'StemSnapV': [std_vw], 'StemSnapH': [std_hw],
    }


def without_specks(rec, least=450):
    """Drop contours under `least` square font units (the 400 floor, with
    room for rounding): a counter a heavy pen has all but closed, or a speck
    of ribbon. Neither shows at text sizes, and each costs outline points."""
    out = RecordingPen()
    for c in cells.contours(rec):
        if abs(cells.area(c)) >= least:
            out.value += c
    return out


class ExtremaPen(BasePen):
    """Splits each cubic at its horizontal and vertical extremes, so every
    curve spans at most a quarter turn and has points where rasterisers and
    hinting expect them."""

    def __init__(self, out):
        super().__init__(None)
        self.out = out

    def _moveTo(self, p):
        self.out.moveTo(p)

    def _lineTo(self, p):
        self.out.lineTo(p)

    def _curveToOne(self, p1, p2, p3):
        p0 = self._getCurrentPoint()
        ts = set()
        for i in (0, 1):
            a = -p0[i] + 3 * p1[i] - 3 * p2[i] + p3[i]
            b = 2 * (p0[i] - 2 * p1[i] + p2[i])
            c = p1[i] - p0[i]
            if abs(a) < 1e-9:
                if abs(b) > 1e-9:
                    ts.add(-c / b)
                continue
            disc = b * b - 4 * a * c
            if disc >= 0:
                r = math.sqrt(disc)
                ts.update(((-b + r) / (2 * a), (-b - r) / (2 * a)))
        ts = sorted(t for t in ts if 0.02 < t < 0.98)
        for seg in (splitCubicAtT(p0, p1, p2, p3, *ts) if ts else [(p0, p1, p2, p3)]):
            self.out.curveTo(seg[1], seg[2], seg[3])

    def _closePath(self):
        self.out.closePath()

    def _endPath(self):
        self.out.endPath()


# ---------------------------------------------------------------- spacing

ROWS = np.arange(-360, 1000, 8)     # font-unit rows the profiles sample, accents included


def profile(img, slant):
    """Leftmost and rightmost ink on each row, in font units, measured with
    the lean taken out (as type designers space an italic)."""
    a = np.asarray(img) > 127
    left = np.full(ROWS.shape, np.nan)
    right = np.full(ROWS.shape, np.nan)
    mid_y = (BASE - 250) * K / 2
    for i, y in enumerate(ROWS):
        r = int(round((BASE - y / K - Y0) * S))
        if 0 <= r < a.shape[0]:
            cols = np.flatnonzero(a[r])
            if cols.size:
                shift = slant * (y - mid_y)
                left[i] = (cols[0] / S + X0) * K - shift
                right[i] = (cols[-1] / S + X0) * K - shift
    return left, right


def zone_for(ch, left, x_height, cap_height):
    """The rows a letter is spaced over: x-height for lowercase, cap height
    for capitals and figures, a mark's own height for marks."""
    k = kind(ch)
    if k == 'lower':
        return (ROWS >= 0) & (ROWS <= x_height)
    if k in ('upper', 'figure'):
        return (ROWS >= 0) & (ROWS <= cap_height)
    ink = ~np.isnan(left)
    return ink if ink.any() else (ROWS >= 0) & (ROWS <= x_height)


def side_white(edge, zone, depth, sign):
    """How far, on average, the ink sits in from the letter's outermost
    point over its zone, each row counted at most `depth` deep."""
    ink = edge[zone]
    extreme = np.nanmin(ink) if sign < 0 else np.nanmax(ink)
    d = (ink - extreme) * -sign
    d = np.where(np.isnan(d), depth, np.minimum(d, depth))
    return float(d.mean()), float(extreme)


# ---------------------------------------------------------------- font

def glyph_name(ch):
    cp = ord(ch)
    return UV2AGL.get(cp, f'uni{cp:04X}')


def suffix(ch, variant):
    if not variant:
        return ''
    if ch in hanzi.ZHS:
        return ('.zhs', '.zhs.vert')[variant - 1]
    if ch in hanzi.VERT_ALT:
        return '.vert'
    return '.case' if ch in COMBINING_MARKS else f'.alt{variant}'


def notdef(width):
    pen = T2CharStringPen(width, None)
    for (x0, y0, x1, y1), outer in (((60, 0, width - 60, 600), True), ((110, 50, width - 110, 550), False)):
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        if not outer:
            pts.reverse()
        pen.moveTo(pts[0])
        for p in pts[1:]:
            pen.lineTo(p)
        pen.closePath()
    return pen.getCharString()


KERNED_MARKS = '.,:;\'"‘’“”-–—()?!/&«»‹›‚„¿¡'
TOUCH = 12      # font units: the least white two kerned shapes keep between them, on any row


def kerning(glyphs, strength=0.55, floor=80):
    """Pair adjustments where two shapes leave a hole or can tuck together:
    on the rows where both letters have ink inside both spacing zones (so an
    ascender beside a short letter doesn't count), the closest the two come is
    compared with the gap their spacing sidebearings give (two straight
    stems meet at exactly that; tails and hooks outside the spacing zone,
    like j's, don't count). A hole wider than that (T o, L T, P ., r ., " A)
    is closed by half its excess; pairs that already meet are left alone.

    Then, over every row both shapes ink (accents, tails, hooks), no pair may
    come closer than TOUCH: an accent tucked under a T is kerned less, and an
    f's hook that would hit a quote or an accent is pushed apart."""
    kernable = [c for c in glyphs if c.isalnum() or c in KERNED_MARKS]
    pairs = {}
    for a in kernable:
        ga = glyphs[a]
        ra = ga['adv'] - ga['right']                # white right of a, per row
        for b in kernable:
            gb = glyphs[b]
            lb = gb['left']                         # white left of b, per row
            inked = ~np.isnan(ra) & ~np.isnan(lb)
            both = inked & ga['zone'] & gb['zone']
            k = 0
            if both.sum() >= 3:
                closest = float((ra + lb)[both].min())
                usual = ga['zsbR'] + gb['zsbL']
                excess = closest - usual
                # Over a short shared band (a period beside an o) every round
                # shape looks like a hole; ask for a deeper one before kerning.
                short = both.sum() * 8 < 0.33 * 430
                if excess >= (floor * 1.75 if short else floor):
                    k = -int(round(excess * strength / 5) * 5)
                    # Between two lowercase letters a hole is never as deep as under
                    # a T or after an r before a period, so keep those pairs gentle.
                    lower = kind(a) == 'lower' and kind(b) == 'lower'
                    k = max(-40 if lower else -160, k)
            if inked.any():
                nearest = float((ra + lb)[inked].min()) + k
                if nearest < TOUCH:
                    k += int(math.ceil((TOUCH - nearest) / 5) * 5)
            if k:
                pairs[(a, b)] = k
    return pairs


def anchor(p):
    return f'<anchor {p[0]} {p[1]}>'


def mark_features(glyphs, anchors):
    """GDEF classes, and ccmp, mark and mkmk for the combining marks: an i
    or j drops its dot under a mark above, a mark above a capital takes its
    flatter .case form, and marks stack."""
    marks = [n for n, g in glyphs.items() if g['ch'] in COMBINING_MARKS]
    top = [n for n in marks if ANCHOR[COMBINING_MARKS[glyphs[n]['ch']]] == 'top' and not n.endswith('.case')]
    below = [n for n in marks if ANCHOR[COMBINING_MARKS[glyphs[n]['ch']]] != 'top']
    caps = [n for n, g in glyphs.items() if kind(g['ch']) == 'upper']
    bases = [n for n in glyphs if n not in marks]
    fea = [f'@top_marks = [{" ".join(top)}];',
           f'@top_case = [{" ".join(n + ".case" for n in top)}];',
           f'@below_marks = [{" ".join(below)}];',
           f'@caps = [{" ".join(caps)}];',
           f'lookup dotless {{ sub i by {glyph_name("ı")}; sub j by {glyph_name("ȷ")}; }} dotless;',
           f'lookup unmake {{ sub {glyph_name("į")} by i {glyph_name(chr(0x328))}; }} unmake;',
           'lookup case_marks { sub @top_marks by @top_case; } case_marks;',
           'feature ccmp {',
           # į under a mark above: back to i and an ogonek, so the i can drop its dot.
           f"  lookup ccmp_unmake {{ sub {glyph_name('į')}' lookup unmake @top_marks;"
           f" sub {glyph_name('į')}' lookup unmake @below_marks @top_marks; }} ccmp_unmake;",
           "  lookup ccmp_dotless {",
           "    sub [i j]' lookup dotless @top_marks;",
           "    sub [i j]' lookup dotless @below_marks @top_marks;",
           "    sub [i j]' lookup dotless @below_marks @below_marks @top_marks;",
           "  } ccmp_dotless;",
           "  lookup ccmp_case {",
           "    sub @caps @top_marks' lookup case_marks;",
           "    sub @caps @below_marks @top_marks' lookup case_marks;",
           "    sub @caps @top_case @top_marks' lookup case_marks;",
           "    sub @caps @top_case @top_case @top_marks' lookup case_marks;",
           "  } ccmp_case;",
           '} ccmp;']
    for n in marks:
        (cls, p), = anchors[n][0].items()
        fea.append(f'markClass {n} {anchor(p)} @{cls};')
    fea.append('feature mark {')
    for n in bases:
        if n in anchors:
            fea.append(f'  pos base {n} ' + ' '.join(f'{anchor(p)} mark @{c}' for c, p in sorted(anchors[n][1].items())) + ';')
    fea += ['} mark;', 'feature mkmk {']
    for n in marks:
        for c, p in anchors[n][1].items():
            if c == 'top':
                fea.append(f'  pos mark {n} {anchor(p)} mark @{c};')
    # A comma below hangs under the mark below before it, whatever marks
    # above come between them.
    fea += ['  lookup mkmk_below {', '    lookupflag UseMarkFilteringSet @below_marks;']
    for n in below:
        for c, p in anchors[n][1].items():
            if c == 'bottom':
                fea.append(f'    pos mark {n} {anchor(p)} mark @{c};')
    fea += ['  } mkmk_below;', '} mkmk;',
            f'table GDEF {{ GlyphClassDef [{" ".join(bases)}], , [{" ".join(marks)}], ; }} GDEF;']
    return fea


# Full-width marks by where their ink sits in the em box. An opening mark's
# left half is blank, a closing mark's right half; Taiwan centres the rest.
# Mainland China sets those in the left half (the .zhs forms), so there they
# count as right-blank too.
CJK_OPEN = '「『（《〈'
CJK_CLOSE = '」』）》〉'
CJK_CENTRED = '。、，；：？！'


def cjk_spacing(style, glyphs):
    """chws and halt. chws (JLREQ, CLREQ): where two marks meet, one blank
    half goes. halt: every mark half-width, on request. The blank side is
    the side the ink isn't on. In Yinni half a mark is one cell, so
    chws keeps the grid; the proportional families also take a quarter off a
    centred mark's side that faces a bracket, as Taiwan sets them."""
    have = lambda chars: [glyph_name(c) for c in chars if glyph_name(c) in glyphs]
    opening, closing, centred = have(CJK_OPEN), have(CJK_CLOSE), have(CJK_CENTRED)
    if not (opening and closing):
        return []
    half = glyphs[glyph_name('中')]['adv'] // 2
    quarter = half // 2
    left = [n + '.zhs' for n in centred if n + '.zhs' in glyphs]
    fea = [f'@CJK_OPEN = [{" ".join(opening)}];', f'@CJK_CLOSE = [{" ".join(closing)}];',
           f'@CJK_RIGHT_BLANK = [{" ".join(closing + left)}];', f'@CJK_CENTRED = [{" ".join(centred)}];',
           'feature chws {',
           f"  pos @CJK_RIGHT_BLANK' <0 0 -{half} 0> [@CJK_RIGHT_BLANK @CJK_OPEN];",
           f"  pos @CJK_OPEN' <0 0 -{half} 0> @CJK_OPEN;"]
    if not style.mono:
        fea += [f"  pos @CJK_CENTRED' <0 0 -{quarter} 0> @CJK_OPEN;",
                f"  pos @CJK_CLOSE' <0 0 -{quarter} 0> @CJK_CENTRED;"]
    fea += ['} chws;', 'feature halt {',
            f'  pos @CJK_OPEN <-{half} 0 -{half} 0>;',
            f'  pos @CJK_RIGHT_BLANK <0 0 -{half} 0>;',
            f'  pos @CJK_CENTRED <-{quarter} 0 -{half} 0>;',
            '} halt;']
    # The same along a column (vchw, vhal), on the vertical forms: there an
    # opening bracket's top half is blank, a closing one's bottom half, and the
    # mainland's 。，、：； (in the upper right) leave the bottom half. ？！ are as
    # tall as a character in a column and have nothing to give.
    turned = {glyph_name(h): glyph_name(v) for h, v in hanzi.VERTICAL.items()}
    v_open = [turned[n] for n in opening if turned[n] in glyphs]
    v_close = [turned[n] for n in closing if turned[n] in glyphs]
    if not (v_open and v_close):
        return fea
    short = have('。、，；：')
    v_low = [n + '.zhs.vert' for n in short if n + '.zhs.vert' in glyphs]
    fea += [f'@CJK_V_OPEN = [{" ".join(v_open)}];', f'@CJK_V_CLOSE = [{" ".join(v_close)}];',
            f'@CJK_V_BOTTOM_BLANK = [{" ".join(v_close + v_low)}];', f'@CJK_V_CENTRED = [{" ".join(short)}];',
            'feature vchw {',
            f"  pos @CJK_V_BOTTOM_BLANK' <0 0 0 -{half}> [@CJK_V_BOTTOM_BLANK @CJK_V_OPEN];",
            f"  pos @CJK_V_OPEN' <0 0 0 -{half}> @CJK_V_OPEN;"]
    if not style.mono:
        fea += [f"  pos @CJK_V_CENTRED' <0 0 0 -{quarter}> @CJK_V_OPEN;",
                f"  pos @CJK_V_CLOSE' <0 0 0 -{quarter}> @CJK_V_CENTRED;"]
    fea += ['} vchw;', 'feature vhal {',
            f'  pos @CJK_V_OPEN <0 {half} 0 -{half}>;',
            f'  pos @CJK_V_BOTTOM_BLANK <0 0 0 -{half}>;',
            f'  pos @CJK_V_CENTRED <0 {quarter} 0 -{half}>;',
            '} vhal;']
    return fea


def features(style, glyphs, pairs, anchors):
    """ccmp and mark positioning, calt alternates and kern, as feature-file
    text. An accented letter kerns in its base letter's class; where its
    accent changes the answer (an accent under a T's bar), a glyph pair says
    so first. Alternates and kerning look through combining marks."""
    fea = ['languagesystem DFLT dflt;', 'languagesystem latn dflt;',
           'languagesystem hani dflt;', 'languagesystem hani ZHS;']
    fea += mark_features(glyphs, anchors)
    zhs = sorted(n for n in glyphs if n.endswith('.zhs'))
    if zhs:
        # Simplified Chinese text sets its punctuation as mainland China does.
        fea += ['feature locl {', '  script hani;', '  language ZHS exclude_dflt;']
        fea += [f'  sub {n[:-4]} by {n};' for n in zhs]
        fea += ['} locl;']
    # In a column: brackets turned, and the mainland's marks moved (after locl).
    vert = [(glyph_name(h), glyph_name(v)) for h, v in hanzi.VERTICAL.items() if glyph_name(v) in glyphs]
    vert += sorted((n[:-5], n) for n in glyphs if n.endswith('.zhs.vert'))
    vert += sorted((n[:-5], n) for n in glyphs if n.endswith('.vert') and not n.endswith('.zhs.vert'))
    if vert:
        fea += ['feature vert {'] + [f'  sub {a} by {b};' for a, b in vert] + ['} vert;']
    fea += cjk_spacing(style, glyphs)
    if style.alternates:
        lower = [g['ch'] for g in glyphs.values() if g['variant'] == 0 and kind(g['ch']) == 'lower'
                 and f'{glyph_name(g["ch"])}.alt1' in glyphs]
        lower = [glyph_name(c) for c in sorted(lower, key=ord)]
        fea += [f'@cycle0 = [{" ".join(lower)}];']
        for v in range(1, style.alternates + 1):
            fea += [f'@cycle{v} = [{" ".join(n + f".alt{v}" for n in lower)}];',
                    f'lookup to_alt{v} {{ sub @cycle0 by @cycle{v}; }} to_alt{v};']
        # Each lowercase letter after another takes the next drawing in turn:
        # "book" is written o, o.alt1 -- never the same o twice in a row.
        rules = ['  lookupflag IgnoreMarks;']
        rules += [f"  sub @cycle{v} @cycle0' lookup to_alt{v + 1};" for v in range(style.alternates - 1, 0, -1)]
        rules.append("  sub @cycle0 @cycle0' lookup to_alt1;")
        fea += ['feature calt {'] + rules + ['} calt;']
    if style.mono and 'hyphen.arrow_r' in glyphs:
        # Programming ligatures, off unless asked for (`dlig`): -> <- => != <= >=, each
        # still two cells wide, so a terminal's cursor stays in step. A pair inside a
        # longer run of these marks (-->, ===, !==, <=>) stays as typed.
        fea += ['@lig_op = [hyphen greater less equal exclam];', 'feature dlig {']
        for a, b, first, second in (('hyphen', 'greater', 'hyphen.arrow_r', 'greater.arrow_r'),
                                    ('less', 'hyphen', 'less.arrow_l', 'hyphen.arrow_l'),
                                    ('equal', 'greater', 'equal.fat_r', 'greater.fat_r'),
                                    ('exclam', 'equal', 'exclam.neq', 'equal.neq'),
                                    ('less', 'equal', 'less.lte', 'equal.lte'),
                                    ('greater', 'equal', 'greater.gte', 'equal.gte')):
            fea += [f"  ignore sub @lig_op {a}' {b};", f"  ignore sub {a}' {b} @lig_op;",
                    f"  sub {a}' {b} by {first};", f"  sub {first} {b}' by {second};"]
        fea.append('} dlig;')
    if pairs:
        variants = {}
        for name, g in glyphs.items():
            variants.setdefault(g['ch'], []).append(name)
        cls = {c: list(v) for c, v in variants.items() if c not in ACCENTED}
        for c in variants:
            if c in ACCENTED and ACCENTED[c][0] in cls:
                cls[ACCENTED[c][0]] += variants[c]
        group = lambda c: ACCENTED[c][0] if c in ACCENTED else c
        chars = sorted({c for ab in pairs for c in ab} | {c for c in variants if c in ACCENTED}, key=ord)
        lines, exceptions = [], []
        for (a, b), k in sorted(pairs.items()):
            if a not in ACCENTED and b not in ACCENTED:
                lines.append(f'  pos [{" ".join(cls[a])}] [{" ".join(cls[b])}] {k};')
        # Accented letters: wherever their own value differs from their class's.
        kernable = [c for c in chars if c in variants]
        for a in kernable:
            for b in kernable:
                if a not in ACCENTED and b not in ACCENTED:
                    continue
                own = pairs.get((a, b), 0)
                if own != pairs.get((group(a), group(b)), 0):
                    for na in variants[a]:
                        for nb in variants[b]:
                            exceptions.append(f'  pos {na} {nb} {own};')
        fea += ['feature kern {', '  lookupflag IgnoreMarks;'] + exceptions + lines + ['} kern;']
    return '\n'.join(fea)


def canvas(style, ch):
    """The empty bitmap a character is drawn on. The pens' jitter depends on
    its size, so anything that checks a drawing (tools/edges.py) uses this too."""
    # A Wide character's canvas runs a cell further right.
    wide = (wide_cells(ch) - 1) * style.advance / K if style.mono else 0
    if ch in hanzi.C:
        wide = max(wide, hanzi.CUTS[style.key]['em'] / K + 100 - (X0 + W))
    return Image.new('L', (int((W + wide) * S), int(H * S)), 0)


_CODE_MARK = None


def code_mark():
    """One hash of the drawing code and of potrace's version."""
    global _CODE_MARK
    if _CODE_MARK is None:
        h = hashlib.sha256()
        for name in CODE:
            h.update(name.encode() + b'\0' + (HERE / name).read_bytes())
        h.update(subprocess.run(['potrace', '--version'], stdout=subprocess.PIPE).stdout)
        _CODE_MARK = h.hexdigest()
    return _CODE_MARK


def glyph_cache_key(style, ch, v, smooth):
    """What one glyph's outline depends on: the code, the font, and the glyph's own strokes."""
    if ch in hanzi.C:
        form = 3 if (v == 1 and ch in hanzi.VERT_ALT) else v
        spec = repr((hanzi.C, hanzi.ZHS, hanzi.VZHS, hanzi.VERT_ALT)[form][ch])
    else:
        spec = repr(style.parts(ch, v))
    h = hashlib.sha256()
    h.update(f'{code_mark()}|{style.key}|{style.bold}|{style.speck}|{smooth}|{ch}|{v}|{spec}'.encode('utf-8'))
    return h.digest()[:16]


_WORKER_STYLE = None
_WORKER_SLANT = 0.0


def _init_worker(key, bold):
    global _WORKER_STYLE, _WORKER_SLANT
    _WORKER_STYLE = STYLES[key](bold=bold)
    _WORKER_SLANT = math.tan(math.radians(_WORKER_STYLE.lean))


def _render_glyph(job):
    ch, v, smooth = job
    style = _WORKER_STYLE
    img = canvas(style, ch)
    img = style.draw(ch, img, v)
    edge = np.asarray(img)
    cut_off = bool(edge[:2].any() or edge[-2:].any() or edge[:, :2].any() or edge[:, -2:].any())
    rec = without_specks(trace(img, None, style.speck, smooth))
    if bounds(rec) is None:
        return ch, v, cut_off, None, None, None
    left, right = profile(img, _WORKER_SLANT)
    return ch, v, cut_off, list(rec.value), left, right


def make(style, shared=None, use_cache=None):
    """One font of a family. `shared` carries the Regular's vertical metrics,
    so both weights set lines alike."""
    family = style.family
    ps = family.replace(' ', '') + '-' + style.weight
    slant = math.tan(math.radians(style.lean))
    if use_cache is None:
        use_cache = not os.environ.get('YISU_NO_CACHE')

    cache_path = CACHE_DIR / f'{ps}.pkl'
    cache = {}
    if use_cache and cache_path.exists():
        try:
            cache = pickle.loads(cache_path.read_bytes())
        except Exception:
            cache = {}
    cache_dirty = False
    cache_hits = 0

    glyphs = {}          # name -> dict(rec, adv, left, right, ...)
    by_char = {}         # char -> its default glyph's entry
    pending = []         # (name, ckey, ch, v, smooth)
    for ch in charset(style.mono) + list(hanzi.C):
        variants = style.alternates if kind(ch) == 'lower' else 0
        if ch in COMBINING_MARKS and ANCHOR[COMBINING_MARKS[ch]] == 'top':
            variants = 1        # the capital form, `.case`
        if ch in hanzi.ZHS:
            # as mainland China sets it in a line, `.zhs`, and in a column, `.zhs.vert`
            variants = 2 if ch in hanzi.VZHS else 1
        elif ch in hanzi.VERT_ALT:
            variants = 1        # its form in a column, `.vert`
        smooth = style.smooth
        for v in range(variants + 1):
            name = glyph_name(ch) + suffix(ch, v)
            ckey = glyph_cache_key(style, ch, v, smooth) if use_cache else None
            hit = cache.get(name) if ckey is not None else None
            if hit is not None and hit[0] == ckey:
                rec = RecordingPen()
                rec.value = list(hit[1])
                left, right = hit[2], hit[3]
                cache_hits += 1
                glyphs[name] = {'ch': ch, 'rec': rec, 'left': left, 'right': right, 'variant': v}
                if v == 0:
                    by_char[ch] = glyphs[name]
            else:
                pending.append((name, ckey, ch, v, smooth))

    if pending:
        workers = min(12, os.cpu_count() or 4)
        jobs = [(ch, v, smooth) for _name, _ckey, ch, v, smooth in pending]
        if workers > 1 and len(jobs) >= 32:
            with ProcessPoolExecutor(workers, initializer=_init_worker, initargs=(style.key, style.bold)) as pool:
                results = list(pool.map(_render_glyph, jobs, chunksize=16))
        else:
            _init_worker(style.key, style.bold)
            results = [_render_glyph(j) for j in jobs]
        for (name, ckey, ch, v, _smooth), (_ch, _v, cut_off, rec_val, left, right) in zip(pending, results):
            if cut_off:
                print(f'  {ch!r}: ink reaches the edge of the canvas, and is cut off')
            if rec_val is None:
                print(f'  {ch!r}: empty, skipped')
                continue
            rec = RecordingPen()
            rec.value = rec_val
            if ckey is not None:
                cache[name] = (ckey, rec_val, left, right)
                cache_dirty = True
            glyphs[name] = {'ch': ch, 'rec': rec, 'left': left, 'right': right, 'variant': v}
            if v == 0:
                by_char[ch] = glyphs[name]

    if use_cache and cache_dirty:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        part = cache_path.with_suffix(f'.{os.getpid()}.part')     # two builds at once never leave half a file
        part.write_bytes(pickle.dumps(cache, protocol=pickle.HIGHEST_PROTOCOL))
        part.replace(cache_path)
    if use_cache and cache_hits:
        print(f'  {ps}: {cache_hits}/{len(glyphs)} glyphs from cache')

    # The skeleton's baseline is the pen's centre line, so half of every flat
    # stroke hangs below it. Lift the whole font by what its pen reaches below
    # (the median foot of the flat letters, so one key struck low or a
    # tapered stroke doesn't decide it): flat feet then stand on y=0, round
    # ones overshoot below it, and the x-height and cap height are the ink's.
    # Spacing and kerning are measured on the bitmaps, before the lift, so
    # neither changes; GPOS anchors and the outlines take it.
    feet = sorted(bounds(by_char[c]['rec'])[1] for c in FLAT_FEET)
    lift = -round(feet[len(feet) // 2])
    for g in glyphs.values():
        g['rec'] = moved(g['rec'], 0, lift)
    # On the skeleton's line a heavy pen's underscore would touch the feet of
    # the letters above it, so it hangs a fixed gap under the baseline
    # instead. Only its height moves: its spacing comes from the bitmap.
    u = glyphs['underscore']
    u['rec'] = moved(u['rec'], 0, UNDERSCORE_TOP - round(bounds(u['rec'])[3]))

    # Measure the flat tops of x and H for the x-height and cap height.
    def top(ch):
        return bounds(by_char[ch]['rec'])[3]
    x_height = round(top('x') if not slant else top('z'))
    cap_height = round(top('H'))
    if shared is None:
        typo_asc = round((LINE + cap_height) / 2)
        shared = {'asc': typo_asc, 'desc': typo_asc - LINE}
    TYPO_ASC, TYPO_DESC = shared['asc'], shared['desc']

    def base_glyph(g):
        name = glyph_name(ACCENTED[g['ch']][0]) + (f'.alt{g["variant"]}' if g['variant'] else '')
        return glyphs[name]

    if style.mono:
        for g in glyphs.values():
            xmin, _, xmax, _ = bounds(g['rec'])
            g['adv'] = style.advance * wide_cells(g['ch'])
            # Chinese is placed by its grid, not its ink: 「 hugs the text after it.
            g['dx'] = 0 if g['ch'] in hanzi.C else (g['adv'] - (xmax - xmin)) / 2 - xmin
            if g['ch'] in hanzi.TONES:
                # Zhuyin's tone marks are East Asian Width A: one cell, the grid's middle half.
                g['dx'] = (g['adv'] - hanzi.CUTS[style.key]['em']) // 2
    else:
        # The profiles' rows are the bitmap's, from before the lift, and so
        # are the heights spacing reads, which keeps every advance as it was.
        xh, caps = x_height - lift, cap_height - lift
        depth = 0.15 * xh
        for g in glyphs.values():
            ch = g['ch']
            if ch in hanzi.C:
                # Chinese is set on its em, placed by its grid, not its ink.
                g['adv'], g['dx'] = hanzi.CUTS[style.key]['em'], 0
                if ch in hanzi.TONES:
                    # Zhuyin's tone marks take the middle half of the em.
                    g['adv'], g['dx'] = g['adv'] // 2, -(g['adv'] // 4)
                continue
            zone = zone_for(ch, g['left'], xh, caps)
            target = style.lower_side if kind(ch) in ('lower', 'other') else style.upper_side
            wl, xl = side_white(g['left'], zone, depth, -1)
            wr, xr = side_white(g['right'], zone, depth, +1)
            # Straight sides keep the full space; round and open ones give
            # back what their own shape already leaves.
            sbl, sbr = target - wl * 0.6, target - wr * 0.6
            if ch in '\'"‘’“”':
                sbl, sbr = max(sbl, 25), max(sbr, 25)
            g['dx'] = sbl - xl
            g['adv'] = round(xr - xl + sbl + sbr)
            g['zsbL'], g['zsbR'], g['zone'] = sbl, sbr, zone
        # Math signs share one width, centred, so sums line up.
        math_signs = [g for g in glyphs.values() if g['ch'] in '+=<>×~-¬±÷−≠≤≥≈']
        cell = max(g['adv'] for g in math_signs if g['ch'] != '-')
        for g in math_signs:
            if g['ch'] == '-':
                continue
            xmin, _, xmax, _ = bounds(g['rec'])
            g['dx'] = (cell - (xmax - xmin)) / 2 - xmin
            g['adv'] = cell
    # An accented letter is its base letter plus a mark: same place, same width.
    for g in glyphs.values():
        if g['ch'] in ACCENTED:
            b = base_glyph(g)
            for k in ('dx', 'adv', 'zsbL', 'zsbR', 'zone'):
                if k in b:
                    g[k] = b[k]
            # An apostrophe caron (ď ľ ť) stands beside the ascender: the
            # letter grows by what it adds on the right.
            if not style.mono and ACCENTED[g['ch']][1] == 'caronvert':
                g['adv'] += max(0, round(np.nanmax(g['right']) - np.nanmax(b['right'])))
    # A combining mark has no width: it hangs left of where the pen stands,
    # over the middle of the letter before it, for apps that don't position it.
    over = style.advance / 2 if style.mono else by_char['n']['adv'] / 2
    for g in glyphs.values():
        if g['ch'] in COMBINING_MARKS:
            xmin, _, xmax, _ = bounds(g['rec'])
            g['adv'], g['dx'] = 0, -over - (xmin + xmax) / 2
    for g in glyphs.values():
        g['left'] = g['left'] + g['dx']
        g['right'] = g['right'] + g['dx']

    # Where marks attach, through the same hand that drew the glyph.
    anchors = {}
    for name, g in glyphs.items():
        ch, v = g['ch'], g['variant']
        if ch in hanzi.C or not (ch in COMBINING_MARKS or ch == '◌' or unicodedata.category(ch).startswith('L')):
            continue
        warp, _rng = style.warp(ch, v)
        def font_pt(p, g=g, warp=warp):
            x, y = warp(*p)
            return round(x * K + g['dx']), round((BASE - y) * K) + lift
        own, stack = style.anchors(ch, v)
        anchors[name] = ({c: font_pt(p) for c, p in own.items()}, {c: font_pt(p) for c, p in stack.items()})

    # Box drawing, blocks and the programming ligatures, made to the cell (Yinni only).
    if style.mono:
        light = round(2 * style.radius * K / 2) * 2
        nan = np.full(ROWS.shape, np.nan)
        for ch, rec in cells.glyphs(style.advance, TYPO_ASC, TYPO_DESC, light).items():
            glyphs[glyph_name(ch)] = {'ch': ch, 'rec': rec, 'left': nan, 'right': nan, 'variant': 0,
                                      'adv': style.advance, 'dx': 0, 'cell': True}
        y_mid = round((BASE - 460) * K) + lift
        for name, (ch, rec) in cells.ligatures(style.advance, y_mid, light).items():
            glyphs[name] = {'ch': ch, 'rec': rec, 'left': nan, 'right': nan, 'variant': 1,
                            'adv': style.advance, 'dx': 0, 'cell': True}

    pairs = {}
    if not style.mono:
        chars = {g['ch']: g for g in glyphs.values() if g['variant'] == 0 and g['ch'] not in hanzi.C}
        pairs = kerning(chars)

    # ---- outlines
    order = ['.notdef', 'space', 'uni00A0'] + sorted(glyphs, key=lambda n: (ord(glyphs[n]['ch']), glyphs[n]['variant']))
    charstrings, metrics, cmap = {}, {}, {32: 'space', 160: 'uni00A0'}
    nd = style.advance if style.mono else 500    # monospace: every glyph one width
    charstrings['.notdef'] = notdef(nd)
    metrics['.notdef'] = (nd, 60)
    for sp in ('space', 'uni00A0'):
        charstrings[sp] = T2CharStringPen(style.space, None).getCharString()
        metrics[sp] = (style.space, 0)
    y_min, y_max = 0, 0
    tops = {'.notdef': 600}
    for name, g in glyphs.items():
        pen = T2CharStringPen(g['adv'], None)
        placed = moved(g['rec'], g['dx'])
        # Cell glyphs are straight lines and exact quarter arcs already.
        placed.replay(RoundingPen(pen) if g.get('cell') else ExtremaPen(RoundingPen(pen)))
        charstrings[name] = pen.getCharString()
        b = bounds(placed)
        metrics[name] = (g['adv'], math.floor(b[0]))
        tops[name] = b[3]
        y_min, y_max = min(y_min, b[1]), max(y_max, b[3])
        if g['variant'] == 0:
            cmap[ord(g['ch'])] = name

    bold = style.bold
    fb = FontBuilder(1000, isTTF=False)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap(cmap)
    fb.setupCFF(ps, {'FullName': f'{family} {style.weight}', 'FamilyName': family, 'Weight': style.weight},
                charstrings, private_dict(by_char))
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(
        ascent=TYPO_ASC, descent=TYPO_DESC, lineGap=0, caretSlopeRise=1, caretSlopeRun=0)
    # In a column every glyph is one em tall, and the em is Chinese's: its top
    # (VORG) is the top of the frame hanzi are drawn in, whose middle is the
    # grid's y 500 (skeleton y 400), so hanzi sit in a column as in a line.
    em = hanzi.CUTS[style.key]['em']
    origin = round((BASE - 400) * K + lift + em / 2)
    fb.setupVerticalHeader(ascent=em // 2, descent=-(em // 2), lineGap=0, caretSlopeRise=0, caretSlopeRun=1)
    fb.setupVerticalMetrics({n: (em, round(origin - tops[n]) if n in tops else 0) for n in order})
    fb.setupVerticalOrigins({}, origin)
    # Regular and Bold are a style-linked pair (RIBBI): one family name,
    # the weight in the subfamily name, so apps pair them for Cmd-B.
    fb.setupNameTable({
        'familyName': family,
        'styleName': style.weight,
        'uniqueFontIdentifier': f'{VERSION:.3f};{ps}',
        'fullName': f'{family} {style.weight}',
        'psName': ps,
        'version': f'Version {VERSION:.3f}',
        'copyright': 'Copyright 2026 The Yisu Fonts Project Authors (https://github.com/zjlgdx/yisu-fonts)',
        'vendorURL': 'https://github.com/zjlgdx/yisu-fonts',
        'licenseDescription': 'This Font Software is licensed under the SIL Open Font License, Version 1.1.',
        'licenseInfoURL': 'https://openfontlicense.org',
    }, mac=False)
    # The family's Chinese name, Traditional for Taiwan, Hong Kong and Macao,
    # Simplified for the mainland and Singapore (Windows language IDs), so a
    # font menu in Chinese lists 一粟印泥 and any other lists Yisu Yinni.
    hant, hans = style.family_zh
    for lang, zh in ((0x0404, hant), (0x0C04, hant), (0x1404, hant), (0x0804, hans), (0x1004, hans)):
        fb.font['name'].setName(zh, 1, 3, 1, lang)
        fb.font['name'].setName(f'{zh} {style.weight}', 4, 3, 1, lang)
    # The underline is the Regular's underscore in both weights: apps draw
    # one underline for a family, and fontbakery expects it to match.
    if 'underline' not in shared:
        ub = bounds(glyphs['underscore']['rec'])
        shared['underline'] = (round(ub[3]), round(ub[3] - ub[1]))
    under_pos, thick = shared['underline']
    fb.setupOS2(
        version=4, usWeightClass=700 if bold else 400, usWidthClass=5,
        # BOLD or REGULAR, and USE_TYPO_METRICS
        fsSelection=((1 << 5) if bold else (1 << 6)) | (1 << 7),
        sTypoAscender=TYPO_ASC, sTypoDescender=TYPO_DESC, sTypoLineGap=0,
        usWinAscent=math.ceil(y_max), usWinDescent=math.ceil(-y_min),
        sxHeight=x_height, sCapHeight=cap_height,
        yStrikeoutSize=thick, yStrikeoutPosition=round(x_height * 0.55),
        achVendID='    ', fsType=0,
        usDefaultChar=0, usBreakChar=32, usMaxContext=2,
    )
    fb.setupPost(keepGlyphNames=False, isFixedPitch=1 if style.mono else 0,
                 italicAngle=0, underlinePosition=under_pos, underlineThickness=thick)
    font = fb.font
    font['head'].fontRevision = VERSION
    font['head'].macStyle = 1 if bold else 0
    from fontTools.ttLib.tables.O_S_2f_2 import Panose
    p = Panose()
    panose = list(style.panose)
    panose[2] = 8 if bold else 5          # weight: Bold, or Book
    (p.bFamilyType, p.bSerifStyle, p.bWeight, p.bProportion, p.bContrast, p.bStrokeVariation,
     p.bArmStyle, p.bLetterForm, p.bMidline, p.bXHeight) = panose
    os2 = font['OS/2']
    os2.panose = p
    os2.recalcUnicodeRanges(font)
    os2.recalcCodePageRanges(font)
    os2.recalcAvgCharWidth(font)
    if style.mono:
        # Terminals size their cell by the average width: keep it one cell,
        # though Chinese takes two.
        os2.xAvgCharWidth = style.advance

    addOpenTypeFeaturesFromString(font, features(style, glyphs, pairs, anchors))
    from fontTools.otlLib.maxContextCalc import maxCtxFont
    os2.usMaxContext = maxCtxFont(font)
    print(f'{family} {style.weight}: {len(order)} glyphs, {len(cmap)} characters, {len(pairs)} kerned character pairs, '
          f'lifted {lift}, x-height {x_height}, cap height {cap_height}')
    return font, shared


def autohint(font):
    """Stem and zone hints from AFDKO's otfautohint, for rasterisers that
    use them (Windows, FreeType). Box drawing and blocks are left unhinted:
    their edges are the cell's, and must not move to the pixel grid on
    their own or rows would stop joining."""
    cmap = font.getBestCmap()
    cell = sorted({cmap[cp] for cp in cmap if 0x2500 <= cp < 0x25A0 or cp == 0x23BF or 0xE0B0 <= cp <= 0xE0B3})
    # Chinese has its own lines, not the Latin's blue zones: leave it unhinted
    # rather than snap its strokes to the x-height and cap height.
    cell += sorted({cmap[cp] for cp in cmap if chr(cp) in hanzi.C})
    cell += sorted(n for n in font.getGlyphOrder()
                   if '.zhs' in n or n.endswith(('.vert', '.arrow_r', '.arrow_l', '.fat_r', '.neq', '.lte', '.gte')))
    with tempfile.TemporaryDirectory() as t:
        src, dst = Path(t) / 'in.otf', Path(t) / 'out.otf'
        font.save(src)
        cmd = [str(Path(sys.executable).parent / 'otfautohint'), str(src), '-o', str(dst)]
        if cell:
            cmd += ['-x', ','.join(cell)]
        subprocess.run(cmd, check=True, capture_output=True)
        hinted = TTFont(dst)
        hinted.ensureDecompiled()
    return hinted


def build(key):
    """Regular, then Bold on the Regular's line; both get the family's
    largest ink bounds as win metrics, so neither clips the other's glyphs."""
    regular, shared = make(STYLES[key](), None)
    bold, _ = make(STYLES[key](bold=True), shared)
    win_asc = max(f['OS/2'].usWinAscent for f in (regular, bold))
    win_desc = max(f['OS/2'].usWinDescent for f in (regular, bold))
    OUT.mkdir(exist_ok=True)
    for font in (regular, bold):
        font['OS/2'].usWinAscent, font['OS/2'].usWinDescent = win_asc, win_desc
        font = autohint(font)
        # Shared runs of outline (an accented letter's base, a repeated
        # stroke) become CFF subroutines: the same glyphs, smaller files.
        cffsubr.subroutinize(font)
        ps = font['name'].getDebugName(6)
        otf = OUT / f'{ps}.otf'
        font.save(otf)
        # Brotli finds the repeats itself, and packs plain charstrings
        # tighter than subroutine calls: the web font goes without.
        w = TTFont(otf)
        cffsubr.desubroutinize(w)
        w.flavor = 'woff2'
        w.save(OUT / f'{ps}.woff2')
        print(f'  -> {otf.name}, {otf.stat().st_size // 1024} KB')


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a != '--no-cache']
    if '--no-cache' in sys.argv[1:]:
        os.environ['YISU_NO_CACHE'] = '1'
    for key in (args or list(STYLES)):
        build(key)
