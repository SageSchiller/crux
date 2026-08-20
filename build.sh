#!/usr/bin/env bash
# Build the distributable single file.
#
# Stdlib only: zipapp ships with Python, so this needs nothing installed and
# produces something a stranger can run with `python3 crux.pyz`.
#
# The staging step is not decoration. `crux/` carries its own __main__.py so
# that `python3 -m crux` works from the source tree, and zipapp refuses to take
# an entry point when the source already has one. Staging keeps `crux` a real
# package inside the archive, which the relative imports need, and puts the
# archive's entry point beside it rather than inside it.
set -euo pipefail
cd "$(dirname "$0")"

OUT="${OUT:-dist}"
mkdir -p "$OUT"

stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT

cp -r crux "$stage/crux"
find "$stage" -name '__pycache__' -type d -prune -exec rm -rf {} +
rm -f "$stage/crux/__main__.py"

cat > "$stage/__main__.py" <<'PY'
import sys

from crux.app import run

sys.exit(run())
PY

python3 -m zipapp "$stage" -p '/usr/bin/env python3' -o "$OUT/crux.pyz"
chmod +x "$OUT/crux.pyz"
printf 'built %s (%s bytes)\n' "$OUT/crux.pyz" "$(stat -c%s "$OUT/crux.pyz")"
