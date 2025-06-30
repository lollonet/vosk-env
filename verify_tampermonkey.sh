#!/bin/bash

echo "🔍 Verifica installazione Tampermonkey"
echo "===================================="

# Test Chrome
if command -v google-chrome >/dev/null 2>&1; then
    echo "🧪 Test Chrome..."
    
    # Controlla se Tampermonkey è installato
    CHROME_PROFILE="$HOME/.config/google-chrome/Default"
    if [ -d "$CHROME_PROFILE/Extensions" ]; then
        if ls "$CHROME_PROFILE/Extensions"/dhdgffkkebhmkfjojejmpbldmpobfkfo* >/dev/null 2>&1; then
            echo "✅ Tampermonkey trovato in Chrome"
            CHROME_TM=true
        else
            echo "❌ Tampermonkey non trovato in Chrome"
            CHROME_TM=false
        fi
    else
        echo "⚠️  Chrome profile non trovato"
        CHROME_TM=false
    fi
fi

# Test Firefox
if command -v firefox >/dev/null 2>&1; then
    echo "🧪 Test Firefox..."
    
    FIREFOX_PROFILE=$(find "$HOME/.mozilla/firefox" -name "*.default*" -type d 2>/dev/null | head -1)
    if [ -n "$FIREFOX_PROFILE" ] && [ -d "$FIREFOX_PROFILE/extensions" ]; then
        if ls "$FIREFOX_PROFILE/extensions"/*tampermonkey* >/dev/null 2>&1; then
            echo "✅ Tampermonkey trovato in Firefox"
            FIREFOX_TM=true
        else
            echo "❌ Tampermonkey non trovato in Firefox"
            FIREFOX_TM=false
        fi
    else
        echo "⚠️  Firefox profile non trovato"
        FIREFOX_TM=false
    fi
fi

echo
echo "📋 Prossimi passi:"
if [ "$CHROME_TM" = true ] || [ "$FIREFOX_TM" = true ]; then
    echo "✅ Tampermonkey installato! Procedi con UserScript"
else
    echo "❌ Installa Tampermonkey manualmente:"
    echo "1. Apri browser"
    echo "2. Vai a Chrome Web Store o Firefox Add-ons"
    echo "3. Cerca 'Tampermonkey'"
    echo "4. Installa l'estensione"
fi
