#!/bin/bash

# Script to rebuild Atlas browser autocomplete cache
# Run this after importing history to make omnibar suggestions work properly

ATLAS_DEFAULT="/Users/joshuapham/Library/Application Support/com.openai.atlas/browser-data/host/Default"

echo "Atlas Autocomplete Cache Rebuilder"
echo "===================================="
echo ""
echo "This will clear Atlas's autocomplete cache so it rebuilds from your imported history."
echo ""
read -p "Make sure Atlas browser is CLOSED. Press Enter to continue or Ctrl+C to cancel..."

# Remove cache files that might affect autocomplete
echo ""
echo "Clearing cache files..."

# Remove Network Action Predictor (affects autocomplete)
if [ -f "$ATLAS_DEFAULT/Network Action Predictor" ]; then
    rm "$ATLAS_DEFAULT/Network Action Predictor"
    echo "✓ Removed Network Action Predictor"
fi

if [ -f "$ATLAS_DEFAULT/Network Action Predictor-journal" ]; then
    rm "$ATLAS_DEFAULT/Network Action Predictor-journal"
    echo "✓ Removed Network Action Predictor journal"
fi

# Remove Top Sites cache
if [ -f "$ATLAS_DEFAULT/Top Sites" ]; then
    rm "$ATLAS_DEFAULT/Top Sites"
    echo "✓ Removed Top Sites cache"
fi

if [ -f "$ATLAS_DEFAULT/Top Sites-journal" ]; then
    rm "$ATLAS_DEFAULT/Top Sites-journal"
    echo "✓ Removed Top Sites journal"
fi

# Update History database to trigger recalculation
echo ""
echo "Updating History database..."
sqlite3 "$ATLAS_DEFAULT/History" "VACUUM;"
echo "✓ Vacuumed History database"

echo ""
echo "Done! Next time you open Atlas browser, it will rebuild autocomplete suggestions."
echo "Try typing 'slick' in the address bar and it should now suggest slickdeals.net"
