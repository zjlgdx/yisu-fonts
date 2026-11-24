#!/bin/bash
# tools/release.sh FIRST LAST [FIX]
#
# After the round's pull request is merged. Run in the checkout that built the
# fonts (its out/ is what gets attached). Makes the release v$VERSION on main
# with every out/*.otf and out/*.woff2 and their SHA-256 in the notes. Refuses
# if main's VERSION isn't this checkout's, or a font says another version.
set -euo pipefail
FIRST=$1 LAST=$2 FIX=${3:-}
cd "$(dirname "$0")/.."
# a worktree has no .venv of its own: use the main checkout's
PY=${PY:-$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo "$(git rev-parse --path-format=absolute --git-common-dir)/../.venv/bin/python")}
V=$(sed -nE 's/^VERSION = ([0-9.]+).*/\1/p' build.py)
git fetch -q --tags origin main   # the tags too: the notes count from the last release
MV=$(git show origin/main:build.py | sed -nE 's/^VERSION = ([0-9.]+).*/\1/p')
[ "$V" = "$MV" ] || { echo "main is at $MV, this checkout at $V: merge first" >&2; exit 1; }
"$PY" - "$V" <<'EOF'
import sys, glob
from fontTools.ttLib import TTFont
v = float(sys.argv[1])
bad = [f for f in sorted(glob.glob('out/*.otf') + glob.glob('out/*.woff2')) if round(TTFont(f)['head'].fontRevision, 4) != v]
sys.exit(f'built for another version: {bad}' if bad else 0)
EOF
read -r COUNT PCT < <(sed -nE 's/.*The first [0-9,]+ rows are ([0-9,]+) characters across both scripts, and cover ([0-9.]+)% of the corpus.*/\1 \2/p' README.md | tr -d ,)
PREV=$(gh release list --limit 1 --json tagName --jq '.[0].tagName')
BEFORE=$(git show "$PREV:README.md" | sed -nE 's/.*rows are ([0-9,]+) characters across both scripts.*/\1/p' | tr -d ,)
fixline=""
[ -n "$FIX" ] && fixline=$'\n'"- $FIX"
sums=$(cd out && shasum -a 256 *.otf *.woff2)
notes="## Chinese rows ${FIRST}–${LAST}
$((COUNT - BEFORE)) more characters, Simplified and Traditional, in all three families: every character in the first ${LAST} rows of \`hanzi_order.tsv\`, ${COUNT} in all, ${PCT}% of the corpus.${fixline}

**Install:** download the \`.otf\` files for a family (both weights) and open them. The \`.woff2\` files are for the web.

**Licence:** SIL Open Font License 1.1.

## SHA-256
\`\`\`
${sums}
\`\`\`"
gh release create "v${V}" --target main --title "${V} · Chinese rows ${FIRST}–${LAST}" --notes "$notes" out/*.otf out/*.woff2
gh release view "v${V}" --json tagName,assets --jq '.tagName + ": " + (.assets|length|tostring) + " files"'
