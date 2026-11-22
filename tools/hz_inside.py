#!/usr/bin/env python3
"""The gate on what is inside one part, and on two characters drawn as one.

    tools/hz_inside.py                 exit 1 on a finding the baseline lacks
    tools/hz_inside.py --batch A.py    with a round's draft batches
    tools/hz_inside.py --accept        write the baseline (tools/hz_inside.tsv)
    tools/hz_inside.py --selftest      seed known defects; each must be found
    tools/hz_inside.py --debt          list what the baseline holds today

hz_gate.py measures how sibling parts sit together. It does not look inside a
list of strokes, and it does not compare one character with another, so 0.991
shipped all of these with the gate green:

  same    two characters with the very same drawing (沈 was 沉's, 剝 was 剥's,
          朮 was 术's, 伫 was 佇's): one of the two is not its own form.
          Compared among Taiwan's forms and among the mainland's.
  twice   two strokes of one part that run along each other, level or
          upright, for 60 or more and 12 or less apart: one line drawn twice
          (𠂤's middle bar, 官's), which the heavy pens draw as a blot.
  dot     a 點 that crosses another stroke of its part away from both ends.
          The 乂 of 区 and 网 is a 撇 and a 點 crossed in the middle and is
          left alone; a dot drawn through a bar or through one end of a 撇
          is not that.
  flick   a stroke that comes down upright for 250 or more and ends in a
          short tail down and to the left. A 豎提 turns up and to the right
          (民 and 氏 had it backwards); a 豎撇 is written as a curve.

twice, dot and flick are found in the part where they are drawn (K, L or a
character's own strokes) and named by it, so one finding is one thing to fix
however many characters hold the part.

A finding in the baseline is debt: it is listed by --debt and fails nothing.
One the baseline lacks fails. One the baseline holds and the drawing no longer
shows is reported as cleared, and --accept drops it. Accept only after a
finding has been looked at on a sheet: the baseline's diff is what the
reviewer reads. Run --selftest after changing this file.
"""
import argparse
import sys
from pathlib import Path

import _repo
from hz_gate import polyline

BASE = Path(__file__).with_name('hz_inside.tsv')
RUN, TWICE = 60, 12
DROP, TAIL = 250, 260
CHECKS = ('same', 'twice', 'dot', 'flick')


def han(name):
    return len(name) == 1 and ord(name) >= 0x3400


def parts(h):
    """{name: strokes} for every list of strokes, named by the entry that is
    that list (C['官'], not the 管 built on it), else by the first that holds
    it; K before L before C."""
    seen = {}

    def walk(x, name):
        if isinstance(x, list):
            seen.setdefault(id(x), (name, x))
        elif isinstance(x, tuple) and x and x[0] == 'box':
            for p, _ in x[1]:
                walk(p, name)
        elif isinstance(x, tuple) and x and x[0] in ('lr', 'tb'):
            walk(x[1], name)
            walk(x[2], name)
    for own in (True, False):
        for d, tag in ((h.K, 'K'), (h.L, 'L'), (h.C, 'C'), (h.ZHS, 'ZHS')):
            for n, v in d.items():
                # kana and symbols have their own rules
                if (tag in 'KL' or han(n)) and (isinstance(v, list) or not own):
                    walk(v, f"{tag}['{n}']")
    return dict(seen.values())


def runs(pts):
    """The level and upright runs of a centre line: ('h', y, x0, x1) and
    ('v', x, y0, y1), each RUN long or more."""
    out = []
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        if abs(x1 - x0) >= RUN and abs(y1 - y0) <= 12:
            out.append(('h', (y0 + y1) / 2, min(x0, x1), max(x0, x1)))
        elif abs(y1 - y0) >= RUN and abs(x1 - x0) <= 12:
            out.append(('v', (x0 + x1) / 2, min(y0, y1), max(y0, y1)))
    return out


def twice(strokes):
    lines = [runs(polyline(d)) for _, d in strokes]
    for i in range(len(lines)):
        for j in range(i + 1, len(lines)):
            for a in lines[i]:
                for b in lines[j]:
                    if a[0] == b[0] and abs(a[1] - b[1]) <= TWICE and min(a[3], b[3]) - max(a[2], b[2]) >= RUN:
                        return True
    return False


def crosses(a, b):
    """Where polyline a crosses b away from the ends of both, as the share of
    each one's length, or None."""
    def along(pl):
        out = [0.0]
        for p, q in zip(pl, pl[1:]):
            out.append(out[-1] + ((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2) ** .5)
        return out
    la, lb = along(a), along(b)
    if not la[-1] or not lb[-1]:
        return False
    for i in range(len(a) - 1):
        for j in range(len(b) - 1):
            (x1, y1), (x2, y2), (x3, y3), (x4, y4) = a[i], a[i + 1], b[j], b[j + 1]
            d = (x2 - x1) * (y4 - y3) - (y2 - y1) * (x4 - x3)
            if abs(d) < 1e-9:
                continue
            t = ((x3 - x1) * (y4 - y3) - (y3 - y1) * (x4 - x3)) / d
            u = ((x3 - x1) * (y2 - y1) - (y3 - y1) * (x2 - x1)) / d
            if 0 <= t <= 1 and 0 <= u <= 1:
                fa = (la[i] + t * (la[i + 1] - la[i])) / la[-1]
                fb = (lb[j] + u * (lb[j + 1] - lb[j])) / lb[-1]
                if .15 < fa < .85 and .08 < fb < .92:
                    return fa, fb
    return None


def dot(strokes):
    pl = [(k, polyline(d)) for k, d in strokes]
    for k, p in pl:
        if k != 'D' or len(p) < 2:
            continue
        for kq, q in pl:
            at = crosses(p, q) if q is not p and len(q) > 1 else None
            # 乂: a 撇 and a 點 through each other's middle
            if at and not (kq == 'P' and .3 <= at[0] <= .7 and .3 <= at[1] <= .7):
                return True
    return False


def flick(strokes):
    for _, d in strokes:
        pts = polyline(d)
        if len(pts) < 3:
            continue
        (x0, y0), (x1, y1), (x2, y2) = pts[-3:]
        tail = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** .5
        if abs(x1 - x0) <= 12 and y1 - y0 >= DROP and x2 - x1 <= -40 and y2 - y1 > 0 and tail <= TAIL:
            return True
    return False


def same(h, hanzi):
    """Pairs of characters with one drawing, among Taiwan's forms and among
    the mainland's (a ZHS form where there is one, the default otherwise)."""
    out = set()
    tw = {k: v for k, v in h.C.items() if han(k)}
    cn = {**tw, **{k: v for k, v in h.ZHS.items() if han(k)}}
    for forms in (tw, cn):
        by = {}
        for ch, v in forms.items():
            by.setdefault(repr(hanzi.flatten(v)), []).append(ch)
        for group in by.values():
            for ch in group[1:]:
                out.add(''.join(sorted((group[0], ch))))
    return out


def findings(h):
    import hanzi
    out = {('same', pair) for pair in same(h, hanzi)}
    for name, strokes in parts(h).items():
        for check, fn in (('twice', twice), ('dot', dot), ('flick', flick)):
            if fn(strokes):
                out.add((check, name))
    return out


def baseline():
    if not BASE.exists():
        return set()
    return {tuple(line.split('\t')) for line in BASE.read_text(encoding='utf-8').splitlines() if line and not line.startswith('#')}


def listing(found):
    for check in CHECKS:
        names = sorted(n for c, n in found if c == check)
        if names:
            print(f'  {check} ({len(names)}): ' + ' '.join(names))


def selftest():
    h = _repo.load()
    before = findings(h)
    S = h.S
    seeds = {
        ('same', '㐀㐁'): lambda: h.C.update({'㐀': S('E M100 500 L900 500; E M500 100 L500 900'), '㐁': S('E M100 500 L900 500; E M500 100 L500 900')}),
        ('twice', "K['seed-bar']"): lambda: h.K.update({'seed-bar': S('E M160 120 L780 120 L780 470; E M160 470 L780 470; E M160 470 L780 470 L780 880')}),
        ('twice', "K['seed-wall']"): lambda: h.K.update({'seed-wall': S('E M200 100 L200 800; P M208 300 L208 700 C200 800 150 880 80 940')}),
        ('dot', "K['seed-dot']"): lambda: h.K.update({'seed-dot': S('E M100 500 L900 500; D M450 400 C480 460 500 540 520 620')}),
        ('flick', "K['seed-flick']"): lambda: h.K.update({'seed-flick': S('E M190 80 L190 780 L60 870')}),
    }
    clean = {
        "K['seed-ok-口']": S('E M200 240 L200 760; E M200 240 L800 240 L800 760; E M200 750 L800 750'),
        "K['seed-ok-提']": S('E M260 155 L260 780 L400 700'),
        "K['seed-ok-點']": S('E M100 300 L900 300; D M480 60 C520 100 540 140 550 200'),
        "K['seed-ok-乂']": S('P M700 200 C600 450 450 650 250 800; D M300 250 C450 450 600 650 750 780'),
    }
    bad = 0
    for key, seed in seeds.items():
        seed()
        if key not in findings(h):
            print(f'  NOT FOUND: the seeded {key[0]} defect {key[1]}')
            bad += 1
    for name, strokes in clean.items():
        h.K[name[3:-2]] = strokes
    extra = {f for f in findings(h) - before if f not in seeds}
    if extra:
        print('  FOUND in a clean seed: ' + ' '.join(f'{c}:{n}' for c, n in sorted(extra)))
        bad += 1
    print(f'  {len(seeds) - bad if bad <= len(seeds) else 0} of {len(seeds)} seeded defects found, {len(clean)} clean seeds' + (' pass' if not extra else ''))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', default='')
    ap.add_argument('--accept', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--debt', action='store_true')
    a = ap.parse_args()
    if a.selftest:
        sys.exit(selftest())
    found = findings(_repo.load(a.batch))
    if a.accept:
        if a.batch:
            sys.exit('accept after the batch is merged')
        BASE.write_text('# tools/hz_inside.py --accept: findings looked at and left for now. check, then the part or the pair.\n'
                        + ''.join(f'{c}\t{n}\n' for c, n in sorted(found, key=lambda f: (CHECKS.index(f[0]), f[1]))), encoding='utf-8')
        print(f'  baseline written: {len(found)} findings')
        return
    base = baseline()
    if a.debt:
        listing(found & base)
        print(f'  {len(found & base)} in the baseline')
        return
    new, cleared = found - base, base - found
    if cleared:
        print(f'  cleared since the baseline ({len(cleared)}; --accept drops them):')
        listing(cleared)
    if new:
        print(f'  NEW ({len(new)}): look at each on a sheet, then fix it or --accept')
        listing(new)
        sys.exit(1)
    print(f'  nothing new inside a part ({len(found & base)} in the baseline)')


if __name__ == '__main__':
    main()
