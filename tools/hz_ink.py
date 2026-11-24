#!/usr/bin/env python3
"""The gate on ink: parts that stand apart on paper and join under the bold pens.

    tools/hz_ink.py                  exit 1 when a form joins more than the baseline says
    tools/hz_ink.py --chars 辯蔑      only these (what a change touched); fails when none is drawn
    tools/hz_ink.py --accept         write the baseline (tools/hz_ink.tsv); with --chars, only their rows
                                     (it names the forms that join more than the old baseline said)
    tools/hz_ink.py --debt 60        the forms that join most (from the baseline; measured with --chars or --batch)
    tools/hz_ink.py --where 辯蔑      which parts join, in which pen
    tools/hz_ink.py --selftest       seeded joins and clear pairs, and the verdicts; each must be told

hz_gate.py measures centre lines. Two parts 40 apart pass it, and the bold
pens, 30 and more wide, still draw them as one mark: 0.995 and 0.996 each
had a review panel find 堯's three 土, 火火 on 冖, the middle of 辯 on its
right 辛 and 艹 on 罒 this way, after the gate had passed them.

For every node of a drawing (box, lr, tb), each pair of sibling parts whose
centre lines are APART or more from each other is meant to stand apart. In
each of the three bold pens the two are drawn together, with nothing else,
in the whole character's place, pen width and hand, and each alone. The
pair is joined in that pen when ink of the one reaches ink of the other,
cell to touching cell, through the drawing of both. The pens are not sums
of their strokes (印泥 blurs the whole drawing before it cuts it, so two
marks 120 apart can close up though neither alone reaches the other), which
is why the two are drawn together. How much is the ink of that drawing
within REACH of both parts.

Kept per form: its stroke count, and for every such pair the ink between
the two in each pen (0 where they stand clear). Fails, against the baseline:
a form new to the list that joins; a pair that was clear in a pen and joins
there, whatever another pair gained (the pairs are followed by their stroke
numbers, so one parting never pays for another joining); a pair with a
quarter more ink in a pen (and RISE more); a pair that newly stands apart
on paper and joins in ink; a pair that closed to under APART on paper,
also when it was the form's only one. A form redrawn with another stroke
count has its strokes renumbered: the pairs that kept their numbers are
judged as before and the rest by the totals per pen, so look at it. Parts
drawn to meet are not measured here.

It draws every form many times: about half an hour on all cores.
"""
import argparse
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import _repo

BASE = Path(__file__).with_name('hz_ink.tsv')
APART = 25      # centre lines this far apart are two marks on paper
REACH = 3       # cells; ink within this of both parts lies between them
RISE = 15       # cells of ink a pen must gain before a quarter more fails
STYLES = ('yinni', 'huasha', 'louhen')
SEED = '\ufffd'


def siblings(item, lo=0):
    """(strokes, [[(lo, hi) of each sibling part] for every node])."""
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


def apart(item, hanzi, gate):
    """The sibling pairs ((lo, hi), (lo, hi)) that stand APART or more on
    paper, and those that stand nearer."""
    strokes = hanzi.flatten(item)
    out, near = [], set()
    for node in siblings(item)[1]:
        shapes = [gate.shape(strokes[a:b]) for a, b in node]
        for i in range(len(node)):
            for j in range(i + 1, len(node)):
                if shapes[i] and shapes[j]:
                    if gate.pair(shapes[i], shapes[j])[0] >= APART:
                        out.append((node[i], node[j]))
                    else:
                        near.add((node[i], node[j]))
    return out, near


def grow(m, np, n=1):
    """A mask grown by n cells, up, down and sideways."""
    for _ in range(n):
        g = m.copy()
        g[1:] |= m[:-1]
        g[:-1] |= m[1:]
        g[:, 1:] |= m[:, :-1]
        g[:, :-1] |= m[:, 1:]
        m = g
    return m


def reaches(a, b, ink, np):
    """Whether ink of a reaches ink of b, cell to touching cell, through `ink`
    (the two drawn together). White between them, however little, parts them."""
    if (a & b).any():
        return True
    rows, cols = np.flatnonzero(ink.any(1)), np.flatnonzero(ink.any(0))
    if not len(rows):
        return False
    box = (slice(rows[0], rows[-1] + 1), slice(cols[0], cols[-1] + 1))
    ink = ink[box]
    seen, target = a[box] & ink, b[box] & ink
    n = int(seen.sum())
    while n:
        if (seen & target).any():
            return True
        seen = grow(seen, np) & ink
        m = int(seen.sum())
        if m == n:
            return False
        n = m
    return False


def shared(ch, form, pairs, hanzi, build, np):
    """{pair: cells of ink between the two in each pen, 0 where they stand
    clear}. A cell is two grid units square."""
    from unittest.mock import patch
    table = (hanzi.C, hanzi.ZHS)[form]
    whole = hanzi.flatten(table[ch])
    real, width = hanzi.placed, hanzi.density_scale
    cell = max(1, round(2 * build.S))
    out = {pq: [] for pq in pairs}
    for key in STYLES:
        st = build.STYLES[key](bold=True)
        masks = {}

        def mask(*rngs):
            if rngs not in masks:
                drawn = []

                def some(*a, **kw):
                    strokes, warp, r = real(*a, **kw)
                    drawn[:] = strokes
                    return [s for lo, hi in rngs for s in strokes[lo:hi]], warp, r

                def pen(ch, _strokes, *a):
                    # the build's own width: from the whole form as it is placed, strayed strokes and all
                    return width(ch, drawn, *a)
                with patch.object(hanzi, 'placed', some), patch.object(hanzi, 'density_scale', pen):
                    masks[rngs] = np.asarray(st.draw(ch, build.canvas(st, ch), form).reduce(cell)) > 64
            return masks[rngs]
        for p, q in pairs:
            a, b, both = mask(p), mask(q), mask(p, q)
            out[p, q].append(max(1, int(np.count_nonzero(both & grow(a, np, REACH) & grow(b, np, REACH))))
                             if reaches(a, b, both, np) else 0)
    return {pq: tuple(v) for pq, v in out.items()}


def work(job):
    """{(form, ch): (strokes, {pair: ink per pen}, pairs nearer than APART)}
    for every form asked for, also one with no pair meant apart."""
    batch, keys = job
    H = _repo.load(batch)
    import numpy as np
    import build
    import hanzi
    import hz_gate
    out = {}
    for f, ch in keys:
        form = int(f == 'S')
        item = (H.C, H.ZHS)[form][ch]
        pairs, near = apart(item, hanzi, hz_gate)
        out[f, ch] = (len(hanzi.flatten(item)), shared(ch, form, pairs, hanzi, build, np) if pairs else {}, near)
    return out


def survey(batch='', only=None, jobs=None):
    import os
    H = _repo.load(batch)
    import hanzi
    import hz_gate
    keys = [('C', ch) for ch in H.C if hz_gate.is_han(ch) and (only is None or ch in only)]
    keys += [('S', ch) for ch, item in H.ZHS.items() if hz_gate.is_han(ch) and (only is None or ch in only)
             and (ch not in H.C or hanzi.flatten(item) != hanzi.flatten(H.C[ch]))]
    jobs = jobs or max(1, (os.cpu_count() or 2) - 2)
    if len(keys) < 40:
        return work((batch, keys))
    out = {}
    with ProcessPoolExecutor(jobs) as ex:
        for part in ex.map(work, [(batch, keys[i::jobs * 8]) for i in range(jobs * 8)]):
            out.update(part)
    return out


def totals(pairs):
    """(pairs joined in each pen x3, ink between parts in each pen x3)."""
    v = list(pairs.values())
    return tuple(sum(1 for p in v if p[i]) for i in range(3)) + tuple(sum(p[i] for p in v) for i in range(3))


def row(f, ch, n, pairs):
    return '\t'.join([f, ch, str(n)] + [f'{a}-{b}:{c}-{d}={",".join(map(str, v))}'
                                        for ((a, b), (c, d)), v in sorted(pairs.items())])


def read_base():
    base = {}
    if BASE.exists():
        for line in BASE.read_text(encoding='utf-8').splitlines():
            if line and not line.startswith('#'):
                f, ch, n, *cols = line.split('\t')
                pairs = {}
                for col in cols:
                    who, v = col.split('=')
                    p, q = (tuple(int(x) for x in r.split('-')) for r in who.split(':'))
                    pairs[p, q] = tuple(int(x) for x in v.split(','))
                base[f, ch] = (int(n), pairs, set())
    return base


def said(pq):
    (a, b), (c, d) = pq
    return f'strokes {a + 1}-{b} and {c + 1}-{d}'


def judge(now, was):
    """Why this form fails. now and was are (strokes, {pair: ink per pen},
    pairs nearer than APART); was is None when the form is not in the baseline."""
    n, pairs, near = now
    if was is None:
        t = totals(pairs)
        return ('new: joined in ' + ', '.join(f'{k} {j}' for k, j in zip(STYLES, t[:3]) if j)) if any(t[:3]) else None
    same = n == was[0]
    why = []
    for pq, v in sorted(pairs.items()):
        old = was[1].get(pq)
        for i, key in enumerate(STYLES):
            if v[i] and old is None:
                if same:
                    why.append(f'{said(pq)}, apart on paper now, join in {key}')
            elif v[i] and not old[i]:
                why.append(f'{said(pq)} join in {key}')
            elif old is not None and v[i] > old[i] * 1.25 and v[i] - old[i] > RISE:
                why.append(f'{said(pq)} in {key}: ink between {old[i]} -> {v[i]}')
    if same:
        # a pair regrouped into other parts is gone too, but is not in `near`
        for pq in sorted(set(was[1]) & near):
            why.append(f'{said(pq)} are under {APART} apart on paper now')
    else:
        # the strokes were renumbered: pairs that kept their numbers are judged above, the rest by the totals
        t, w = totals(pairs), totals(was[1])
        for i, key in enumerate(STYLES):
            if t[i] > w[i]:
                why.append(f'{key}: pairs joined {w[i]} -> {t[i]}')
            elif t[3 + i] > w[3 + i] * 1.25 and t[3 + i] - w[3 + i] > RISE:
                why.append(f'{key}: ink between parts {w[3 + i]} -> {t[3 + i]}')
    return '; '.join(why) or None


def selftest():
    H = _repo.load()
    import numpy as np
    import hanzi
    full = (0, 0, 1000, 1000)
    bad = 0

    def check(label, got, want, shown=''):
        nonlocal bad
        print(f'  {label}: {shown or got}' + ('' if got == want else '  <- WRONG'))
        bad += got != want

    a = np.array([[1, 0, 0]], bool)
    b = a[:, ::-1]
    check('ink with one white cell between', reaches(a, b, a | b, np), False)
    check('ink that only the joint drawing bridges', reaches(a, b, np.ones((1, 3), bool), np), True)
    check('ink that overlaps', reaches(a | b, b, a | b, np), True)

    def measure(item, form='C'):
        (H.ZHS if form == 'S' else H.C)[SEED] = item
        if form == 'S':
            H.C[SEED] = [('E', 'M100 500 L900 500')]
        got = work(('', [(form, SEED)]))[form, SEED]
        H.C.pop(SEED, None)
        H.ZHS.pop(SEED, None)
        return got

    def told(label, item, want, form='C'):
        got = measure(item, form)
        if not got[1]:
            return check(label, 'not measured', 'measured')
        pens = totals(got[1])[:3]
        check(label, all(bool(g) == want for g in pens), True,
              ' '.join(f'{k} {"joined" if g else "apart"}' for k, g in zip(STYLES, pens)))

    def up(x):
        return [('E', f'M{x} 150 L{x} 850')]

    def ups(*xs):
        return ('box', [(up(x), full) for x in xs])
    told('two uprights 40 apart, a box', ups(300, 340), True)
    told('two uprights 300 apart, a box', ups(300, 600), False)
    told('two uprights close, lr', ('lr', up(960), up(60), 0.5), True)
    told('two bars close, tb', ('tb', [('E', 'M150 960 L850 960')], [('E', 'M150 40 L850 40')], 0.5), True)
    told('two uprights 40 apart, nested', ('box', [(ups(300, 340), full), (up(800), full)]), True)
    told('two uprights 40 apart, a mainland form', ups(300, 340), True, 'S')
    assert SEED not in hanzi.C and SEED not in hanzi.ZHS

    def pen(n, ems, bold, family=None, ch='\u4e00'):
        return hanzi.density_scale(ch, [('E', f'M0 0 L{ems * 1000 / n} 0')] * n, bold, family)
    check('pen, a path with lines after its M', round(hanzi.line_length([('E', 'M0 0 300 400 L300 1400 C300 1400 300 2400 300 2400')]), 3), 2.5)
    check('pen, Regular takes no dense rule', pen(15, 6.6, False, 'louhen'), pen(15, 6.6, False))
    check('pen, Bold 畫沙 takes none', pen(15, 6.6, True, 'huasha'), pen(15, 6.6, True))
    check('pen, Bold 鏤痕 narrows with much line', pen(15, 6.6, True, 'louhen') < pen(15, 5.0, True, 'louhen') < 1, True)
    check('pen, the narrower rule wins', pen(24, 4.1, True, 'louhen'), pen(24, 4.1, True))
    check('pen, not Chinese: left alone', pen(15, 6.6, True, 'louhen', 'A'), 1.0)
    check('pen, no step where the dense rule starts', abs(pen(5, 4.001, True, 'louhen') - pen(5, 4.0, True, 'louhen')) < 1e-4, True)
    import build
    from unittest.mock import patch
    ch, seen = '\u5f48', []
    if ch in hanzi.C:
        st = build.STYLES['louhen'](bold=True)
        true = hanzi.density_scale
        with patch.object(hanzi, 'density_scale', lambda *a: [seen.append(v) for v in [true(*a)] if a[-1] == 'louhen'] and seen[-1] or true(*a)):
            st.draw(ch, build.canvas(st, ch), 0)
            work(('', [('C', ch)]))
        check('pen, the gate draws with the build\'s width', len(set(seen)) == 1 and len(seen) > 1, True)
    left, right, wide = measure(ups(300, 340, 800)), measure(ups(300, 760, 800)), measure(ups(180, 500, 900))
    check('verdict, one pair parted and another joined', bool(judge(right, left)), True)
    check('verdict, a clear pair closed to under APART', bool(judge(measure(ups(180, 200, 900)), wide)), True)
    check('verdict, the only pair closed to under APART', bool(judge(measure(ups(180, 200)), measure(ups(180, 500)))), True)
    check('verdict, the same strokes grouped another way', bool(judge(measure(('box', [(ups(180, 500), full), (up(900), full)])), wide)), False)
    check('印泥 closes two uprights 120 apart (only the joint drawing has it)', bool(measure(ups(300, 420))[1][(0, 1), (1, 2)][0]), True)
    P, Q = ((0, 2), (2, 5)), ((2, 5), (5, 7))
    was = (7, {P: (40, 0, 90), Q: (0, 0, 0)}, set())
    for label, now, want in (('the same', was, False), ('nothing joined', (7, {P: (0, 0, 0), Q: (0, 0, 0)}, set()), False),
                             ('the clear pair joins in a pen', (7, {P: (40, 0, 90), Q: (0, 5, 0)}, set()), True),
                             ('one pair parts, the other joins', (7, {P: (0, 0, 0), Q: (40, 0, 90)}, set()), True),
                             ('a quarter more ink in a pen', (7, {P: (40, 0, 130), Q: (0, 0, 0)}, set()), True),
                             ('a little more ink', (7, {P: (44, 0, 95), Q: (0, 0, 0)}, set()), False),
                             ('a pair joins while a stroke is added after it', (8, {P: (0, 0, 0), Q: (40, 0, 90)}, set()), True),
                             ('a new pair that joins', (7, {P: (40, 0, 90), Q: (0, 0, 0), ((0, 2), (5, 7)): (9, 0, 0)}, set()), True),
                             ('redrawn with a stroke more, no worse in all', (8, {((0, 3), (3, 6)): (30, 0, 80)}, set()), False),
                             ('redrawn with a stroke more, a pen worse', (8, {((0, 3), (3, 6)): (30, 4, 80)}, set()), True)):
        check(f'verdict, {label}', bool(judge(now, was)), want)
    check('verdict, a new form that joins', bool(judge((2, {P: (0, 8, 0)}, set()), None)), True)
    check('verdict, a new form that is clear', bool(judge((2, {P: (0, 0, 0)}, set()), None)), False)
    return bad


def name(ch, f):
    return ch + ('(S)' if f == 'S' else '')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', default='')
    ap.add_argument('--chars', default=None)
    ap.add_argument('--accept', action='store_true')
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--debt', type=int, default=0)
    ap.add_argument('--where', default='')
    ap.add_argument('--jobs', type=int, default=0)
    a = ap.parse_args()
    if a.selftest:
        sys.exit(1 if selftest() else 0)
    if a.where:
        got = survey(a.batch, set(a.where))
        if not got:
            sys.exit('none of these is drawn')
        for (f, ch), (n, pairs, _) in sorted(got.items(), key=lambda kv: a.where.index(kv[0][1])):
            t = totals(pairs)
            print(f'{name(ch, f)}: {sum(t[:3])} joined' if any(t[:3]) else f'{name(ch, f)}: nothing joined')
            for pq, v in sorted(pairs.items()):
                for key, cells in zip(STYLES, v):
                    if cells:
                        print(f'   {key} bold: {said(pq)} of {n}, {cells} cells of ink between')
        return
    if a.accept and a.batch:
        sys.exit('--accept is for what is merged: run it without --batch')
    measured = a.chars is not None or bool(a.batch) or a.accept or not a.debt
    now = survey(a.batch, set(a.chars) if a.chars is not None else None, a.jobs) if measured else read_base()
    if a.chars is not None and not now:
        sys.exit('--chars: none of these is drawn (an empty or mangled list?)')
    if a.accept:
        rows = dict(now) if a.chars is None else {**{k: v for k, v in read_base().items() if k[1] not in a.chars}, **now}
        rows = {k: v for k, v in rows.items() if v[1]}
        was = read_base()
        worse = [name(ch, f) for (f, ch), m in sorted(now.items()) if judge(m, was.get((f, ch)))]
        if worse:
            print(f'accepted though they join more than the baseline did ({len(worse)}): ' + ''.join(worse))
        BASE.write_text('# tools/hz_ink.py --accept. form (C Taiwan/shared, S mainland), character, strokes, then each pair of '
                        'parts meant apart (strokes lo-hi:lo-hi, counted from 0, hi not included) = cells of ink between them in the bold '
                        + ', '.join(STYLES) + ' pens (0: they stand clear)\n'
                        + ''.join(row(f, ch, n, pairs) + '\n' for (f, ch), (n, pairs, _) in sorted(rows.items())), encoding='utf-8')
        joined = sum(1 for _, pairs, _ in rows.values() if any(totals(pairs)[:3]))
        print(f'baseline written: {len(rows)} forms with parts meant apart, {joined} join' + ('' if a.chars is None else f'; {len(now)} measured again'))
        return
    if a.debt:
        worst = sorted(((sum(t[3:]), sum(t[:3]), f, ch) for (f, ch), (_, pairs, _) in now.items()
                        for t in [totals(pairs)] if any(t[:3])), reverse=True)
        print(f'{len(worst)} forms join in a bold pen' + ('' if measured else ' (the baseline)') + f'; the {min(a.debt, len(worst))} with most ink between parts:')
        print('  ' + '  '.join(f'{name(ch, f)} {j}/{p}' for p, j, f, ch in worst[:a.debt]))
        return
    base = read_base()
    fails = [(name(ch, f), why) for (f, ch), m in sorted(now.items()) for why in [judge(m, base.get((f, ch)))] if why]
    better = [name(ch, f) for (f, ch), (_, pairs, _) in sorted(now.items())
              if (f, ch) in base and sum(totals(pairs)[:3]) < sum(totals(base[f, ch][1])[:3])]
    joined = sum(1 for _, pairs, _ in now.values() if any(totals(pairs)[:3]))
    print(f'drawn {len(now)} forms in the three bold pens: {joined} join'
          + (f' ({len(base)} forms in the baseline)' if a.chars is None else ''))
    if better:
        print(f'  join less than the baseline ({len(better)}): ' + ''.join(better[:80]))
    for who, why in fails:
        print(f'FAIL {who}: {why}')
    print(f'{len(fails)} forms join more' if fails else 'no form joins more')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
