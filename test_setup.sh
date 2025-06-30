#!/bin/bash
echo "🔧 Test Configurazione Vosk"
echo "=========================="

# Attiva ambiente
source venv/bin/activate

# Test 1: Verifica modelli
echo "📁 Test modelli..."
ls -la models/
echo

# Test 2: Test dispositivi audio
echo "🎤 Dispositivi audio disponibili:"
python3 -c "
import sounddevice as sd
devices = sd.query_devices()
for i, device in enumerate(devices):
    if device['max_input_channels'] > 0:
        print(f'  [{i}] {device[\"name\"]} - {device[\"max_input_channels\"]} ch')
"
echo

# Test 3: Test registrazione breve
echo "📼 Test registrazione 3 secondi..."
python3 -c "
import sounddevice as sd
import numpy as np
duration = 3
sample_rate = 16000
print('Parla ora...')
recording = sd.rec(int(duration * sample_rate), samplerate=sample_rate, channels=1)
sd.wait()
print(f'Registrato: {len(recording)} samples')
print('Volume medio:', np.mean(np.abs(recording)))
"

# Test 4: Test engine Vosk
echo "🗣️  Test engine Vosk (10 secondi)..."
echo "Pronuncia qualche parola in italiano..."
python3 scripts/vosk_engine.py --duration 10 --verbose

echo "✅ Test completato!"
