"""tools/hz_mainland_parts.py [FIRST_ROW]

The other side of hz_forms.py: lists each character Taiwan writes (the
Traditional column of hanzi_order.tsv, shared ones too) whose default drawing
holds the mainland's form of a part in hanzi_strokes._TW_PARTS. The default
is Taiwan's form; the mainland's belongs in ZHS (via _SHARED_TW).

It only lists: some older characters are deliberate. Read a round's own rows
(FIRST_ROW on) before its pull request.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo

first = int(sys.argv[1]) if len(sys.argv) > 1 else 0
h = _repo.load('')
simp, trad, row = set(), set(), {}
for r in _repo.rows():
    for c in r[2]:
        if c != '-':
            simp.add(c)
    for c in r[3]:
        if c != '-':
            trad.add(c)
            row[c] = int(r[0])
cn = {id(h.K[c]): c for t, c in h._TW_PARTS if c in h.K and t in h.K and h.K[c] is not h.K[t]}


def walk(x, out):
    if id(x) in cn:
        out.add(cn[id(x)])
    if isinstance(x, tuple) and x and x[0] == 'box':
        for p, _ in x[1]:
            walk(p, out)
    elif isinstance(x, tuple) and x and x[0] in ('lr', 'tb'):
        walk(x[1], out)
        walk(x[2], out)


found = []
for ch, v in h.C.items():
    if ch in trad and row[ch] >= first:
        parts = set()
        walk(v, parts)
        if parts:
            found.append((row[ch], ch, 'shared' if ch in simp else 'Traditional', ''.join(sorted(parts))))
for r in sorted(found):
    print(*r)
print(f'  {len(found)} with a mainland part')
