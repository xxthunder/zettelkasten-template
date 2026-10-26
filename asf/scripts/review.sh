#!/bin/bash
# Surface notes for review based on age and link count
# Usage: asf/scripts/review.sh [days_threshold] (from the Kasten root)

set -e

DAYS="${1:-30}"
NOW=$(date +%s)

echo "📋 Zettelkasten Review (notes older than ${DAYS} days or with few links)"
echo ""

echo "--- Stale Notes (not updated in ${DAYS}+ days) ---"
for f in learnings/*.md literature/*.md; do
  [ -f "$f" ] || continue
  # Try to get updated date from frontmatter
  updated=$(grep -m1 '^updated:' "$f" 2>/dev/null | sed 's/updated: *//' | tr -d '"')
  if [ -n "$updated" ]; then
    file_epoch=$(date -d "$updated" +%s 2>/dev/null || stat -c %Y "$f")
  else
    file_epoch=$(stat -c %Y "$f")
  fi
  age_days=$(( (NOW - file_epoch) / 86400 ))
  if [ "$age_days" -ge "$DAYS" ]; then
    title=$(grep -m1 '^title:' "$f" 2>/dev/null | sed 's/title: *//' | tr -d '"')
    echo "  📝 ${title:-$f} (${age_days} days old)"
    echo "     → $f"
  fi
done

echo ""
echo "--- Weakly Connected Notes (0-1 outgoing links) ---"
for f in learnings/*.md; do
  [ -f "$f" ] || continue
  # Outgoing links: relative Markdown links to notes, without the hub back-link and
  # without external URLs. `|| true`, not `|| echo 0`: grep -c prints the 0 itself.
  link_count=$(grep -oP '\]\(\K(?!https?:|mailto:)[^)\s#]+\.md(?=[#)])' "$f" 2>/dev/null | grep -vc 'README\.md$' || true)
  if [ "$link_count" -le 1 ]; then
    title=$(grep -m1 '^title:' "$f" 2>/dev/null | sed 's/title: *//' | tr -d '"')
    echo "  🔗 ${title:-$f} ($link_count links)"
    echo "     → $f"
  fi
done

echo ""
echo "--- Unprocessed Inbox ---"
inbox_count=$(find inbox/ -name '*.md' 2>/dev/null | wc -l)
echo "  📥 $inbox_count notes waiting in inbox"
if [ "$inbox_count" -gt 0 ]; then
  for f in inbox/*.md; do
    [ -f "$f" ] || continue
    echo "     → $f"
  done
fi
