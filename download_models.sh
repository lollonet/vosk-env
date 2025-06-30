#!/bin/bash
set -e

MODELS_DIR="$HOME/vosk-env/models"
mkdir -p "$MODELS_DIR"

echo "📥 Download modelli Vosk LARGE in: $MODELS_DIR"

# Modello Italiano Large (1.8GB - accuracy ~92%)
if [ ! -d "$MODELS_DIR/italian" ]; then
    echo "⬇️  Downloading Italian LARGE model (1.8GB)..."
    wget -q --show-progress -O "$MODELS_DIR/vosk-model-it-large.zip" \
      "https://alphacephei.com/vosk/models/vosk-model-it-0.22.zip"
    
    echo "📦 Extracting Italian model..."
    cd "$MODELS_DIR"
    unzip -q vosk-model-it-large.zip
    mv vosk-model-it-0.22 italian
    rm vosk-model-it-large.zip
    echo "✅ Modello italiano LARGE installato"
else
    echo "✅ Modello italiano già presente"
fi

# Modello Inglese Large (1.6GB - accuracy ~95%)
if [ ! -d "$MODELS_DIR/english" ]; then
    echo "⬇️  Downloading English LARGE model (1.6GB)..."
    wget -q --show-progress -O "$MODELS_DIR/vosk-model-en-large.zip" \
      "https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"
    
    echo "📦 Extracting English model..."
    cd "$MODELS_DIR"
    unzip -q vosk-model-en-large.zip
    mv vosk-model-en-us-0.22 english
    rm vosk-model-en-large.zip
    echo "✅ Modello inglese LARGE installato"
else
    echo "✅ Modello inglese già presente"
fi

echo
echo "✅ Modelli LARGE installati in: $MODELS_DIR"
echo "📊 Accuracy attesa: IT ~92%, EN ~95%"
echo "💾 Spazio usato: ~3.5GB"
ls -la "$MODELS_DIR"
