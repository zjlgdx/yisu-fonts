"""python tools/merge_round.py ROWS VERSION BATCH.py [BATCH.py ...]

Merges a round: puts the batches into hanzi_strokes.py (before the mainland
block), sets VERSION in build.py, and updates the README's counts for the
first ROWS rows of hanzi_order.tsv. Run it in the checkout that gets the round.
"""
import os
import re
import subprocess
import sys
from pathlib import Path
import _repo

R = _repo.ROOT
rows, version, batches = int(sys.argv[1]), sys.argv[2], sys.argv[3:]

# Big5's count needs Unihan (see order.py). work/ isn't committed, so a new
# worktree has none: look in it, then in the main checkout, or take $UNIHAN.
# Checked before anything is written.
common = subprocess.check_output(['git', 'rev-parse', '--path-format=absolute', '--git-common-dir'], cwd=R, text=True)
places = [Path(p) for p in (os.environ.get('UNIHAN'),) if p] + [R / 'work/unihan', Path(common.strip()).parent / 'work/unihan']
unihan = next((p for p in places if (p / 'Unihan_OtherMappings.txt').exists()), None)
if unihan is None:
    sys.exit('Big5 needs Unihan: put it in work/unihan (see order.py) or set UNIHAN')

hs = R / 'hanzi_strokes.py'
text = hs.read_text(encoding='utf-8')
i = text.index('# Mainland China sets the full-width marks')
add = '\n\n'.join(Path(b).read_text(encoding='utf-8').strip('\n') for b in batches)
# A batch that defines a part or character again would quietly replace the
# one already drawn (0.880 redrew 23 this way): refuse it.
DEF = re.compile(r"^([KCL])\['([^']+)'\]\s*=", re.M)
old = set(DEF.findall(text))
again = [k + "['" + n + "']" for k, n in DEF.findall(add) if (k, n) in old]
names = DEF.findall(add)
again += [k + "['" + n + "'] twice" for k, n in set(names) if names.count((k, n)) > 1]
if again:
    sys.exit('already defined: ' + ' '.join(again) + ' (tools/hz_dupes.py lists them)')
# Each script's own form of every part, before an hour's build finds out.
if subprocess.run([sys.executable, str(Path(__file__).parent / 'hz_forms.py'), '--batch', ','.join(batches)]).returncode:
    sys.exit('fix the forms above first (tools/hz_forms.py --batch ...)')
hs.write_text(text[:i].rstrip('\n') + '\n\n' + add + '\n\n\n' + text[i:], encoding='utf-8')

bp = R / 'build.py'
b, n = re.subn(r'^VERSION = [0-9.]+(\s+#)', f'VERSION = {version}\\1', bp.read_text(encoding='utf-8'), flags=re.M)
assert n == 1, 'VERSION line not found'
bp.write_text(b, encoding='utf-8')

# Count in a fresh interpreter: hanzi_strokes has just changed on disk. Only the
# rows' own characters count: the README lists apart the ones drawn from past
# the lists.
have = set(subprocess.check_output(
    [sys.executable, '-c', "import hanzi_strokes as h; print(''.join(h.C))"], cwd=R, text=True))
count = sum(c in have for c in _repo.chars_of(1, rows))
order = _repo.rows()
cover = sum(int(r[1]) for r in order[:rows]) / sum(int(r[1]) for r in order) * 100
# Whole percents, but never round up to 100: past 99.5, one decimal.
pct = int(cover + 0.5) if cover < 99.5 else round(cover, 1)

rd = R / 'README.md'
r = rd.read_text(encoding='utf-8')
r, n1 = re.subn(r'every character in the first [0-9,]+ rows of \[`hanzi_order.tsv`\]\(hanzi_order.tsv\): [0-9,]+ in all',
                f'every character in the first {rows} rows of [`hanzi_order.tsv`](hanzi_order.tsv): {count} in all', r)
r, n2 = re.subn(r'The first [0-9,]+ rows are [0-9,]+ characters across both scripts, and cover [0-9.]+% of the corpus.',
                f'The first {rows:,} rows are {count:,} characters across both scripts, and cover {pct}% of the corpus.', r)
# How much of each standard's list is drawn.
targets = subprocess.check_output([sys.executable, '-c', '''
import sys, hanzi_strokes as h, order
have = set(h.C)
moe = order.moe_4808('moe_4808.tsv')[:4808]
lv1 = []
for _, _, s, _, l in (r.rstrip('\\n').split('\\t') for r in open('hanzi_order.tsv', encoding='utf-8') if r[0].isdigit()):
    lv1 += [i.split(':')[0] if ':' in i else s for i in l.split() if i != '-']
assert len(lv1) == 3500, len(lv1)
big5 = order.big5_level_1(sys.argv[1])
import re
lv2 = [c for c, v in order.fields(sys.argv[1], 'Unihan_OtherMappings.txt', 'kTGH').items() if any(3500 < int(i) <= 6500 for i in re.findall(r'2013:(\\d+)', v))]
assert len(lv2) == 3000, len(lv2)
print(sum(c in have for c in moe), sum(c in have for c in lv1), sum(c in have for c in big5), sum(c in have for c in lv2))
''', str(unihan)], cwd=R, text=True).split()
r, n3 = re.subn(r"Drawn so far: [0-9,]+ of Taiwan's 4,808, [0-9,]+ of the first level's 3,500 and [0-9,]+ of Big5's 5,401\.",
                f"Drawn so far: {int(targets[0]):,} of Taiwan's 4,808, {int(targets[1]):,} of the first level's 3,500"
                f" and {int(targets[2]):,} of Big5's 5,401.", r)
r, n5 = re.subn(r"Of the second level's 3,000, [0-9,]+ are drawn so far\.", f"Of the second level's 3,000, {int(targets[3]):,} are drawn so far.", r)
assert n1 == 1 and n2 == 1 and n3 == 1 and n5 == 1, f'README sentences not found ({n1}, {n2}, {n3}, {n5})'
rd.write_text(r, encoding='utf-8')
# The Chinese README gives the same count as the English one.
zh = R / 'README.zh-Hant.md'
z, n4 = re.subn(r'<!-- hanzi -->[0-9,]+<!-- /hanzi -->', f'<!-- hanzi -->{count:,}<!-- /hanzi -->',
                zh.read_text(encoding='utf-8'))
assert n4 == 1, 'README.zh-Hant.md count not found'
zh.write_text(z, encoding='utf-8')
print(f'rows {rows}, version {version}, {count} hanzi, {cover:.2f}% of the corpus, MOE {targets[0]}/4808, level 1 {targets[1]}/3500, Big5 {targets[2]}/5401, level 2 {targets[3]}/3000')
