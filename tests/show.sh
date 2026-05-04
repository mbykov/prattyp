#!/bin/bash
# tests/show.sh — рендерит Typst-формулу из аргумента или буфера обмена
# Использование: ./tests/show.sh 'frac(x, 2)'
#                ./tests/show.sh          (читает из буфера)

set -e

if [ $# -gt 0 ]; then
  INPUT="$1"
else
  INPUT=$(xclip -selection clipboard -o 2>/dev/null || echo "")
  if [ -z "$INPUT" ]; then
    echo "Буфер обмена пуст. Дайте формулу аргументом."
    exit 1
  fi
fi

TMPDIR=$(mktemp -d)

printf '#set page(width: auto, height: auto, margin: 8pt)\n#set text(size: 24pt)\n$ %s $' "$INPUT" | typst compile - --format svg "$TMPDIR/formula.svg"

eog "$TMPDIR/formula.svg"
rm -rf "$TMPDIR"
