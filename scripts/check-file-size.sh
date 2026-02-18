#!/bin/bash

# Configuration
WARN_LIMIT=600
ERROR_LIMIT=800

# Colors
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if arguments are provided (manual mode), otherwise check staged files
if [ "$#" -gt 0 ]; then
    FILES="$@"
else
    # Get staged files that are not deleted
    FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(js|jsx|ts|tsx)$')
fi

if [ -z "$FILES" ]; then
    exit 0
fi

EXIT_CODE=0

for FILE in $FILES; do
    if [ ! -f "$FILE" ]; then
        continue
    fi

    LINES=$(wc -l < "$FILE" | tr -d ' ')
    
    if [ "$LINES" -gt "$ERROR_LIMIT" ]; then
        echo -e "${RED}ERROR: $FILE has $LINES lines (limit: $ERROR_LIMIT)${NC}"
        EXIT_CODE=1
    elif [ "$LINES" -gt "$WARN_LIMIT" ]; then
        echo -e "${YELLOW}WARNING: $FILE has $LINES lines (limit: $WARN_LIMIT)${NC}"
    fi
done

if [ "$EXIT_CODE" -ne 0 ]; then
    echo -e "${RED}Commit blocked due to file size limits. Please refactor or split large files.${NC}"
fi

exit $EXIT_CODE
