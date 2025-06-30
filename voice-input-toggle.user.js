// ==UserScript==
// @name         Voice Input Toggle + Language Detection
// @namespace    http://tampermonkey.net/
// @version      2.0
// @description  Voice input toggle con riconoscimento automatico lingua
// @author       VoskSpeech
// @match        *://*/*
// @grant        none
// @run-at       document-end
// ==/UserScript==

(function() {
    'use strict';
    
    const CONFIG = {
        SERVER_URL: 'ws://localhost:8765',
        BUTTON_SIZE: '60px',
        POSITION: { bottom: '20px', right: '20px' }
    };
    
    let socket = null;
    let isListening = false;
    let isPermanentMode = false; // Nuovo: modalità toggle
    let activeElement = null;
    let voiceButton = null;
    let currentLanguage = 'auto'; // auto, it, en
    
    // CSS con indicatori lingua
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
        
        .voice-btn:hover { transform: scale(1.1); }
        
        .voice-btn.listening {
            background: linear-gradient(45deg, #f44336, #d32f2f);
            animation: voicePulse 1.5s infinite;
        }
        
        .voice-btn.permanent {
            background: linear-gradient(45deg, #ff9800, #f57c00);
            box-shadow: 0 0 15px rgba(255, 152, 0, 0.6);
        }
        
        .voice-btn.disconnected {
            background: linear-gradient(45deg, #9E9E9E, #757575);
        }
        
        @keyframes voicePulse {
            0% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(244, 67, 54, 0); }
            100% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0); }
        }
        
        .voice-highlight { outline: 2px solid #4CAF50 !important; outline-offset: 2px !important; }
        
        .lang-indicator {
            position: fixed;
            bottom: 90px;
            right: 20px;
            background: rgba(0,0,0,0.8);
            color: white;
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 12px;
            z-index: 999998;
            transition: opacity 0.3s;
        }
    `;
    
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
    
    function createButton() {
        if (voiceButton) return;
        
        voiceButton = document.createElement('button');
        voiceButton.className = 'voice-btn';
        voiceButton.innerHTML = '🎤';
        voiceButton.title = 'Voice Input Toggle (Ctrl+/)';
        
        voiceButton.addEventListener('click', toggleVoice);
        document.body.appendChild(voiceButton);
    }
    
    function createLanguageIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'lang-indicator';
        indicator.id = 'voice-lang-indicator';
        indicator.textContent = 'AUTO';
        indicator.style.opacity = '0';
        document.body.appendChild(indicator);
        return indicator;
    }
    
    function showLanguageIndicator(lang) {
        let indicator = document.getElementById('voice-lang-indicator');
        if (!indicator) indicator = createLanguageIndicator();
        
        const langNames = { 'auto': 'AUTO', 'it': 'ITA', 'en': 'ENG' };
        indicator.textContent = langNames[lang] || lang.toUpperCase();
        indicator.style.opacity = '1';
        
        if (isPermanentMode) {
            setTimeout(() => { indicator.style.opacity = '0.3'; }, 2000);
        } else {
            setTimeout(() => { indicator.style.opacity = '0'; }, 3000);
        }
    }
    
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
    
    function handleMessage(data) {
        switch(data.type) {
            case 'speech_result':
                if (activeElement) {
                    insertText(activeElement, data.text);
                }
                break;
                
            case 'listening_started':
                isListening = true;
                updateButtonState(isPermanentMode ? 'permanent' : 'listening');
                break;
                
            case 'listening_stopped':
                isListening = false;
                if (!isPermanentMode) {
                    updateButtonState('ready');
                    clearHighlight();
                }
                break;
                
            case 'language_detected':
                currentLanguage = data.language;
                showLanguageIndicator(currentLanguage);
                console.log(`Language detected: ${currentLanguage}`);
                break;
        }
    }
    
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
    
    function findInput() {
        const focused = document.activeElement;
        if (isValidInput(focused)) return focused;
        
        const inputs = document.querySelectorAll('input[type="text"], input[type="email"], input[type="search"], textarea, [contenteditable="true"]');
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
        const type = el.type?.toLowerCase();
        return (tag === 'input' && ['text', 'email', 'search', 'url'].includes(type)) || 
               tag === 'textarea' || 
               el.contentEditable === 'true';
    }
    
    function isVisible(el) {
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
    }
    
    // Nuovo: Toggle logic
    function toggleVoice() {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            alert('Voice server non connesso');
            return;
        }
        
        if (isPermanentMode) {
            // Disattiva modalità permanente
            stopPermanentMode();
        } else {
            // Attiva modalità permanente
            startPermanentMode();
        }
    }
    
    function startPermanentMode() {
        activeElement = findInput();
        if (!activeElement) {
            alert('Clicca in un campo di testo prima di attivare voice input');
            return;
        }
        
        isPermanentMode = true;
        highlightElement(activeElement);
        showLanguageIndicator('auto');
        
        socket.send(JSON.stringify({
            type: 'start_permanent_listening',
            language: 'auto'
        }));
        
        updateButtonState('permanent');
        console.log('🎤 Voice input ATTIVO (modalità permanente)');
    }
    
    function stopPermanentMode() {
        isPermanentMode = false;
        isListening = false;
        
        socket.send(JSON.stringify({type: 'stop_permanent_listening'}));
        
        updateButtonState('ready');
        clearHighlight();
        
        const indicator = document.getElementById('voice-lang-indicator');
        if (indicator) indicator.style.opacity = '0';
        
        console.log('🛑 Voice input DISATTIVATO');
    }
    
    function updateButtonState(state) {
        if (!voiceButton) return;
        
        voiceButton.className = 'voice-btn';
        switch(state) {
            case 'ready':
                voiceButton.innerHTML = '🎤';
                voiceButton.title = 'Voice Input OFF (Ctrl+/ per attivare)';
                break;
                
            case 'permanent':
                voiceButton.classList.add('permanent');
                voiceButton.innerHTML = '🔥';
                voiceButton.title = 'Voice Input ON (Ctrl+/ per disattivare)';
                break;
                
            case 'listening':
                voiceButton.classList.add('listening');
                voiceButton.innerHTML = '🔴';
                voiceButton.title = 'Voice Input - Listening...';
                break;
                
            case 'disconnected':
                voiceButton.classList.add('disconnected');
                voiceButton.innerHTML = '📵';
                voiceButton.title = 'Voice Input - Disconnesso';
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
    
    // Focus change listener
    document.addEventListener('focusin', function(e) {
        if (isPermanentMode && isValidInput(e.target)) {
            activeElement = e.target;
            clearHighlight();
            highlightElement(activeElement);
        }
    });
    
    // Hotkey: Ctrl+/ per toggle
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.code === 'Slash') {
            e.preventDefault();
            toggleVoice();
        }
        
        // Esc per disattivare modalità permanente
        if (e.code === 'Escape' && isPermanentMode) {
            e.preventDefault();
            stopPermanentMode();
        }
    });
    
    function init() {
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', init);
            return;
        }
        
        createButton();
        connectServer();
        console.log('🎤 Voice Input Toggle + Language Detection loaded');
        console.log('💡 Ctrl+/ = Toggle ON/OFF, Esc = Force OFF');
    }
    
    init();
    
})();

    // Aggiungi dopo handleMessage()
    function showCorrectionFeedback(originalText, correctedText) {
        if (!originalText || originalText === correctedText) return;
        
        const feedback = document.createElement('div');
        feedback.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0,123,255,0.9);
            color: white;
            padding: 10px 15px;
            border-radius: 5px;
            font-size: 12px;
            z-index: 1000000;
            max-width: 300px;
        `;
        
        feedback.innerHTML = `
            🔧 <strong>Corretto:</strong><br>
            <del style="opacity:0.7">${originalText}</del><br>
            <strong>${correctedText}</strong>
        `;
        
        document.body.appendChild(feedback);
        
        setTimeout(() => {
            feedback.style.opacity = '0';
            setTimeout(() => feedback.remove(), 300);
        }, 3000);
    }

    // Modifica handleMessage per mostrare correzioni
    function handleMessage(data) {
        switch(data.type) {
            case 'speech_result':
                if (activeElement) {
                    insertText(activeElement, data.text);
                    
                    // Mostra feedback se c'è stata una correzione
                    if (data.original_text && data.original_text !== data.text) {
                        showCorrectionFeedback(data.original_text, data.text);
                    }
                }
                break;
                
            // resto uguale...
        }
    }
