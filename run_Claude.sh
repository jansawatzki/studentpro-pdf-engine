#!/bin/bash
# Run from anywhere: bash run_Claude.sh

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

# Try to find streamlit in common locations
STREAMLIT=""
for candidate in \
    "$HOME/Library/Python/3.9/bin/streamlit" \
    "$HOME/Library/Python/3.10/bin/streamlit" \
    "$HOME/Library/Python/3.11/bin/streamlit" \
    "/usr/local/bin/streamlit" \
    "/opt/homebrew/bin/streamlit" \
    "$(which streamlit 2>/dev/null)"; do
    if [ -f "$candidate" ]; then
        STREAMLIT="$candidate"
        break
    fi
done

if [ -z "$STREAMLIT" ]; then
    echo "streamlit not found. Installing..."
    pip3 install streamlit mistralai supabase python-dotenv
    STREAMLIT="$HOME/Library/Python/3.9/bin/streamlit"
fi

echo "Starting student PRO PDF Engine..."
"$STREAMLIT" run app_Claude.py
