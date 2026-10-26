#!/bin/bash
# Create a new learning or literature note from template
# Usage: asf/scripts/new-zettel.sh "My Note Title" [learning|literature] (from the Kasten root)

set -e

TITLE="${1:?Usage: new-zettel.sh 'Title' [learning|literature]}"
TYPE="${2:-learning}"
DATE=$(date +"%Y%m%d%H%M%S")
DATE_ISO=$(date +"%Y-%m-%dT%H:%M:%S")
SLUG=$(echo "$TITLE" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-//' | sed 's/-$//')

case "$TYPE" in
  learning)
    FILENAME="learnings/${DATE}-${SLUG}.md"
    TEMPLATE="asf/templates/learning.md"
    ;;
  literature)
    FILENAME="literature/lit-${SLUG}.md"
    TEMPLATE="asf/templates/literature.md"
    ;;
  *)
    echo "Unknown type: $TYPE (use 'learning' or 'literature')"
    exit 1
    ;;
esac

if [ ! -f "$TEMPLATE" ]; then
  echo "Template not found: $TEMPLATE"
  exit 1
fi

# The templates use Obsidian's placeholder syntax, so the Templates plugin fills them too.
sed -e "s|{{title}}|${TITLE}|g" \
    -e "s|{{date:YYYY-MM-DDTHH:mm:ss}}|${DATE_ISO}|g" \
    "$TEMPLATE" > "$FILENAME"

echo "Created: $FILENAME"
echo "Open and start writing!"
