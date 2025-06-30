// ==UserScript==
// @name         Voice Input Toggle + Language Switch
// @namespace    http://tampermonkey.net/
// @version      3.1
// @description  Voice input con switch lingua IT/EN + correzioni termini IT
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
    let isPermanentMode = false;
    let activeElement = null;
    let voiceButton = null;
    let languageButton = null;
    let currentLanguage = 'it';
    let availableLanguages = ['it', 'en'];
    let correctionsEnabled = true;
    
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
        
        .lang-btn {
            position: fixed;
            bottom: 90px;
            right: ${CONFIG.POSITION.right};
            width: 45px;
            height: 25px;
            border-radius: 12px;
            border: none;
            background: rgba(0,0,0,0.7);
            color: white;
            font-size: 11px;
            font-weight: bold;
            cursor: pointer;
            z-index: 999998;
            transition: all 0.3s ease;
        }
        
        .lang-btn:hover {
            background: rgba(0,0,0,0.9);
            transform: scale(1.05);
        }
        
        .lang-btn.it { background: #27ae60; }
        .lang-btn.en { background: #3498db; }
        
        @keyframes voicePulse {
            0% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0.7); }
            70% { box-shadow: 0 0 0 10px rgba(244, 67, 54, 0); }
            100% { box-shadow: 0 0 0 0 rgba(244, 67, 54, 0); }
        }
        
        .voice-highlight { outline: 2px solid #4CAF50 !important; outline-offset: 2px !important; }
        
        .correction-feedback {
            position: fixed;
            top: 20px;
            right: 20px;
            background: rgba(0,123,255,0.95);
            color: white;
            padding: 12px 16px;
            border-radius: 6px;
            font-size: 13px;
            z-index: 1000000;
            max-width: 350px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }
        
        .lang-switch-notification {
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: rgba(46, 204, 113, 0.95);
            color: white;
            padding: 10px 20px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
            z-index: 1000001;
        }
    `;
    
    const style = document.createElement('style');
    style.textContent = css;
    document.head.appendChild(style);
    
    function createButtons() {
        if (voiceButton) return;
        
        // Pulsante voice principale
        voiceButton = document.createElement('button');
        voiceButton.className = 'voice-btn';
        voiceButton.innerHTML = '🎤';
        voiceButton.title = 'Voice Input Toggle (Ctrl+/)';
        voiceButton.addEventListener('click', toggleVoice);
        document.body.appendChild(voiceButton);
        
        // Pulsante switch lingua
        languageButton = document.createElement('button');
        languageButton.className = 'lang-btn';
        languageButton.innerHTML = currentLanguage.toUpperCase();
        languageButton.title = 'Switch Language (Ctrl+?)';
        languageButton.addEventListener('click', switchLanguage);
        document.body.appendChild(languageButton);
    }
    
    function connectServer() {
        try {
            socket = new WebSocket(CONFIG.SERVER_URL);
            
            socket.onopen = () => {
                console.log('🌐 Voice server connected');
                updateButtonState('ready');
            };
            
            socket.onmessage = (event) => {
                const data = JSON.parse(event.data);
                handleMessage(data);
            };
            
            socket.onclose = () => {
                console.log('🔌 Voice server disconnected');
                updateButtonState('disconnected');
                setTimeout(connectServer, 3000);
            };
            
        } catch (error) {
            console.error('❌ WebSocket error:', error);
            updateButtonState('disconnected');
        }
    }
    
    function handleMessage(data) {
        switch(data.type) {
            case 'language_status':
                currentLanguage = data.current_language;
                availableLanguages = data.available_languages;
                correctionsEnabled = data.corrections_enabled;
                updateLanguageButton();
                console.log(`🌍 Lingua corrente: ${currentLanguage.toUpperCase()}`);
                break;
                
            case 'speech_result':
                if (activeElement) {
                    insertText(activeElement, data.text);
                    
                    // Mostra feedback correzioni
                    if (data.original_text && data.original_text !== data.text) {
                        showCorrectionFeedback(data.original_text, data.text);
                    }
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
                
            case 'language_switched':
                currentLanguage = data.language;
                correctionsEnabled = data.corrections_enabled;
                updateLanguageButton();
                showLanguageSwitchNotification(currentLanguage);
                console.log(`🔄 Switched to: ${currentLanguage.toUpperCase()}`);
                break;
                
            case 'error':
                console.error('❌ Server error:', data.message);
                break;
        }
    }
    
    function showCorrectionFeedback(originalText, correctedText) {
        const feedback = document.createElement('div');
        feedback.className = 'correction-feedback';
        feedback.innerHTML = `
            🔧 <strong>Termine IT corretto:</strong><br>
            <del style="opacity:0.7">"${originalText}"</del><br>
            <strong>"${correctedText}"</strong>
        `;
        
        document.body.appendChild(feedback);
        
        setTimeout(() => {
            feedback.style.opacity = '0';
            setTimeout(() => feedback.remove(), 300);
        }, 4000);
    }
    
    function showLanguageSwitchNotification(lang) {
        const notification = document.createElement('div');
        notification.className = 'lang-switch-notification';
        
        const langNames = { 'it': '🇮🇹 Italiano', 'en': '🇺🇸 English' };
        const corrections = lang === 'it' ? ' + Correzioni IT' : '';
        
        notification.innerHTML = `Lingua: ${langNames[lang] || lang.toUpperCase()}${corrections}`;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => notification.remove(), 300);
        }, 2500);
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
    
    function toggleVoice() {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            alert('Voice server non connesso');
            return;
        }
        
        if (isPermanentMode) {
            stopPermanentMode();
        } else {
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
        
        socket.send(JSON.stringify({type: 'start_permanent_listening'}));
        
        updateButtonState('permanent');
        console.log(`🎤 Voice input ATTIVO (${currentLanguage.toUpperCase()})`);
    }
    
    function stopPermanentMode() {
        isPermanentMode = false;
        isListening = false;
        
        socket.send(JSON.stringify({type: 'stop_permanent_listening'}));
        
        updateButtonState('ready');
        clearHighlight();
        
        console.log('🛑 Voice input DISATTIVATO');
    }
    
    function switchLanguage() {
        if (!socket || socket.readyState !== WebSocket.OPEN) {
            console.warn('⚠️ WebSocket not connected');
            return;
        }
        
        // Cicla tra lingue disponibili
        const currentIndex = availableLanguages.indexOf(currentLanguage);
        const nextIndex = (currentIndex + 1) % availableLanguages.length;
        const nextLanguage = availableLanguages[nextIndex];
        
        console.log(`🔄 Switching language: ${currentLanguage} → ${nextLanguage}`);
        
        socket.send(JSON.stringify({
            type: 'switch_language',
            language: nextLanguage
        }));
    }
    
    function updateButtonState(state) {
        if (!voiceButton) return;
        
        voiceButton.className = 'voice-btn';
        switch(state) {
            case 'ready':
                voiceButton.innerHTML = '🎤';
                voiceButton.title = `Voice Input OFF (${currentLanguage.toUpperCase()}) - Ctrl+/ per attivare`;
                break;
                
            case 'permanent':
                voiceButton.classList.add('permanent');
                voiceButton.innerHTML = '🔥';
                voiceButton.title = `Voice Input ON (${currentLanguage.toUpperCase()}) - Ctrl+/ per disattivare`;
                break;
                
            case 'listening':
                voiceButton.classList.add('listening');
                voiceButton.innerHTML = '🔴';
                voiceButton.title = `Voice Input - Listening (${currentLanguage.toUpperCase()})...`;
                break;
                
            case 'disconnected':
                voiceButton.classList.add('disconnected');
                voiceButton.innerHTML = '📵';
                voiceButton.title = 'Voice Input - Disconnesso';
                break;
        }
    }
    
    function updateLanguageButton() {
        if (!languageButton) return;
        
        languageButton.innerHTML = currentLanguage.toUpperCase();
        languageButton.className = `lang-btn ${currentLanguage}`;
        
        const langNames = { 'it': 'Italiano', 'en': 'English' };
        const corrections = correctionsEnabled ? ' + Correzioni IT' : '';
        languageButton.title = `Lingua: ${langNames[currentLanguage] || currentLanguage}${corrections} (Ctrl+? per cambiare)`;
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
    
    // Hotkeys
    document.addEventListener('keydown', (e) => {
        // Ctrl+/ per toggle voice
        if (e.ctrlKey && e.code === 'Slash') {
            e.preventDefault();
            toggleVoice();
        }
        
        // Ctrl+? per switch lingua
        if (e.ctrlKey && e.shiftKey && e.code === 'Slash') {
            e.preventDefault();
            switchLanguage();
        }
        
        // Esc per disattivare
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
        
        createButtons();
        connectServer();
        console.log('🎤 Voice Input Multi-Language + IT Corrections loaded');
        console.log('💡 Ctrl+/ = Toggle Voice, Ctrl+? = Switch Language, Esc = Force OFF');
    }
    
    init();
    
})();
