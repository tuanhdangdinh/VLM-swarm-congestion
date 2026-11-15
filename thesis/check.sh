#!/usr/bin/env bash
# Thesis checks: compile, TODO/VERIFY counts, path leaks, ev/evidence cross-check, citation keys.
cd "$(dirname "$0")/.." || exit 1
T=${THESIS_DIR:-thesis}
fail=0

echo "== (0) source globs"
for g in "$T/chapters/*.typ" "$T/short/*.typ" "$T/evidence/*.typ"; do
  n=$(ls $g 2>/dev/null | wc -l | tr -d ' ')
  if [ "$n" -eq 0 ]; then echo "FAIL: glob $g matches 0 files"; fail=1; else echo "$g: $n files"; fi
done
[ $fail -eq 1 ] && { echo "CHECKS FAILED"; exit 1; }

echo "== (a) compile"
if typst compile $T/main.typ $T/main.pdf; then echo "compile OK"; else echo "FAIL: compile"; fail=1; fi
if typst compile $T/extended.typ $T/extended.pdf; then echo "extended compile OK"; else echo "FAIL: extended compile"; fail=1; fi

echo "== (b) held items per chapter"
total_todo=0; total_verify=0
for f in $T/chapters/*.typ $T/short/*.typ; do
  t=$(grep -o '#todo' "$f" | wc -l | tr -d ' ')
  v=$(grep -o '\[VERIFY\]' "$f" | wc -l | tr -d ' ')
  printf '%-45s todo=%s verify=%s\n' "$(basename "$f")" "$t" "$v"
  total_todo=$((total_todo + t)); total_verify=$((total_verify + v))
done
for f in $T/evidence/*.typ; do
  v=$(grep -o '\[VERIFY\]' "$f" | wc -l | tr -d ' ')
  [ "$v" -gt 0 ] && printf '%-45s verify=%s\n' "evidence/$(basename "$f")" "$v"
  total_verify=$((total_verify + v))
done
echo "TOTAL todo=$total_todo verify=$total_verify (verify includes evidence rows)"

echo "== (c) paths in chapter text"
if grep -nE 'docs/|data/|\.md\b|\.json\b|worktree|vgu-vlm-swarm-' $T/chapters/*.typ $T/short/*.typ; then
  echo "FAIL: repo paths in chapters"; fail=1
else echo "none"; fi

echo "== (d) ev vs evidence ids"
# Multi-line safe: flatten each file to one line, then match calls with or without "#" and "id:".
ids() {
  local calls=$1; shift
  for f in "$@"; do tr '\n' ' ' < "$f"; echo; done \
    | grep -oE "(^|[^A-Za-z0-9_-])$calls\([[:space:]]*(id:[[:space:]]*)?\"[^\"]+\"" \
    | sed -E 's/^[^"]*"//; s/"$//' | sort -u
}
used=$(ids '(ev|fig-source)' $T/chapters/*.typ $T/short/*.typ)
short_used=$(ids '(ev|fig-source)' $T/short/*.typ)
defd=$(ids 'evidence' $T/evidence/*.typ)
missing=$(comm -23 <(echo "$used" | sed '/^$/d') <(echo "$defd" | sed '/^$/d'))
unused=$(comm -13 <(echo "$used" | sed '/^$/d') <(echo "$defd" | sed '/^$/d'))
[ -n "$missing" ] && { echo "FAIL: used but not defined:"; echo "$missing"; fail=1; }
smissing=$(comm -23 <(echo "$short_used" | sed '/^$/d') <(echo "$defd" | sed '/^$/d'))
[ -n "$smissing" ] && { echo "FAIL: condensed report uses undefined ids:"; echo "$smissing"; fail=1; }
[ -n "$unused" ] && { echo "FAIL: defined but never used:"; echo "$unused"; fail=1; }
echo "used=$(echo "$used" | sed '/^$/d' | wc -l | tr -d ' ') defined=$(echo "$defd" | sed '/^$/d' | wc -l | tr -d ' ')"

echo "== (e) citation keys"
keys=$( { grep -ohE '@[A-Za-z][A-Za-z0-9_:.-]*[A-Za-z0-9_]' $T/chapters/*.typ $T/short/*.typ | sed 's/^@//'; \
          grep -ohE 'cite\(<[^>]+>' $T/chapters/*.typ $T/short/*.typ | sed -E 's/^cite\(<//; s/>$//'; } \
        | grep -vE '^(fig|tab|sec|eq|app):' | sort -u)
bad=0
for k in $keys; do
  grep -qE "^@[A-Za-z]+\{$k," $T/bibliography/refs.bib || { echo "FAIL: missing key $k"; bad=1; }
done
[ $bad -eq 1 ] && fail=1
echo "keys=$(echo "$keys" | sed '/^$/d' | wc -l | tr -d ' ')"

[ $fail -eq 0 ] && echo "ALL CHECKS PASSED" || echo "CHECKS FAILED"
exit $fail
