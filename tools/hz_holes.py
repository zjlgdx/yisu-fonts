#!/usr/bin/env python3
"""The gate on openings: a part whose insides fill in under the bold pens.

    tools/hz_holes.py REF                  every form changed since REF; exit 1 if a part got worse
    tools/hz_holes.py REF --chars 月日     these forms too, changed or not (after a change to the pens)
    tools/hz_holes.py REF --looked 瓊      forms whose parts changed, judged by eye on hz_diff's sheets
    tools/hz_holes.py --where 瓊           the openings of each part of these forms, in this tree

hz_ink sees ink between parts; nothing saw ink inside one. 0.9999's first try
cleared 瓊's 目 from 攵 and 墮's 月 from 左 by giving them smaller boxes, and in
Louhen Bold 目's three openings closed to one and 月's to none: solid blocks,
which every other gate passed.

Each part is drawn alone, in its place in the whole form and with the whole
form's pen width, in each bold pen, and its openings counted: white regions
its own ink closes in, at least MIN cells (a cell is two grid units square).
Only the smallest parts are judged, those with no part inside them; a larger
part's openings include the pockets between its parts, which open as they
come apart. A part is worse when, in any pen, an opening of BIG cells or more
is lost, or its openings lose a third of their area (when they had 20 cells or
more). Yinni's stroke corners close small pockets of their own, so in Yinni
only openings of BIG cells or more count.

It checks REF out beside this tree, as hz_diff.py does, and compares the forms
whose drawing changed (Taiwan's, and the mainland's of their own). It picks
them by their strokes: a change to the pens or to hanzi.py changes every
glyph and no drawing, so name the forms to measure with --chars. A form whose
parts are no longer the same strokes (their ranges changed, or two parts of
one size traded places, told by their strokes' kinds) can't be compared
part by part: it fails until it is named in --looked, once its hz_diff sheet
has been looked at. A form new since REF is listed. When the drawing code
(hanzi.py, skeleton.py, outline.py, build.py past its VERSION) changed since
REF, it fails unless --chars names forms to measure.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from collections import deque
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STYLES = ('yinni', 'huasha', 'louhen')
MIN = 3          # cells: smaller white specks are not openings
BIG = 300        # cells: an opening that must not close; in Yinni, the least that counts at all
LOSS = 2 / 3     # the share of the openings' area a part must keep


def siblings(item, lo=0):
    """(strokes, [[(lo, hi) of each sibling part] for every node]), as hz_ink.py reads a form."""
    if isinstance(item, list):
        return len(item), []
    kids = [item[1], item[2]] if item[0] in ('lr', 'tb') else [p for p, _ in item[1]]
    here, below, at = [], [], lo
    for k in kids:
        n, sub = siblings(k, at)
        here.append((at, at + n))
        below += sub
        at += n
    return at - lo, [here] + below


def leaves(item):
    """The parts with no part inside them; a form drawn as one list of strokes is one part."""
    n, nodes = siblings(item)
    parts = sorted({r for node in nodes for r in node}) or [(0, n)]
    return [(lo, hi) for lo, hi in parts if not any((l, h) != (lo, hi) and lo <= l and h <= hi for l, h in parts)]


def openings(m):
    """Sizes of the white regions that don't reach the edge, MIN cells or more."""
    h, w = m.shape
    seen = m.copy()
    out = []
    for y0 in range(h):
        for x0 in range(w):
            if seen[y0, x0]:
                continue
            q = deque([(y0, x0)])
            seen[y0, x0] = True
            n, edge = 0, False
            while q:
                y, x = q.popleft()
                n += 1
                edge = edge or y in (0, h - 1) or x in (0, w - 1)
                for yy, xx in ((y + 1, x), (y - 1, x), (y, x + 1), (y, x - 1)):
                    if 0 <= yy < h and 0 <= xx < w and not seen[yy, xx]:
                        seen[yy, xx] = True
                        q.append((yy, xx))
            if not edge and n >= MIN:
                out.append(n)
    return sorted(out)


def measure(keys):
    """{'C瓊': {'10-15': [[sizes] per pen], ...}} for (form, char) keys, in the tree at the cwd."""
    sys.path[:0] = [os.getcwd()]
    from unittest.mock import patch
    import numpy as np
    import build
    import hanzi
    import hanzi_strokes as H
    real, width = hanzi.placed, hanzi.density_scale
    cell = max(1, round(2 * build.S))
    out = {}
    for f, ch in keys:
        form = int(f == 'S')
        item = (H.C, H.ZHS)[form].get(ch)
        if item is None:
            continue
        here = out[f + ch] = {}
        kinds = ''.join(k for k, _ in hanzi.flatten(item))
        for lo, hi in leaves(item):
            # a part is its strokes' range and kinds: two parts of one size that trade places differ
            row = here[f'{lo}-{hi} {kinds[lo:hi]}'] = []
            for key in STYLES:
                st = build.STYLES[key](bold=True)
                drawn = []

                def some(*a, _lo=lo, _hi=hi, **kw):
                    strokes, warp, r = real(*a, **kw)
                    drawn[:] = strokes
                    return strokes[_lo:_hi], warp, r

                def pen(c, _strokes, *a):
                    # the build's own width: from the whole form as it is placed
                    return width(c, drawn, *a)
                with patch.object(hanzi, 'placed', some), patch.object(hanzi, 'density_scale', pen):
                    m = np.asarray(st.draw(ch, build.canvas(st, ch), form).reduce(cell)) > 64
                row.append(openings(m))
    return out


def measured(tree, keys, jobs):
    """measure() run in `tree`, the keys spread over processes."""
    keys = list(keys)
    chunks = [keys[i::jobs] for i in range(jobs) if keys[i::jobs]]
    out = {}
    with ProcessPoolExecutor(len(chunks) or 1) as ex:
        for part in ex.map(_run, [(str(tree), c) for c in chunks]):
            out.update(part)
    return out


def _run(job):
    tree, keys = job
    r = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--measure', json.dumps(keys)],
                       cwd=tree, check=True, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return json.loads(r.stdout)


def worse(was, now):
    """[(pen, (count, area) before, after)] where a part got worse."""
    out = []
    for pen, a, b in zip(STYLES, was, now):
        least = BIG if pen == 'yinni' else 0
        area = lambda v: sum(s for s in v if s >= least)
        big = lambda v: sum(1 for s in v if s >= BIG)
        if (area(a) >= 20 and area(b) < LOSS * area(a)) or big(b) < big(a):
            out.append((pen, (big(a), area(a)), (big(b), area(b))))
    return out


DUMP = ('import sys, json, hashlib; sys.path.insert(0, "."); import hanzi_strokes as h; from hanzi import flatten; '
        'd = lambda v: hashlib.md5(repr(flatten(v)).encode()).hexdigest(); '
        'print(json.dumps({"C": {k: d(v) for k, v in h.C.items()}, "S": {k: d(v) for k, v in h.ZHS.items()}}))')


def by_range(parts):
    """{'4-8': (kinds, [[sizes] per pen])} from measure()'s {'4-8 PGEE': [...]}."""
    return {key.split(' ')[0]: (key.split(' ')[1], v) for key, v in parts.items()}


def moved(was, now):
    """Whether the parts are no longer the same strokes: their ranges changed, or a part now has the kinds
    another part had (two parts of one size that traded places). A stroke whose kind changed in place is
    measured as before."""
    return set(was) != set(now) or any(
        now[r][0] != was[r][0] and now[r][0] in {was[q][0] for q in was if q != r} for r in now)


DRAWING = ('hanzi.py', 'skeleton.py', 'outline.py', 'build.py')


def drawing_changed(ref):
    """The files of the drawing code that changed since ref, a release's VERSION line aside."""
    out = []
    for f in DRAWING:
        d = subprocess.run(['git', 'diff', ref, '--', f], cwd=ROOT, check=True, capture_output=True, text=True).stdout
        if any(l[:1] in '+-' and not l.startswith(('+++', '---')) and not l[1:].startswith('VERSION =')
               for l in d.splitlines()):
            out.append(f)
    return out


def forms(tree):
    return json.loads(subprocess.run([sys.executable, '-c', DUMP], cwd=tree, check=True, capture_output=True, text=True).stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('ref', nargs='?')
    ap.add_argument('--where', help='print the openings of these forms, in this tree')
    ap.add_argument('--chars', default='', help='measure these forms too, changed or not')
    ap.add_argument('--looked', default='', help='forms whose parts changed, judged by eye')
    ap.add_argument('--measure', help=argparse.SUPPRESS)
    ap.add_argument('--jobs', type=int, default=max(1, (os.cpu_count() or 2) - 2))
    a = ap.parse_args()
    if a.measure:
        print(json.dumps(measure(json.loads(a.measure)), ensure_ascii=False))
        return
    if a.where:
        got = measured(ROOT, [(f, ch) for ch in a.where for f in 'CS'], a.jobs)
        for k, parts in got.items():
            for r, row in parts.items():
                print(k, r, '  '.join(f'{p} {len([s for s in v if s >= BIG])} of {BIG}+ / {sum(v)} cells' for p, v in zip(STYLES, row)))
        return
    if not a.ref:
        ap.error('give REF, or --where')
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp) / 'base'
        try:
            subprocess.run(['git', 'worktree', 'add', '-q', '--detach', str(base), a.ref], cwd=ROOT, check=True)
            was, now = forms(base), forms(ROOT)
            unknown = [c for c in a.chars if not c.isspace() and c not in now['C'] and c not in now['S']]
            if unknown:
                ap.error(f'--chars names forms this tree doesn\'t draw: {"".join(unknown)}')
            default = [k for k in now['C'] if len(k) == 1 and k in was['C'] and (was['C'][k] != now['C'][k] or k in a.chars)]
            mainland = [k for k in now['S'] if len(k) == 1 and k in was['S'] and (was['S'][k] != now['S'][k] or k in a.chars)
                        and (now['S'][k] != now['C'].get(k) or was['S'][k] != was['C'].get(k))]
            new = [k for k in now['C'] if len(k) == 1 and k not in was['C']] + \
                  [k + '(S)' for k in now['S'] if len(k) == 1 and k not in was['S'] and now['S'][k] != now['C'].get(k)]
            keys = [('C', k) for k in default] + [('S', k) for k in mainland]
            old, now_ = measured(base, keys, a.jobs), measured(ROOT, keys, a.jobs)
        finally:
            if base.exists() and subprocess.run(['git', 'worktree', 'remove', '--force', str(base)], cwd=ROOT).returncode:
                print(f'could not remove the worktree {base}: run `git worktree prune`', file=sys.stderr)
    changed = drawing_changed(a.ref)
    bad, other, looked = [], [], []
    for f, ch in keys:
        k = f + ch
        o, n = by_range(old.get(k, {})), by_range(now_.get(k, {}))
        if moved(o, n):
            (looked if ch in a.looked else other).append(ch + ('(S)' if f == 'S' else ''))
            continue
        for r in n:
            for pen, x, y in worse(o[r][1], n[r][1]):
                bad.append(k)
                print(f'  {ch}{"(S)" if f == "S" else ""} strokes {r} {n[r][0]}, {pen} bold: openings of {BIG}+ {x[0]} -> {y[0]}, area {x[1]} -> {y[1]} cells')
    print(f'measured {len(keys)} forms changed since {a.ref} in the three bold pens')
    if changed and not a.chars:
        print(f'FAIL the drawing code changed since {a.ref} ({", ".join(changed)}), which changes forms without '
              'changing their strokes: name the forms it touches with --chars')
    if new:
        print(f'  new since {a.ref}, nothing to compare ({len(new)}): {"".join(new)}')
    if looked:
        print(f'  parts no longer the same strokes, judged by eye (--looked): {"".join(looked)}')
    if other:
        print(f'FAIL parts no longer the same strokes ({len(other)}): {"".join(other)}: look at their hz_diff sheets, '
              'then name them in --looked')
    print(f'{len(set(bad))} forms with a part whose openings closed or shrank' if bad else 'no part closed its openings')
    sys.exit(1 if bad or other or (changed and not a.chars) else 0)


if __name__ == '__main__':
    main()
