#!/bin/bash
# Lint the Zettelkasten for common issues
# Usage: asf/scripts/lint.sh (from the Kasten root)

set -e

# The content areas: every top-level folder with a README.md hub. The template's
# own folders and the meta folders are never areas, so the same script lints every
# Kasten without a list of its areas.
areas() {
  local dir
  for dir in */; do
    dir=${dir%/}
    case "$dir" in
      asf|docs|inbox|memory|templates|scripts) continue ;;
    esac
    [ -f "$dir/README.md" ] && echo "$dir"
  done
  return 0
}
mapfile -t AREAS < <(areas)

ERRORS=0
WARNINGS=0

# Every note file of the content areas, hubs included.
area_files() {
  local dir
  for dir in "${AREAS[@]}"; do
    find "$dir" -maxdepth 1 -name '*.md' -type f
  done | sort
}

# Files whose links are checked: every area note plus the root README.
link_files() {
  area_files
  echo README.md
}

echo "🔍 Linting Zettelkasten..."
echo ""

# 1. Check for notes without frontmatter
echo "--- Frontmatter Check ---"
while read -r f; do
  [ -n "$f" ] || continue
  if ! head -1 "$f" | grep -q '^---$'; then
    echo "  ❌ Missing frontmatter: $f"
    ERRORS=$((ERRORS + 1))
  fi
done <<< "$(area_files)"

# 2. Check links: relative Markdown links must resolve, wiki-links are not allowed.
#    External URLs and bare anchors are skipped, an anchor on a target is cut off;
#    embeds (`![[…]]`) are examples in the text, not links.
echo "--- Broken Links ---"
while read -r f; do
  [ -n "$f" ] || continue
  while read -r link; do
    [ -n "$link" ] || continue
    echo "  ❌ Wiki-Link in $f → [[$link]] — use relative Markdown links"
    ERRORS=$((ERRORS + 1))
  done <<< "$(grep -oP '(?<!!)\[\[\K[^\]]+(?=\]\])' "$f" 2>/dev/null)"
  dir=$(dirname "$f")
  while read -r target; do
    [ -n "$target" ] || continue
    case "$target" in
      http://*|https://*|mailto:*|\#*) continue ;;
    esac
    if [ ! -e "$dir/${target%%#*}" ]; then
      echo "  ❌ Broken link in $f → $target"
      ERRORS=$((ERRORS + 1))
    fi
  done <<< "$(grep -oP '\]\(\K[^)\s]+(?=\))' "$f" 2>/dev/null)"
done <<< "$(link_files)"

# 3. Check for orphaned notes (no incoming links) — in every area, not only the
#    core: an area note that its hub does not list is exactly the case to catch.
#    Same here-string pattern as the link check, so the counter survives the loop.
echo "--- Orphan Check ---"
while read -r f; do
  [ -n "$f" ] || continue
  # Hubs are entry points, not linked notes
  [ "$(basename "$f")" = "README.md" ] && continue
  basename=$(basename "$f" .md)
  # Incoming links: relative Markdown links, with or without a path or an anchor
  incoming=$(grep -rlE "\]\(([^)]*/)?$basename\.md(#[^)]*)?\)" "${AREAS[@]}" 2>/dev/null | grep -v "^$f$" | wc -l)
  if [ "$incoming" -eq 0 ]; then
    echo "  ⚠️  Orphaned (no incoming links): $f"
    WARNINGS=$((WARNINGS + 1))
  fi
done <<< "$(area_files)"

# 4. Check for empty notes
echo "--- Empty Notes ---"
for f in learnings/*.md literature/*.md; do
  [ -f "$f" ] || continue
  # Count non-frontmatter, non-template lines. The hub back-link comes from the
  # template too, so it does not count as content; neither do the continuation
  # lines of a multi-line template comment.
  content=$(sed '/^---$/,/^---$/d' "$f" | sed '/^<!--/,/-->$/d' | sed '/^#/d' | sed '/^\[← .*\](README\.md)$/d' | sed '/^$/d' | wc -l)
  if [ "$content" -eq 0 ]; then
    echo "  ⚠️  Empty note (only template): $f"
    WARNINGS=$((WARNINGS + 1))
  fi
done

# 5. Tag consistency
echo "--- Tag Report ---"
echo "  All tags in use:"
area_files | tr '\n' '\0' | xargs -0 grep -hoP 'tags: \[([^\]]*)\]' 2>/dev/null \
  | sed 's/tags: \[//;s/\]//' | tr ',' '\n' | sed 's/^ *//;s/ *$//' \
  | sort | uniq -c | sort -rn | while read -r count tag; do
    [ -z "$tag" ] && continue
    echo "    $count × $tag"
  done

echo ""
echo "Done: $ERRORS errors, $WARNINGS warnings"
