"""Chinese for the Yisu fonts, written with each family's own pen.

The Latin letters are centre lines (skeleton.py) inked by a pen. Chinese is
drawn the same way, with one more layer, because characters share their
parts:

- A stroke (筆畫) is a centre line plus how the pen moves along it. `E` is
  even, with a slight press where the pen lands (橫, 豎, the turns). `P`
  lifts as it goes, ending lighter (撇, 提). `G` stays even and lifts only
  in its final hook (豎鉤, 橫折鉤, 斜鉤). `N` presses toward its end and
  lifts at the foot (捺). `D` is a dot (點), heavier where it ends.
- A component (部件) is a list of strokes on a 1000-unit grid, y down.
- A character is a component, or components placed in boxes: `lr` (left and
  right, ⿰), `tb` (top and bottom, ⿱), or `box` with explicit boxes for
  enclosures (⿴ ⿵ ⿶ ⿸ ⿹ ⿺) and anything else. A component scales into its
  box; the pen does not, so strokes keep one weight in any part.

Every stroke here was drawn for this font, from what each character is: no
other font's outlines or stroke data. The grid's frame is the character's
face.

Each family writes the same strokes its own way (CUTS): Yinni as
仿宋 metal type struck through a ribbon, Huasha as a hand's 楷書, Louhen
with its own chisel nib. Only the pen and the grid's transform
differ, so a character drawn once serves all three.
"""
import math
import random
import re

# Each family's cut of Chinese.
#   em      the character's advance, font units (Yinni's two cells)
#   face    how much of it the grid's frame fills, font units
#   pen     the pen against the family's Latin pen: (Regular, Bold). Dense
#           characters stay open under the Bold.
#   nib     the round pen's reach across and along a stroke, against its
#           radius: wider than tall makes verticals heavier than horizontals
#   cut     the pressure profile along each stroke (see profile)
#   rise    degrees horizontals climb to the right; verticals stay upright
#   lean    degrees the whole character leans, to sit with a leaning Latin
#   narrow, tall   the face's width and height, against square
#   hand    how much each stroke strays from its place, as a hand's do
#   inked   times Yinni's ribbon is struck over it
#   dense   the Bold pen in a form of much line: (how much narrower at most,
#           the length of line, in ems, where it starts and where it ends)
CUTS = {
    # 仿宋 type, after the slugs of the Chinese typewriter: rising
    # horizontals, a narrow upright face, a press where the pen lands and
    # stops, a little contrast, and a worn ribbon.
    'yinni': dict(em=1200, face=1060, pen=(0.92, 0.76), nib=(1.12, 0.70), cut='fang',
                       rise=5.5, lean=0, narrow=0.90, tall=1.03, hand=0, inked=2,
                       dense=(0.16, 4.4, 7.2)),
    # A hand's 楷書 in ballpoint: pressure that comes and goes, rising
    # horizontals, the Latin's lean (less of it), each stroke a little astray.
    'huasha': dict(em=1000, face=900, pen=(1.0, 0.85), nib=(1.0, 0.93), cut='hand',
                      rise=4.5, lean=4, narrow=1.0, tall=1.0, hand=1.0, inked=0, dense=None),
    # Louhen's chisel at 35 degrees: thick and thin come from the nib.
    'louhen': dict(em=1000, face=940, pen=(0.92, 0.82), nib=None, cut='even',
                   rise=3, lean=0, narrow=1.0, tall=1.0, hand=0.6, inked=0, dense=(0.32, 4.0, 7.2)),
}

# ---------------------------------------------------------------- strokes

STROKE_KINDS = 'EPGND'


def ease(a, b, x):
    x = min(1.0, max(0.0, (x - a) / (b - a)))
    return x * x * (3 - 2 * x)


def profile(kind, t, cut='kai'):
    """The pen's radius, as a share of its usual one, at t (0 to 1) along a
    stroke of this kind, in one of the cuts:

    - kai: hard-pen 楷書, one weight with a slight press where the pen lands.
    - fang: 仿宋, a firm press where the pen lands and a small one where it
      stops (頓筆); 撇 thins further.
    - hand: kai with a ballpoint's pressure, lighter where it lands and lifts.
    - even: one weight throughout (a broad nib makes its own thick and thin).
    """
    if cut == 'even':
        return 1.15 if kind == 'D' else 1.0
    if cut == 'hand':
        return profile(kind, t) * (0.86 + 0.14 * math.sin(math.pi * min(1.0, t * 1.1)))
    if cut == 'fang':
        if kind == 'E':
            return 1.0 + 0.32 * (1 - ease(0, .1, t)) + 0.16 * ease(.9, 1, t)
        if kind == 'G':
            return 1.0 + 0.32 * (1 - ease(0, .1, t)) - 0.5 * ease(.86, 1, t)
        if kind == 'P':
            return 1.15 - 0.62 * ease(.35, 1, t)
        if kind == 'N':
            return 0.75 + 0.55 * ease(0, .8, t) - 0.6 * ease(.85, 1, t)
        if kind == 'D':
            return 0.7 + 0.6 * ease(0, .9, t)
        raise ValueError(kind)
    if kind == 'E':
        return 1.0 + 0.14 * (1 - ease(0.0, 0.08, t))
    if kind == 'P':
        return 1.08 - 0.5 * ease(0.45, 1.0, t)
    if kind == 'G':
        return 1.0 + 0.14 * (1 - ease(0.0, 0.06, t)) - 0.45 * ease(0.86, 1.0, t)
    if kind == 'N':
        return 0.82 + 0.38 * ease(0.0, 0.78, t) - 0.55 * ease(0.82, 1.0, t)
    if kind == 'D':
        return 0.7 + 0.5 * ease(0.0, 0.9, t)
    raise ValueError(kind)


def strokes(spec):
    """'E M100 200 L900 200; P M…' -> [(kind, path)]."""
    out = []
    for part in spec.split(';'):
        part = part.strip()
        if part:
            out.append((part[0], part[1:].strip()))
    return out


from hanzi_strokes import C, TONES, VERTICAL, VERT_ALT, VZHS, ZHS   # noqa: E402,F401  (the characters, kept apart from the engine)


def flatten(item, box=(0, 0, 1000, 1000)):
    """A character or component as [(kind, path)] in the 1000 grid of `box`."""
    from skeleton import transform
    x0, y0, x1, y1 = box
    sx, sy = (x1 - x0) / 1000, (y1 - y0) / 1000

    def into(b):
        return (x0 + b[0] * sx, y0 + b[1] * sy, x0 + b[2] * sx, y0 + b[3] * sy)
    if isinstance(item, list):
        return [(k, transform(d, lambda p: (x0 + p[0] * sx, y0 + p[1] * sy))) for k, d in item]
    op = item[0]
    if op == 'lr':
        _, a, b, r = item
        return flatten(a, into((0, 0, 1000 * r, 1000))) + flatten(b, into((1000 * r, 0, 1000, 1000)))
    if op == 'tb':
        _, a, b, r = item
        return flatten(a, into((0, 0, 1000, 1000 * r))) + flatten(b, into((0, 1000 * r, 1000, 1000)))
    if op == 'box':
        return [s for part, b in item[1] for s in flatten(part, into(b))]
    raise ValueError(op)


_PATH = re.compile(r'[MLlC]|-?[\d.]+')


def line_length(strokes):
    """The length of a character's centre lines, in ems of its 1000 grid."""
    total = 0.0
    for _kind, d in strokes:
        t, i, cmd, cur = _PATH.findall(d), 0, 'M', None
        while i < len(t):
            if t[i] in 'MLlC':
                cmd = t[i]
                i += 1
                continue
            n = 6 if cmd == 'C' else 2
            v = [float(x) for x in t[i:i + n]]
            i += n
            if cmd == 'C':
                p, last = [cur, v[0:2], v[2:4], v[4:6]], cur
                for k in range(1, 9):
                    u = k / 8
                    w = 1 - u
                    at = [w ** 3 * p[0][a] + 3 * w * w * u * p[1][a] + 3 * w * u * u * p[2][a] + u ** 3 * p[3][a] for a in (0, 1)]
                    total += math.dist(last, at)
                    last = at
                cur = v[4:6]
            else:
                to = [cur[0] + v[0], cur[1] + v[1]] if cmd == 'l' else v
                if cmd != 'M':
                    total += math.dist(cur, to)
                else:
                    cmd = 'L'       # pairs after the first of an M are lines to
                cur = to
    return total / 1000


def density_scale(ch, strokes, bold=False, family=None):
    """The pen's width for a Chinese character, by how many strokes it has: a
    character of a few strokes (一 十 人) a little wider, up to 6% (4% in Bold),
    so it is not faint beside its neighbours; one of many (鬱 靈 讓) a little
    narrower, down to 8% (12% in Bold), so its spaces stay open. Characters of
    7 to 10 strokes keep the pen as it is. Kana and punctuation are left alone.

    A family's Bold may also narrow by how much line the form has (the cut's
    `dense`): the narrower of the two rules is used, and a form of few
    strokes and much line (而) keeps its share of the widening. Strokes do not say how full a form is:
    邊 has nineteen and 5.3 ems of line, 彈 fifteen and 6.6, and it is 彈 that
    the broad pen fills."""
    cp = ord(ch)
    if not (0x3400 <= cp <= 0x9FFF or 0xF900 <= cp <= 0xFAFF or 0x20000 <= cp <= 0x3FFFF):
        return 1.0      # CJK Unified (with Extension A and B onward) and Compatibility only
    n = len(strokes)
    scale = 1.0
    if n <= 6:
        scale = 1.0 + (0.04 if bold else 0.06) * (1.0 - ease(1, 7, n))
    elif n >= 11:
        scale = 1.0 - (0.12 if bold else 0.08) * ease(10, 24, n)
    dense = CUTS[family]['dense'] if bold and family else None
    if dense:
        depth, lo, hi = dense
        thin = 1.0 - depth * ease(lo, hi, line_length(strokes))
        scale = scale * thin if n <= 6 else min(scale, thin)
    return scale


_START = re.compile(r'M\s*(-?[\d.]+)[\s,]+(-?[\d.]+)')


def by_hand(strokes, rng, amount):
    """Each stroke shifted, turned and sized a little about where it starts,
    as a hand's strokes stray: the character stays itself, the parts loosen.
    Past 8 strokes they stray less (two thirds as much at 18, never under 45%), so close parts don't
    run into each other."""
    from skeleton import transform
    if not amount:
        return strokes
    if len(strokes) > 8:
        amount *= max(0.45, 1.0 / (1.0 + (len(strokes) - 8) * 0.055))
    out = []
    for kind, d in strokes:
        sx, sy = map(float, _START.search(d).groups())
        dx, dy = rng.gauss(0, 9 * amount), rng.gauss(0, 9 * amount)
        a = math.radians(rng.gauss(0, 2.2 * amount))
        c, s = math.cos(a), math.sin(a)
        f = 1 + rng.gauss(0, 0.035 * amount)

        def m(p, sx=sx, sy=sy, c=c, s=s, dx=dx, dy=dy, f=f):
            x, y = (p[0] - sx) * f, (p[1] - sy) * f
            return sx + x * c - y * s + dx, sy + x * s + y * c + dy
        out.append((kind, transform(d, m)))
    return out


def placed(ch, family, cell, K, seed, form=0):
    """A character's strokes, and the warp from its 1000 grid onto the
    skeleton canvas: the family's cut, its face centred in `cell` (skeleton
    units, K of them to a font unit) and on the capitals (y 400), struck or
    written a little off. `form` 1 is the form mainland China sets in a line
    (ZHS), 2 the one it sets in a column (VZHS)."""
    cut = CUTS[family]
    rng = random.Random(seed)
    sc = cut['face'] / K / 1000
    rise = math.tan(math.radians(cut['rise']))
    lean = math.tan(math.radians(cut['lean']))
    nx, ty = cut['narrow'], cut['tall']
    dy = rng.uniform(-10, 10)
    rot = math.radians(rng.uniform(-1.1, 1.1))
    cr, sr = math.cos(rot), math.sin(rot)

    def warp(x, y):
        y = y - rise * (x - 500)
        x, y = 500 + (x - 500) * nx, 500 + (y - 500) * ty
        x = x - lean * (y - 500)
        x, y = (x - 500) * sc, (y - 500) * sc
        return x * cr - y * sr + cell / 2, x * sr + y * cr + 400 + dy
    return by_hand(flatten((C, ZHS, VZHS, VERT_ALT)[form][ch]), rng, cut['hand']), warp, rng
