#!/bin/bash

echo "📝 Installazione Manuale UserScript"
echo "=================================="

# Crea UserScript ottimizzato
cat > voice-input-tampermonkey.user.js << 'JSEOF'
// ==UserScript==
// @name         Voice Input Vosk
// @namespace    http://tampermonkey.net/
// @version      1.0
// @description  Input vocale per tutti i siti tramite Vosk locale
// @author       VoskSpeech
// @match        *://*/*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';
    
    // Configurazione
    const CONFIG = {
        SERVER_URL: 'ws://localhost:8765',
        BUTTON_SIZE: '60px',
        POSITION: { bottom: '20px', right: '20px' }
    };
    
    let socket = null;
    let isListening = false;
    let activeElement = null;
    let voiceButton = null;
    
    // Stili CSS
    const css = `
        .voice-btn {
            position: fixed;
            bottom: ${CONFIG.POSITION.bottom};
            right: ${CONFIG.POSITION.right};
            width: ${CONFIG.BUTTON_SIZE};
            height: ${CONFIG.BUTTON_SIZE};
            border-radius: 50%;
            border: none;
            background: linear-gradient(45deg, #4CAF50, #45a049);
            color: white;
            font-size: 24px;
            cursor: pointer;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            z-index: 999999;
            transition: all 0.3s ease;
        }
        
        .voice-btn:hover {
            transform: scale(1.1);
        }
        
        .voice-btn.listening {
            background: linear-gradient(45deg, #f44336, #d32f2f);
            animation: voicePulse 1.5s infinite;
        }
        
        .voice-btn.disconnected {
            background: linear-gradient(45deg, #9E9E9E, #757575);
        }
        
        @keyframes voicePulse {
            0% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(244, 67, 54, 0); }
            100% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0); }
        }
        
        .voice-highlight {
            outline: 2px solid #4CAF50 !important;
            outline-offset: 2px !important;
        }
    `;
    
    // Inserisci CSS
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
    
    // Crea pulsante
    function createButton() {
        if (voiceButton) return;
        
        voiceButton = document.createElement('button');
        voiceButton.className = 'voice-btn';
        voiceButton.innerHTML = '🎤';
        voiceButton.title = 'Voice Input (Ctrl+Shift+V)';
        
        voiceButton.addEventListener('click', toggleVoice);
        document.body.appendChild(voiceButton);
    }
    
    // Connessione WebSocket
    function connectServer() {
        try {
            socket = new WebSocket(CONFIG.SERVER_URL);
            
            socket.onopen = () => {
                console.log('Voice server connected');
                updateButtonState('ready');
            };
            
            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            socket.onclose = () => {
                console.log('Voice server disconnected');
                updateButtonState('disconnected');
                setTimeout(connectServer, 3000);
            };
            
        } catch (error) {
            console.error('WebSocket error:', error);
            updateButtonState('disconnected');
        }
    }
    
    // Gestione messaggi
    function handleMessage(data) {
        if (data.type === 'speech_result' && activeElement) {
            insertText(activeElement, data.text);
        } else if (data.type === 'listening_started') {
            isListening = true;
            updateButtonState('listening');
        } else if (data.type === 'listening_stopped') {
            isListening = false;
            updateButtonState('ready');
            clearHighlight();
        }
    }
    
    // Inserimento testo
    function insertText(element, text) {
        const cleanText = text.trim() + ' ';
        
        if (element.tagName === 'INPUT' || element.tagName === 'TEXTAREA') {
            const start = element.selectionStart;
            const end = element.selectionEnd;
            const current = element.value;
            
            element.value = current.substring(0, start) + cleanText + current.substring(end);
            element.selectionStart = element.selectionEnd = start + cleanText.length;
        } else if (element.contentEditable === 'true') {
            document.execCommand('insertText', false, cleanText);
        }
        
        element.dispatchEvent(new Event('input', {bubbles: true}));
        element.focus();
    }
    
    // Trova input attivo
    function findInput() {
        const focused = document.activeElement;
        if (isValidInput(focused)) return focused;
        
        const inputs = document.querySelectorAll('input[type="text"], textarea, [contenteditable="true"]');
        for (const input of inputs) {
            if (isValidInput(input) && isVisible(input)) {
                return input;
            }
        }
        return null;
    }
    
    function isValidInput(el) {
        if (!el) return false;
        const tag = el.tagName.toLowerCase();
        return (tag === 'input' && el.type === 'text') || 
               tag === 'textarea' || 
               el.contentEditable === 'true';
    }
    
    function isVisible(el) {
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }
    
    // Toggle voice
    function toggleVoice() {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            alert('Voice server non connesso');
            return;
        }
        
        if (isListening) {
            socket.send(JSON.stringify({type: 'stop_listening'}));
        } else {
            activeElement = findInput();
            if (!activeElement) {
                alert('Clicca in un campo di testo');
                return;
            }
            
            highlightElement(activeElement);
            socket.send(JSON.stringify({type: 'start_listening'}));
        }
    }
    
    // Gestione UI
    function updateButtonState(state) {
        if (!voiceButton) return;
        
        voiceButton.className = 'voice-btn';
        switch(state) {
            case 'ready':
                voiceButton.innerHTML = '🎤';
                break;
            case 'listening':
                voiceButton.classList.add('listening');
                voiceButton.innerHTML = '🔴';
                break;
            case 'disconnected':
                voiceButton.classList.add('disconnected');
                voiceButton.innerHTML = '📵';
                break;
        }
    }
    
    function highlightElement(el) {
        clearHighlight();
        el.classList.add('voice-highlight');
    }
    
    function clearHighlight() {
        document.querySelectorAll('.voice-highlight').forEach(el => {
            el.classList.remove('voice-highlight');
        });
    }
    
    // Hotkey
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.shiftKey && e.code === 'KeyV') {
            e.preventDefault();
            toggleVoice();
        }
    });
    
    // Inizializzazione
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }
        
        createButton();
        connectServer();
        console.log('Voice Input loaded');
    }
    
    init();
    
})();
JSEOF

echo "✅ UserScript creato: voice-input-tampermonkey.user.js"
echo
echo "📋 Installazione manuale:"
echo "1. Apri browser con Tampermonkey"
echo "2. Clicca icona Tampermonkey → Dashboard"
echo "3. Tab 'Editor' → '+' (Create new script)"
echo "4. Cancella tutto il contenuto"
echo "5. Copia e incolla il contenuto da:"
echo "   $(pwd)/voice-input-tampermonkey.user.js"
echo "6. Salva (Ctrl+S)"
echo
echo "🔧 Test:"
echo "- Apri qualsiasi sito web"
echo "- Dovresti vedere il pulsante 🎤"
echo "- Hotkey: Ctrl+Shift+V"

# Apri il file per copia manuale
if command -v gedit >/dev/null 2>&1; then
    echo
    echo "📝 Apertura file per copia..."
    gedit voice-input-tampermonkey.user.js &
elif command -v nano >/dev/null 2>&1; then
    echo
    echo "📝 File disponibile per lettura:"
    echo "nano voice-input-tampermonkey.user.js"
fi
