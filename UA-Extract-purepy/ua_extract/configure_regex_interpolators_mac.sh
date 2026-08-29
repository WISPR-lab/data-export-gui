#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$SCRIPT_DIR/regexes"

if [ ! -d "$BASE_DIR" ]; then
  echo "Error: $BASE_DIR does not exist"
  exit 1
fi

find "$BASE_DIR" -name "*.yml" -type f -print0 | xargs -0 sed -i '' -E 's/\$([1-5])/\\g<\1>/g'

find "$BASE_DIR" -name "*.yml" -type f -print0 | xargs -0 sed -i '' "s/eZee'Tab\\\\g/eZee'Tab\\\\\\\\g/g"
