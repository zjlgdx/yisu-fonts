#!/bin/bash
# tools/open_pr.sh ISSUE FIRST LAST [FIX]
#
# Run in the round's checkout, after tools/check_fonts.py passes. Pushes the
# branch and opens a pull request on main that closes ISSUE; FIX, if given, is
# one more line for the notes. Prints the pull request's URL. Merging is the
# maintainer's call (AGENTS.md): this script never merges.
set -euo pipefail
ISSUE=$1 FIRST=$2 LAST=$3 FIX=${4:-}
cd "$(dirname "$0")/.."
BR=$(git branch --show-current)
V=$(sed -nE 's/^VERSION = ([0-9.]+).*/\1/p' build.py)
read -r COUNT PCT < <(sed -nE 's/.*The first [0-9,]+ rows are ([0-9,]+) characters across both scripts, and cover ([0-9.]+)% of the corpus.*/\1 \2/p' README.md | tr -d ,)
git fetch -q origin main
# Another branch may have shipped this version while this one was building.
MV=$(git show origin/main:build.py | sed -nE 's/^VERSION = ([0-9.]+).*/\1/p')
if [ -n "$(git ls-remote --tags origin "refs/tags/v$V")" ] || ! python3 -c "import sys; sys.exit(not $V > $MV)"; then
  echo "version $V is taken (main is at $MV, or v$V is tagged): merge origin/main and set a higher VERSION" >&2
  exit 1
fi
BEFORE=$(git show origin/main:README.md | sed -nE 's/.*rows are ([0-9,]+) characters across both scripts.*/\1/p' | tr -d ,)
NEW=$((COUNT - BEFORE))
# A merge forward resolved in a hurry once left its markers in a commit.
if git grep -nE '^(<<<<<<<|>>>>>>>) ' -- '*.py' '*.md' '*.tsv' '*.sh'; then
  echo "conflict markers above: resolve them first" >&2
  exit 1
fi
gitleaks git --no-banner --log-opts="origin/main..HEAD"
git push -q -u origin "$BR"
fixline=""
[ -n "$FIX" ] && fixline=$'\n'"- $FIX"
body="Rows ${FIRST}–${LAST} of \`hanzi_order.tsv\`, in Yisu Yinni, Huasha and Louhen, Simplified and Traditional together.

- Every character in the first ${LAST} rows is drawn: ${COUNT} hanzi in all (${NEW} new), ${PCT}% of the corpus.${fixline}
- Version ${V}. \`tools/edges.py\` and the build report no glyph cut off.
- Checks (\`tools/check_fonts.py\`): OTS passes on all six fonts, \`fontbakery check-universal\` has no FAIL but the known one, \`massive-font\` on fonts past 9 MB (the README says why), and the known warnings (\`file_size\`; Yinni's \`xAvgCharWidth\` and CFF \`glyf\` check), and no personal data.

Closes #${ISSUE}

🤖 Generated with [Claude Code](https://claude.com/claude-code)"
gh pr create --base main --head "$BR" --title "Chinese rows ${FIRST}–${LAST} (${V})" --body "$body"
