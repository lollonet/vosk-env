#!/bin/bash
# Setup Voice System - Installazione globale senza venv

echo "🔧 Setup Voice Input System (Global Python)"
echo "============================================"

# Verifica Python
if ! command -v python3 >/dev/null; then
    echo "❌ Python3 non trovato"
    exit 1
fi

echo "✅ Python3: $(python3 --version)"

# Installa dipendenze Python globali
echo "📦 Installazione dipendenze Python..."
pip3 install --user vosk websockets sounddevice numpy scipy

# Verifica installazione
echo "🧪 Test dipendenze..."
python3 -c "
import vosk
import websockets
import sounddevice
import numpy
import scipy
print('✅ Tutti i moduli installati correttamente')
" || {
    echo "❌ Errore installazione moduli"
    exit 1
}

# Verifica modelli
echo "📁 Verifica modelli Vosk..."
if [ -d "$HOME/vosk-env/models/italian" ]; then
    echo "✅ Modello italiano trovato"
else
    echo "⚠️  Modello italiano non trovato"
    echo "💡 Esegui: ./download_models.sh"
fi

echo
echo "✅ Setup completato!"
echo "🚀 Ora puoi usare:"
echo "  • ./bin/voice_daemon.sh start"
echo "  • voice-terminal start"  
echo "  • claude-voice-session"
echo "  • Voice input nel browser (Tampermonkey)"
