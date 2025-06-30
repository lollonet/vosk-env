#!/bin/bash
# Voice Daemon - Gestione servizi Vosk

# Path assoluti per evitare problemi
VOSK_DIR="/home/claudio/vosk-env"
PID_DIR="/tmp"
BROWSER_SERVER_PID="$PID_DIR/vosk-browser.pid"
LOG_DIR="$VOSK_DIR/logs"

# Colori
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

mkdir -p "$LOG_DIR"

print_status() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

print_success() {
    echo -e "${GREEN}✅${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

check_deps() {
    print_status "Verifica dipendenze..."
    
    # Debug paths
    print_status "VOSK_DIR: $VOSK_DIR"
    print_status "Script path: $VOSK_DIR/scripts/voice_browser_server.py"
    
    # Verifica directory
    if [ ! -d "$VOSK_DIR" ]; then
        print_error "Directory Vosk non trovata: $VOSK_DIR"
        return 1
    fi
    
    # Verifica script server
    if [ ! -f "$VOSK_DIR/scripts/voice_browser_server.py" ]; then
        print_error "Script server non trovato: $VOSK_DIR/scripts/voice_browser_server.py"
        print_error "Contenuto directory scripts:"
        ls -la "$VOSK_DIR/scripts/" 2>/dev/null || print_error "Directory scripts non esiste"
        return 1
    fi
    
    # Verifica virtual environment
    if [ -z "$VIRTUAL_ENV" ]; then
    # Check Python modules
    if ! python3 -c "import vosk, websockets, sounddevice" 2>/dev/null; then
        print_error "Moduli Python mancanti"
        print_status "Installa con: pip install vosk websockets sounddevice"
        return 1
    fi
        print_status "Tentativo attivazione..."
        if [ -f "$VOSK_DIR/bin/activate" ]; then
            source "$VOSK_DIR/bin/activate"
    # Check Python modules
    if ! python3 -c "import vosk, websockets, sounddevice" 2>/dev/null; then
        print_error "Moduli Python mancanti"
        print_status "Installa con: pip install vosk websockets sounddevice"
        return 1
    fi
        else
            print_error "Script activate non trovato in $VOSK_DIR/bin/"
        fi
    else
    # Check Python modules
    if ! python3 -c "import vosk, websockets, sounddevice" 2>/dev/null; then
        print_error "Moduli Python mancanti"
        print_status "Installa con: pip install vosk websockets sounddevice"
        return 1
    fi
    fi
    
    # Verifica moduli Python
    python3 -c "import vosk, websockets, sounddevice" 2>/dev/null || {
        print_error "Moduli Python mancanti"
        print_status "Installa con: pip install vosk websockets sounddevice"
        return 1
    }
    
    # Verifica modelli
    if [ ! -d "$VOSK_DIR/models/italian" ]; then
        print_warning "Modello italiano non trovato in $VOSK_DIR/models/italian"
    fi
    
    print_success "Dipendenze OK"
    return 0
}

start_browser_server() {
    if [ -f "$BROWSER_SERVER_PID" ] && kill -0 $(cat "$BROWSER_SERVER_PID") 2>/dev/null; then
        print_warning "Server già attivo (PID: $(cat $BROWSER_SERVER_PID))"
        return 1
    fi
    
    print_status "Avvio browser server..."
    
    # Vai nella directory giusta
    cd "$VOSK_DIR" || {
        print_error "Impossibile entrare in $VOSK_DIR"
        return 1
    }
    
    # Attiva virtual environment se necessario
    if [ -z "$VIRTUAL_ENV" ] && [ -f "$VOSK_DIR/bin/activate" ]; then
        source "$VOSK_DIR/bin/activate"
    fi
    
    # Avvia server
    nohup python3 scripts/voice_browser_server.py \
        --port 8765 > "$LOG_DIR/browser-server.log" 2>&1 &
    
    local pid=$!
    echo $pid > "$BROWSER_SERVER_PID"
    
    # Verifica avvio
    sleep 3
    if kill -0 $pid 2>/dev/null; then
        print_success "Server avviato (PID: $pid)"
        print_status "Log: tail -f $LOG_DIR/browser-server.log"
        
        # Test connessione
        if nc -z localhost 8765 2>/dev/null; then
            print_success "WebSocket accessibile su localhost:8765"
        else
            print_warning "WebSocket non risponde (potrebbe essere normale nei primi secondi)"
        fi
        
        return 0
    else
        print_error "Errore avvio server"
        print_error "Vedi log: cat $LOG_DIR/browser-server.log"
        rm -f "$BROWSER_SERVER_PID"
        return 1
    fi
}

stop_browser_server() {
    if [ -f "$BROWSER_SERVER_PID" ]; then
        local pid=$(cat "$BROWSER_SERVER_PID")
        if kill -0 $pid 2>/dev/null; then
            print_status "Fermando server (PID: $pid)..."
            kill $pid
            sleep 2
            
            if kill -0 $pid 2>/dev/null; then
                print_warning "Force kill..."
                kill -9 $pid
            fi
            print_success "Server fermato"
        else
            print_warning "Process non trovato"
        fi
        rm -f "$BROWSER_SERVER_PID"
    else
        print_warning "Server non in esecuzione"
    fi
}

status() {
    print_status "Stato Voice Input System"
    echo
    
    # Directory
    print_status "Directory: $VOSK_DIR"
    
    # Virtual environment
    if [ -n "$VIRTUAL_ENV" ]; then
        print_success "Virtual Env: ACTIVE ($VIRTUAL_ENV)"
    else
        print_warning "Virtual Env: NOT ACTIVE"
    fi
    
    # Server
    if [ -f "$BROWSER_SERVER_PID" ] && kill -0 $(cat "$BROWSER_SERVER_PID") 2>/dev/null; then
        local pid=$(cat "$BROWSER_SERVER_PID")
        print_success "Browser Server: RUNNING (PID: $pid)"
    else
        print_error "Browser Server: STOPPED"
    fi
    
    # WebSocket
    if command -v nc >/dev/null && nc -z localhost 8765 2>/dev/null; then
        print_success "WebSocket: ACCESSIBLE (localhost:8765)"
    else
        print_error "WebSocket: NOT ACCESSIBLE"
    fi
    
    # Modelli
    echo
    print_status "Modelli disponibili:"
    if [ -d "$VOSK_DIR/models" ]; then
        ls -la "$VOSK_DIR/models/"
    else
        print_warning "Directory models non trovata"
    fi
}

show_logs() {
    if [ -f "$LOG_DIR/browser-server.log" ]; then
        print_status "Log server (Ctrl+C per uscire):"
        tail -f "$LOG_DIR/browser-server.log"
    else
        print_error "Log non trovato: $LOG_DIR/browser-server.log"
    fi
}

show_help() {
    echo "Voice Daemon - Gestione Voice Input System"
    echo
    echo "Comandi:"
    echo "  start    - Avvia server WebSocket"
    echo "  stop     - Ferma server"
    echo "  restart  - Riavvia server"
    echo "  status   - Mostra stato sistema"
    echo "  logs     - Mostra log real-time"
    echo "  help     - Questo aiuto"
}

# Main
case "${1:-help}" in
    start)
        check_deps && start_browser_server
        ;;
    stop)
        stop_browser_server
        ;;
    restart)
        stop_browser_server
        sleep 2
        check_deps && start_browser_server
        ;;
    status)
        status
        ;;
    logs)
        show_logs
        ;;
    help|*)
        show_help
        ;;
esac
