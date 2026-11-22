"""tools/hz_resolve_shared.py

Resolves hanzi_strokes.py's merge conflicts in the _SHARED_TW lines, after a
round's branch is merged into the next: each side added lines at the same
place. Keeps ours, takes theirs where it extends a line of ours, and stops if
theirs has a line that fits neither (resolve that one by hand). Run it in the
checkout mid-merge, then `git add hanzi_strokes.py` and commit.
"""
import re
import sys
from pathlib import Path

p = Path(__file__).resolve().parent.parent / 'hanzi_strokes.py'
s = p.read_text(encoding='utf-8')


def fix(m):
    ours, theirs, out = m.group(1).split('\n'), m.group(2).split('\n'), []
    for line in ours:
        longer = [t for t in theirs if line.endswith("'") and t.startswith(line[:-1]) and t != line]
        out.append(longer[0] if longer else line)
    for t in theirs:
        if t not in out and not any(o.endswith("'") and t.startswith(o[:-1]) for o in ours):
            sys.exit('not a _SHARED_TW line of ours, resolve by hand: ' + t[:80])
    return '\n'.join(out) + '\n'


s, n = re.subn(r'<<<<<<< [^\n]*\n(.*?)\n=======\n(.*?)\n>>>>>>> [^\n]*\n', fix, s, flags=re.S)
p.write_text(s, encoding='utf-8')
print(f'  {n} resolved')
