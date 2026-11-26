#!/usr/bin/env python3
"""Move two parts of a form apart by measuring, not by eye.

    tools/hz_fit.py 寶                  the parts of 寶 and the ink between each two (hz_ink's measure)
    tools/hz_fit.py 崩 --pair 0,1       try moves that part 0 off part 1; print the smallest that clears them
    tools/hz_fit.py 崩 --pair 0,1 --write   and write it into hanzi_strokes.py
    tools/hz_fit.py 寶 --pair 0,1+2     parts 1 and 2 together off part 0
    tools/hz_fit.py 巍 --node 1 --pair 0,1   parts inside top-level part 1's own box
    tools/hz_fit.py S:祟 --pair 0,1     the mainland form, where it is drawn apart from Taiwan's

hz_ink.py says which parts join under the bold pens; this finds how far to
move them. 1.004 and 1.005 cleared 山 off the part under it in 33 forms this
way (123,674 and 114,221 cells of ink to 190 and 1,368), where guessing a box
by eye had taken rounds per form. It works on hanzi_strokes.py as it is: a
round's drafts are merged first.

A form is a box of parts, each in its rect. Of the two parts (or groups of
parts) named, the first stands above the second (--axis y) or to its left
(--axis x); the first gives up its far edge and the second its near edge,
each by shrinking (that edge moves) or shifting (the whole rect moves, and
stays on the grid; a part drawn on the full grid, as 宀 is, may shift off it,
as that is how it moves at all). --steps are in the units of the box worked
in: inside a part's own box (--node) they are that part's thousandths.
Every move is drawn and measured as hz_ink.py measures: the ink between the
two parts in each bold pen, and every other pair.

A move clears the two when the ink left between them, summed over the pens,
is --limit or less and none of it is in a pen where they stood clear; and no
other pair joins in a pen it was clear in, gains a quarter (and hz_ink's
RISE) in a pen, or comes under hz_ink's APART on paper. Of the moves that
clear it, the smallest (the two steps summed) wins; of those, the one that
splits it between the two parts, then the one that shrinks less. The winner
is then written into a copy of hanzi_strokes.py and every form whose drawing
that changes (the mainland's twins, forms built from the part) is measured
against what it was, else the next move is tried (the form itself is checked
first, in memory; at most --tries moves are checked in every form):

  - ink: the rules above, for every changed form;
  - openings (hz_holes.py's measure): no part may lose an opening, the trap
    of 1.003 (回, 目 filled in) and 1.005 (巍's 女);
  - edges: no ink at the canvas edge in any of the six fonts (edges.py).

When the room has to come from a third part (宀 over 王 and 缶 over 貝 in 寶),
move one pair with --allow naming the next, then move the next.

The copy is made by rewriting the box()/lr() call that defines the box, in
the statement that binds it (the form's own, or the K/C/ZHS name the box is
bound to; a mainland form built from Taiwan's is written in Taiwan's, which
changes both), read with Python's own parser, so a rect written as FULL or
RIGHT is replaced where it stands. When no statement defines the box, the
move is only checked on the one form, and --write refuses (exit 1).
"""
import argparse
import ast
import itertools
import json
import os
import subprocess
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import _repo

SRC = _repo.ROOT / 'hanzi_strokes.py'
OLD = {}        # measures of the forms as they are, by key, kept across the moves tried
PENS = ('yinni', 'huasha', 'louhen')


def form_of(key):
    """('C' or 'S', char) from 嵐 or S:巍."""
    if key.startswith('S:'):
        return 'S', key[2:]
    return 'C', key.removeprefix('C:')


def table(H, f):
    return H.ZHS if f == 'S' else H.C


def is_box(x):
    return isinstance(x, tuple) and len(x) == 2 and x[0] == 'box'


def node_at(item, path):
    """(the box at path, the stroke number its first part starts at)."""
    import hanzi
    lo = 0
    for i in path:
        if not is_box(item) or not 0 <= i < len(item[1]):
            raise SystemExit(f'no box at {path}')
        for p, _ in item[1][:i]:
            lo += len(hanzi.flatten(p))
        item = item[1][i][0]
    if not is_box(item):
        raise SystemExit(f'no box at {path}: {"strokes" if isinstance(item, list) else type(item).__name__}')
    return item, lo


def ranges(node, lo):
    import hanzi
    out = []
    for p, _ in node[1]:
        n = len(hanzi.flatten(p))
        out.append((lo, lo + n))
        lo += n
    return out


def swapped(item, old, new):
    """item with every occurrence of the box `old` replaced by `new` (a box used twice moves twice, as a write does)."""
    if item is old:
        return new
    if is_box(item):
        parts = [(swapped(p, old, new), r) for p, r in item[1]]
        if any(a is not b for (a, _), (b, _) in zip(parts, item[1])):
            return ('box', parts)
    elif isinstance(item, tuple) and len(item) == 4 and item[0] in ('lr', 'tb'):
        a, b = swapped(item[1], old, new), swapped(item[2], old, new)
        if a is not item[1] or b is not item[2]:
            return (item[0], a, b, item[3])
    return item


def moved(node, I, J, axis, d, e, di, dj):
    """The box with the parts in I giving up d at their far edge and those in J e at their near edge ('shrink' or 'shift')."""
    parts = list(node[1])
    a, b = (1, 3) if axis == 'y' else (0, 2)
    for ks, n, mode, near, far, sign in ((I, d, di, b, a, -1), (J, e, dj, a, b, 1)):
        for k in ks:
            p, r = parts[k]
            r = list(r)
            r[near] += sign * n
            if mode == 'shift':
                r[far] += sign * n
            parts[k] = (p, tuple(r))
    return ('box', parts)


def measure(job):
    """(apart pairs, near pairs) as hz_ink measures them, for the form with the box `node` swapped for `new`."""
    f, ch, path, new = job
    H = _repo.load()
    import hz_ink
    t = table(H, f)
    old = t[ch]
    if new is not None:
        t[ch] = swapped(old, node_at(old, path)[0], new)
    try:
        g = hz_ink.work(('', [(f, ch)]))[f, ch]
    finally:
        t[ch] = old
    return g[1], g[2]


def between(pairs, ri, rj):
    v = pairs.get((ri, rj)) or pairs.get((rj, ri))
    return tuple(v) if v else (0, 0, 0)


def rose(base, now, skip=frozenset()):
    """Pairs that join in a pen they were clear in, gain a quarter and RISE there, or came under APART on paper.
    base and now are (apart, near) as measure() gives them."""
    import hz_ink
    out = []
    was = {**base[0], **base[1]}
    for pq, v in {**now[0], **now[1]}.items():
        if pq in skip:
            continue
        if pq in base[0] and pq in now[1]:
            out.append(f'{pq} under APART on paper now')
        w = was.get(pq, (0, 0, 0))
        for pen, a, b in zip(PENS, w, v):
            if (a == 0 and b > 0) or (a and b > a * 1.25 and b - a > hz_ink.RISE):
                out.append(f'{pq} {pen} {a}->{b}')
    return out


def pen_ink(v):
    return ' '.join(f'{p[0]}{x}' for p, x in zip(PENS, v))


# ---- the source: find the call that defines a box, and rewrite it

def bindings(tree):
    """{"K['x']": the last statement assigning it} for K/L/C/ZHS."""
    out = {}
    for st in tree.body:
        if isinstance(st, ast.Assign) and len(st.targets) == 1:
            t = st.targets[0]
            if isinstance(t, ast.Subscript) and isinstance(t.value, ast.Name) and t.value.id in ('K', 'L', 'C', 'ZHS') \
                    and isinstance(t.slice, ast.Constant):
                out[f"{t.value.id}['{t.slice.value}']"] = st
    return out


def parts_of(call):
    """[(part expr, rect expr or None for FULL implied, default text)] of a box()/lr() call, or None."""
    if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Name):
        return None
    if call.func.id == 'box' and all(isinstance(a, ast.Tuple) and len(a.elts) == 2 for a in call.args) and not call.keywords:
        return [(a.elts[0], a.elts[1], None) for a in call.args]
    if call.func.id == 'lr' and 2 <= len(call.args) <= 3 and not call.keywords:
        return [(call.args[0], None, 'FULL'), (call.args[1], call.args[2] if len(call.args) == 3 else None, 'RIGHT')]
    return None


def follow(expr, binds, name):
    """Through K['x'] / C['x'] to the expression that defines it: (expr, the statement's name)."""
    seen = set()
    while isinstance(expr, ast.Subscript) and isinstance(expr.value, ast.Name) and isinstance(expr.slice, ast.Constant):
        n = f"{expr.value.id}['{expr.slice.value}']"
        if n not in binds or n in seen:
            break
        seen.add(n)
        expr, name = binds[n].value, n
    return expr, name


def descend(expr, path, binds, name):
    """The call at path below expr, following names into their own statements: (expr, statement name)."""
    expr, name = follow(expr, binds, name)
    for k in path:
        ps = parts_of(expr)
        if ps is None or k >= len(ps):
            return None, name
        expr, name = follow(ps[k][0], binds, name)
    return expr, name


def rewrite(H, f, ch, path, node, new):
    """(new source text, the name written, the call's new text) or (None, why, None)."""
    src = SRC.read_bytes()
    tree = ast.parse(src)
    binds = bindings(tree)
    names = [f"{n}['{k}']" for n in ('K', 'L', 'C', 'ZHS') for k, v in getattr(H, n).items() if v is node]
    cands = [(n, binds[n].value) for n in names if n in binds]
    tops = [f"{'ZHS' if f == 'S' else 'C'}['{ch}']"]
    if f == 'S':
        tops.append(f"C['{ch}']")          # a mainland form built from Taiwan's by _mainland
    for t in tops:
        if t in binds:
            call, n = descend(binds[t].value, path, binds, t)
            cands.append((n, call))
    seg = lambda e: ast.get_source_segment(src.decode('utf-8'), e)
    why = []
    for name, call in cands:
        ps = parts_of(call)
        if ps is None or len(ps) != len(new[1]):
            why.append(f'{name}: not a box() or lr() call of {len(new[1])} parts')
            continue
        items = []
        for k, (p, r, default) in enumerate(ps):
            want = new[1][k][1]
            if tuple(node[1][k][1]) == tuple(want):
                items.append(f'({seg(p)}, {seg(r) if r is not None else default})')
            else:
                items.append(f'({seg(p)}, ({", ".join(map(str, want))}))')
        text = 'box(' + ', '.join(items) + ')'
        lines = src.split(b'\n')
        starts = [0]
        for line in lines:
            starts.append(starts[-1] + len(line) + 1)
        a = starts[call.lineno - 1] + call.col_offset
        b = starts[call.end_lineno - 1] + call.end_col_offset
        return (src[:a] + text.encode('utf-8') + src[b:]).decode('utf-8'), name, text
    return None, '; '.join(why) or 'no statement defines this box', None


# ---- probing a tree: the drawings of every form, and the measures of some

def _probe_init(tmp):
    if tmp:
        sys.path.insert(0, tmp)


def _probe_one(job):
    """(key, apart, near, openings, cut fonts) for one form, in this process's hanzi_strokes."""
    f, ch = job
    H = _repo.load()
    import numpy as np
    import build
    import hz_holes
    import hz_ink
    g = hz_ink.work(('', [(f, ch)]))[f, ch]
    holes = hz_holes.measure([(f, ch)]).get(f + ch, {})
    cut = []
    for style in PENS:
        for bold in (False, True):
            st = build.STYLES[style](bold=bold)
            e = np.asarray(st.draw(ch, build.canvas(st, ch), int(f == 'S')))
            if e[:2].any() or e[-2:].any() or e[:, :2].any() or e[:, -2:].any():
                cut.append(f'{style}-{"bold" if bold else "regular"}')
    enc = lambda d: [[list(p), list(q), list(v)] for (p, q), v in d.items()]
    return f + ch, enc(g[1]), enc(g[2]), holes, cut


def probe_main(tmp, what, jobs):
    """Run in a fresh interpreter: tmp (a folder holding a changed hanzi_strokes.py) first on the path."""
    _probe_init(tmp)
    H = _repo.load()
    import hanzi
    if what == 'drawings':
        out = {}
        for f, t in (('C', H.C), ('S', H.ZHS)):
            for c, item in t.items():
                try:
                    out[f + c] = repr(hanzi.flatten(item))
                except Exception as x:          # noqa: BLE001  (a part that doesn't draw is still a change)
                    out[f + c] = 'error ' + repr(x)
        return out
    keys = [(k[0], k[1:]) for k in json.loads(what)]
    with ProcessPoolExecutor(max(1, min(jobs, len(keys))), initializer=_probe_init, initargs=(tmp,)) as ex:
        return {k: [a, n, h, c] for k, a, n, h, c in ex.map(_probe_one, keys)}


def probe(tmp, what, jobs):
    r = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--probe', tmp or '', what, '--jobs', str(jobs)],
                       capture_output=True, text=True, cwd=_repo.ROOT, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    if r.returncode:
        raise RuntimeError(r.stderr.strip().splitlines()[-1] if r.stderr.strip() else 'probe failed')
    return json.loads(r.stdout)


def dec(rows):
    return {(tuple(p), tuple(q)): tuple(v) for p, q, v in rows}


def verify(text, f, ch, path, win, skip, pairs, was_target, jobs, old_drawings):
    """Write text to a copy and measure every form it changes against what it was. (changed keys, [problems])."""
    import hz_holes
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / 'hanzi_strokes.py').write_text(text, encoding='utf-8')
        try:
            now = probe(tmp, 'drawings', jobs)
        except RuntimeError as x:
            return [], [f'the rewritten source fails: {x}']
        changed = sorted(k for k in set(now) | set(old_drawings) if now.get(k) != old_drawings.get(k))
        mine = f + ch
        if mine not in changed:
            return changed, ['the rewrite did not change this form']
        need = [k for k in changed if k not in OLD]
        if need:
            OLD.update(probe(None, json.dumps(need), jobs))
        a = OLD
        b = probe(tmp, json.dumps(changed), jobs)
    bad = []
    for k in changed:
        if k not in a or k not in b:
            bad.append(f'{k}: new or gone')
            continue
        (a0, a1, ah, ac), (b0, b1, bh, bc) = a[k], b[k]
        base, got = (dec(a0), dec(a1)), (dec(b0), dec(b1))
        if k == mine:
            left = tuple(map(sum, zip(*(between({**got[0], **got[1]}, *pq) for pq in pairs)))) if pairs else (0, 0, 0)
            if any(w == 0 and v > 0 for w, v in zip(was_target, left)):
                bad.append(f'{k}: the pair joins in a pen it was clear in ({pen_ink(left)})')
        r = rose(base, got, skip if k == mine else frozenset())
        if r:
            bad.append(f'{k}: ' + '; '.join(r[:3]))
        for part in ah:
            if part in bh:
                w = hz_holes.worse(ah[part], bh[part])
                if w:
                    bad.append(f'{k}: openings of {part} worse {w}')
        new_cut = [c for c in bc if c not in ac]
        if new_cut:
            bad.append(f'{k}: cut in {", ".join(new_cut)}')
    return changed, bad


def openings_one(f, ch, path, new):
    import hz_holes
    H = _repo.load()
    t = table(H, f)
    old = t[ch]
    if new is not None:
        t[ch] = swapped(old, node_at(old, path)[0], new)
    try:
        return hz_holes.measure([(f, ch)]).get(f + ch, {})
    finally:
        t[ch] = old


def cut_one(f, ch, path, new):
    H = _repo.load()
    import numpy as np
    import build
    t = table(H, f)
    old = t[ch]
    t[ch] = swapped(old, node_at(old, path)[0], new)
    bad = []
    try:
        for style in PENS:
            for bold in (False, True):
                st = build.STYLES[style](bold=bold)
                e = np.asarray(st.draw(ch, build.canvas(st, ch), int(f == 'S')))
                if e[:2].any() or e[-2:].any() or e[:, :2].any() or e[:, -2:].any():
                    bad.append(f'{style}-{"bold" if bold else "regular"}')
    finally:
        t[ch] = old
    return bad


def group(text, n, what):
    try:
        ks = [int(x) for x in text.split('+')]
    except ValueError:
        raise SystemExit(f'{what}: {text!r} is not part numbers joined by +')
    if any(not 0 <= k < n for k in ks):
        raise SystemExit(f'{what}: parts are 0 to {n - 1}')
    return ks


def sides(text, n, what):
    s = text.split(',')
    if len(s) != 2:
        raise SystemExit(f'{what}: two sides, as 0,1 or 0,1+2')
    I, J = group(s[0], n, what), group(s[1], n, what)
    if set(I) & set(J):
        raise SystemExit(f'{what}: a part on both sides')
    return I, J


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('form', help='a character (Taiwan or shared form), or S:char for the mainland form')
    ap.add_argument('--node', default='', help='the box to work in: indices from the top, e.g. 1 or 1,0 (default the top)')
    ap.add_argument('--pair', help='the parts of that box to move apart, the upper (or left) first: 0,1, or 0,1+2 to move 1 and 2 together off 0')
    ap.add_argument('--axis', choices=('y', 'x'), default='y', help='y: the first stands above the second; x: to its left')
    ap.add_argument('--allow', help='parts whose ink may rise, to be moved apart next: 1+2,3')
    ap.add_argument('--steps', default='0,20,40,60', help='the moves to try at each edge (units of the box worked in)')
    ap.add_argument('--limit', type=int, default=60, help='ink left between the two, summed over the pens, that counts as clear')
    ap.add_argument('--tries', type=int, default=6, help='moves to check in every form they change, at most (each takes a minute or more)')
    ap.add_argument('--no-shift', action='store_true', help='only shrink, never move a whole rect')
    ap.add_argument('--write', action='store_true', help='write the winning move into hanzi_strokes.py')
    ap.add_argument('--jobs', type=int, default=max(1, (os.cpu_count() or 2) - 2))
    if len(sys.argv) > 1 and sys.argv[1] == '--probe':
        jobs = int(sys.argv[sys.argv.index('--jobs') + 1]) if '--jobs' in sys.argv else 4
        print(json.dumps(probe_main(sys.argv[2], sys.argv[3], jobs)))
        return
    a = ap.parse_args()

    f, ch = form_of(a.form)
    H = _repo.load()
    import hz_holes
    if ch not in table(H, f):
        raise SystemExit(f'{a.form}: not drawn' + (f'; the mainland draws the shared form, name {ch}' if f == 'S' and ch in H.C else ''))
    try:
        path = [int(x) for x in a.node.split(',') if x != '']
    except ValueError:
        raise SystemExit(f'--node {a.node!r}: part numbers joined by commas')
    item = table(H, f)[ch]
    node, lo = node_at(item, path)
    rs = ranges(node, lo)
    base = measure((f, ch, path, None))
    flat = {**base[0], **base[1]}

    if not a.pair:
        print(f'{a.form}: parts of the box at [{a.node}] (strokes, rect)')
        for k, ((x, y), (_, r)) in enumerate(zip(rs, node[1])):
            print(f'  {k}: strokes {x + 1}-{y}  {r}')
        print('ink between parts, per bold pen:')
        rows = sorted(((sum(between(flat, rs[p], rs[q])), p, q) for p, q in itertools.combinations(range(len(rs)), 2)), reverse=True)
        for tot, p, q in rows:
            print(f'  {p},{q}: {tot:6}  ({pen_ink(between(flat, rs[p], rs[q]))})')
        print(f'  other pairs in the form: {sum(sum(v) for v in flat.values()) - sum(r[0] for r in rows)}')
        return

    I, J = sides(a.pair, len(rs), '--pair')
    axis = a.axis
    lo_edge, hi_edge = (1, 3) if axis == 'y' else (0, 2)
    pairs = [(rs[p], rs[q]) for p in I for q in J]
    skip = set(pairs) | {pq[::-1] for pq in pairs}
    if a.allow:
        P, Q = sides(a.allow, len(rs), '--allow')
        skip |= {(rs[p], rs[q]) for p in P for q in Q} | {(rs[q], rs[p]) for p in P for q in Q}

    def gap(m):
        both = {**m[0], **m[1]}
        return tuple(map(sum, zip(*(between(both, *pq) for pq in pairs))))
    was = gap(base)
    name = lambda ks: '+'.join(f'{k} {node[1][k][1]}' for k in ks)
    print(f'{a.form}: {name(I)} then {name(J)} along {axis}; ink between: {sum(was)} ({pen_ink(was)})')
    if sum(was) <= a.limit:
        print('already clear')
        return
    try:
        steps = sorted({int(x) for x in a.steps.split(',')})
    except ValueError:
        raise SystemExit('--steps: numbers joined by commas')
    modes = ('shrink',) if a.no_shift else ('shrink', 'shift')
    full = lambda r: r[hi_edge] - r[lo_edge] >= 1000       # drawn on the full grid (or shifted off it before)
    tries = []
    for d, e in itertools.product(steps, steps):
        if d == e == 0:
            continue
        for di in (modes if d else ('shrink',)):
            for dj in (modes if e else ('shrink',)):
                ri = [node[1][k][1] for k in I]
                rj = [node[1][k][1] for k in J]
                # a shift stays on the grid, but for a part drawn on the full grid (宀), which moves no other way
                if di == 'shift' and any(r[lo_edge] - d < 0 and not full(r) for r in ri):
                    continue
                if dj == 'shift' and any(r[hi_edge] + e > 1000 and not full(r) for r in rj):
                    continue
                # a shrink leaves the part at least 100 units
                if di == 'shrink' and any(r[hi_edge] - d < r[lo_edge] + 100 for r in ri):
                    continue
                if dj == 'shrink' and any(r[lo_edge] + e > r[hi_edge] - 100 for r in rj):
                    continue
                tries.append((d + e, max(d, e), (di == 'shrink') + (dj == 'shrink'), d, e, di, dj))
    tries.sort()
    nodes = [moved(node, I, J, axis, d, e, di, dj) for *_, d, e, di, dj in tries]
    with ProcessPoolExecutor(a.jobs) as ex:
        got = list(ex.map(measure, [(f, ch, path, n) for n in nodes]))

    old_drawings = h0 = None
    checks = 0
    win = why_not = None
    tried = {}
    for t, n, m in zip(tries, nodes, got):
        *_, d, e, di, dj = t
        left = gap(m)
        tag = f'{d:3} {di:6} / {e:3} {dj:6}: between {sum(left):6} ({pen_ink(left)})'
        if sum(left) > a.limit:
            continue
        if any(w == 0 and v > 0 for w, v in zip(was, left)):
            tried[t] = 'joins in a pen it was clear in'
            continue
        r = rose(base, m, skip)
        if r:
            tried[t] = 'rises: ' + '; '.join(r[:3])
            continue
        # the form itself first, in memory: openings and edges
        if h0 is None:
            h0 = openings_one(f, ch, path, None)
        h1 = openings_one(f, ch, path, n)
        lost = [(k, hz_holes.worse(h0[k], h1[k])) for k in h0 if k in h1]
        lost = [f'openings of {k} worse {w}' for k, w in lost if w]
        c = cut_one(f, ch, path, n)
        if lost or c:
            tried[t] = '; '.join(lost + ([f'cut in {", ".join(c)}'] if c else []))
            print(f'  {tag}  {tried[t]}')
            continue
        text, written, call = rewrite(H, f, ch, path, node, n)
        if text is None:
            print(f'  {tag}  clear in this form; openings and edges pass (no other form checked)')
            win, why_not = n, written
            break
        if checks >= a.tries:
            tried[t] = f'not checked in the forms it changes (--tries {a.tries} spent)'
            continue
        checks += 1
        if old_drawings is None:
            old_drawings = probe(None, 'drawings', a.jobs)
        changed, bad = verify(text, f, ch, path, n, skip, pairs, was, a.jobs, old_drawings)
        if bad:
            tried[t] = '; '.join(bad[:4])
            print(f'  {tag}  {tried[t]}')
            continue
        others = [k for k in changed if k != f + ch]
        print(f'  {tag}  clear; ink, openings and edges pass in every form it changes')
        if others:
            print('  it also redraws (measured above): ' + ' '.join(k[1:] + ('(S)' if k[0] == 'S' else '') for k in others))
        win = n
        break

    if win is None:
        print(f'no move in --steps {a.steps} clears it within --limit {a.limit}; the nearest:')
        for t, m in sorted(zip(tries, got), key=lambda tg: (sum(gap(tg[1])), tg[0]))[:5]:
            *_, d, e, di, dj = t
            print(f'  {d:3} {di:6} / {e:3} {dj:6}: between {sum(gap(m)):6} ({pen_ink(gap(m))})'
                  + (f'  {tried[t]}' if t in tried else ''))
        sys.exit(1)
    print('new rects: ' + ', '.join(f'part {k} {win[1][k][1]}' for k in I + J))
    if why_not is not None:
        print(f'not written: {why_not}' if a.write else f'--write would refuse: {why_not}')
        sys.exit(1 if a.write else 0)
    if a.write:
        SRC.write_text(text, encoding='utf-8')
        print(f'{written}: {call}')


if __name__ == '__main__':
    main()
