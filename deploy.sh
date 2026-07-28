#!/bin/bash
set -e

# Script di deploy automatico per FBOPreventivi
# Usage: ./deploy.sh [opzioni]
#   -m "messaggio"  : Commit con messaggio specificato
#   -s              : Solo deploy VPS (skip git)
#   -g              : Solo git push (skip VPS)
#   -h              : Help

COLOR_RESET='\033[0m'
COLOR_GREEN='\033[0;32m'
COLOR_YELLOW='\033[1;33m'
COLOR_RED='\033[0;31m'
COLOR_BLUE='\033[0;34m'

VPS_HOST="mkremote-vps"
VPS_APP_PATH="/opt/preventivi/app"

print_step() {
    echo -e "${COLOR_BLUE}▶ $1${COLOR_RESET}"
}

print_success() {
    echo -e "${COLOR_GREEN}✓ $1${COLOR_RESET}"
}

print_warning() {
    echo -e "${COLOR_YELLOW}⚠ $1${COLOR_RESET}"
}

print_error() {
    echo -e "${COLOR_RED}✗ $1${COLOR_RESET}"
}

show_help() {
    cat << EOF
Deploy automatico FBOPreventivi

Usage: ./deploy.sh [opzioni]

Opzioni:
  -m "messaggio"    Commit con messaggio specificato e deploy completo
  -s                Solo deploy VPS (skip commit/push GitHub)
  -g                Solo commit/push GitHub (skip deploy VPS)
  -h                Mostra questo help

Senza opzioni: deploy completo interattivo (chiede messaggio commit)

Esempi:
  ./deploy.sh                              # Deploy completo interattivo
  ./deploy.sh -m "Fix bug PDF footer"      # Deploy completo con messaggio
  ./deploy.sh -s                           # Solo aggiorna VPS
  ./deploy.sh -g                           # Solo commit/push GitHub
EOF
}

# Parse opzioni
COMMIT_MSG=""
SKIP_GIT=false
SKIP_VPS=false

while getopts "m:sgha" opt; do
    case $opt in
        m)
            COMMIT_MSG="$OPTARG"
            ;;
        s)
            SKIP_GIT=true
            ;;
        g)
            SKIP_VPS=true
            ;;
        h)
            show_help
            exit 0
            ;;
        *)
            show_help
            exit 1
            ;;
    esac
done

echo ""
echo "=========================================="
echo "  FBOPreventivi - Deploy Automatico"
echo "=========================================="
echo ""

# ==========================================
# PARTE 1: GIT COMMIT & PUSH
# ==========================================

if [ "$SKIP_GIT" = false ]; then
    print_step "Verifica modifiche Git..."
    
    if [ -z "$(git status --porcelain)" ]; then
        print_warning "Nessuna modifica da committare"
    else
        echo ""
        git status --short
        echo ""
        
        # Se messaggio non specificato, chiedi
        if [ -z "$COMMIT_MSG" ]; then
            read -p "Messaggio commit: " COMMIT_MSG
            if [ -z "$COMMIT_MSG" ]; then
                print_error "Messaggio commit obbligatorio"
                exit 1
            fi
        fi
        
        print_step "Commit modifiche..."
        git add .
        git commit -m "$COMMIT_MSG"
        print_success "Commit creato"
    fi
    
    print_step "Push su GitHub..."
    git push origin main
    print_success "Push completato su GitHub"
    echo ""
fi

# ==========================================
# PARTE 2: DEPLOY VPS
# ==========================================

if [ "$SKIP_VPS" = false ]; then
    print_step "Connessione al VPS $VPS_HOST..."
    
    # Test connessione
    if ! ssh -o ConnectTimeout=5 "$VPS_HOST" "exit" 2>/dev/null; then
        print_error "Impossibile connettersi al VPS"
        exit 1
    fi
    print_success "Connesso al VPS"
    
    print_step "Deploy applicazione sul VPS..."
    
    ssh "$VPS_HOST" bash << 'ENDSSH'
set -e

echo "  → Git pull..."
cd /opt/preventivi/app
sudo -u preventivi git pull origin main

echo "  → Aggiornamento dipendenze..."
sudo -u preventivi venv/bin/pip install -q -r requirements.txt

echo "  → Migrazioni database..."
sudo -u preventivi venv/bin/python manage.py migrate --noinput

echo "  → Raccolta file statici..."
sudo -u preventivi venv/bin/python manage.py collectstatic --noinput --clear

echo "  → Restart servizio..."
systemctl restart preventivi-web.service

echo "  → Attesa avvio servizio..."
sleep 2
ENDSSH
    
    print_success "Deploy completato sul VPS"
    echo ""
    
    print_step "Stato servizio:"
    ssh "$VPS_HOST" "systemctl status preventivi-web.service --no-pager -l | head -15"
    echo ""
    
    print_success "Deploy completato con successo! 🚀"
    echo ""
    echo "Applicazione disponibile su: https://94.177.161.127:8445"
else
    print_success "Commit/Push completato! 🎯"
fi

echo ""
