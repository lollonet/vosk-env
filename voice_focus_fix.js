// Aggiungi dopo la funzione toggleVoice()
document.addEventListener('focusin', function(e) {
    if (isListening && isValidInput(e.target)) {
        activeElement = e.target;
        clearHighlight();
        highlightElement(activeElement);
        console.log('Voice input switched to new field');
    }
});
