"""tools/hz_forms.py [--batch A.py,B.py]

Checks that each character is drawn in its own script's form of the parts
Taiwan and the mainland write differently (hanzi_strokes._TW_PARTS: 艹 as
十十 or 一 across, 敖 with or without the 點, 戶 or 户, 阝 in three strokes or two):

- a character both scripts write (shared) that uses a Taiwan part has a ZHS
  form, and that form is the drawing with the mainland's parts;
- a Simplified-only character uses no Taiwan part;
- a character Taiwan writes holds no mainland part in its default drawing
  (獾 once took the mainland's 雚, so Traditional text got it too).

A pair in _TW_PARTS is a part every character writes differently. Where only
one character does (釉's side, 蚤's top), pair that character's own part, not
the part its family shares: 番 and 杈 hold 釆 and 叉 in both scripts.

Which script has a character: hanzi_order.tsv's columns, and Unihan's kTGH
(in 通用规范汉字表 at any level, so the mainland writes it too: 著 and 藉 sit
in the Traditional column of 着's and 借's rows) when work/unihan is there.
Exits 1 on any problem; check_fonts.py runs it, and merge_round.py with the
round's batches. A batch's shared character can't have its ZHS form yet (that
is made from _SHARED_TW when hanzi_strokes loads, before the batch runs), so
with --batch those are listed to add after the merge, not failed.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _repo

ap = argparse.ArgumentParser()
ap.add_argument('--batch', default='')
a = ap.parse_args()
h = _repo.load(a.batch)
from hanzi import flatten  # noqa: E402  (after the batches are in)

simp, trad = set(), set()
for r in _repo.rows():
    simp.update(c for c in r[2] if c != '-')
    trad.update(c for c in r[3] if c != '-')

# Past the rows: in 通用规范汉字表 means the mainland writes it too.
common = subprocess.check_output(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                                 cwd=_repo.ROOT, text=True).strip()
places = [Path(p) for p in (os.environ.get('UNIHAN'),) if p] + [_repo.ROOT / 'work/unihan', Path(common).parent / 'work/unihan']
unihan = next((p for p in places if (p / 'Unihan_OtherMappings.txt').exists()), None)
tgh = set()
if unihan:
    for line in open(unihan / 'Unihan_OtherMappings.txt', encoding='utf-8'):
        p = line.split('\t')
        if len(p) == 3 and p[1] == 'kTGH':
            tgh.add(chr(int(p[0][2:], 16)))


def han(c):
    return len(c) == 1 and ('㐀' <= c <= '鿿' or '\U00020000' <= c <= '\U0003ffff')


cn = {id(h.K[c]): c for t, c in h._TW_PARTS if c in h.K and t in h.K and h.K[c] is not h.K[t]}


def mainland_parts(x, out):
    if id(x) in cn:
        out.add(cn[id(x)])
    if isinstance(x, tuple) and x and x[0] == 'box':
        for p, _ in x[1]:
            mainland_parts(p, out)
    elif isinstance(x, tuple) and x and x[0] in ('lr', 'tb'):
        mainland_parts(x[1], out)
        mainland_parts(x[2], out)
    return out


bad, owed = [], []
for ch, v in h.C.items():
    if not han(ch):
        continue
    in_simp = ch in simp or ch in tgh   # 著 藉 are Traditional on their rows, and the mainland's too
    in_trad = ch in trad or ch not in simp
    if in_trad and mainland_parts(v, set()):
        bad.append(f"{ch} is Taiwan's too but draws the mainland's {' '.join(sorted(mainland_parts(v, set())))}")
    mainland = flatten(h._mainland(v))
    if mainland == flatten(v):
        continue                       # no Taiwan part
    if in_simp and not in_trad:
        bad.append(f'{ch} is Simplified only but draws a Taiwan part')
    elif in_simp:
        if ch not in h.ZHS and a.batch:
            owed.append(ch)
        elif ch not in h.ZHS:
            bad.append(f'{ch} is shared and has a Taiwan part, but no ZHS form')
        elif flatten(h.ZHS[ch]) != mainland:
            bad.append(f"{ch}'s ZHS form is not its drawing with the mainland's parts")
print(f'  {len(bad)} problems' + (': ' + '; '.join(bad) if bad else ''))
if owed:
    print("  shared, with a Taiwan part: after merging, add to _SHARED_TW: " + ''.join(owed))
sys.exit(1 if bad else 0)
