# FBOPreventivi

Sistema di gestione e generazione preventivi in formato PDF per FBO Solution.

## 🚀 Quick Start

### Deploy Automatico

Usa lo script `deploy.sh` per deployment rapido:

```bash
# Deploy completo (commit + push GitHub + aggiornamento VPS)
./deploy.sh -m "Messaggio di commit"

# Solo aggiornamento VPS (senza commit/push)
./deploy.sh -s

# Solo commit/push GitHub (senza deploy VPS)
./deploy.sh -g

# Deploy interattivo (chiede il messaggio di commit)
./deploy.sh
```

### Setup Locale

```bash
# Crea virtual environment
python3 -m venv venv
source venv/bin/activate  # su Windows: venv\Scripts\activate

# Installa dipendenze
pip install -r requirements.txt

# Configura ambiente
cp .env.example .env
# Modifica .env con le tue credenziali

# Migrazione database
python manage.py migrate

# Crea superuser
python manage.py createsuperuser

# Avvia server di sviluppo
python manage.py runserver
```

Applicazione disponibile su: http://localhost:8000

## 📦 Funzionalità

### Gestione Preventivi
- ✅ Creazione, modifica, visualizzazione ed eliminazione preventivi
- ✅ Numero preventivo e revisione con vincolo di unicità
- ✅ Stati: Bozza, Inviato, Accettato, Rifiutato
- ✅ Riferimento clienti dall'anagrafica condivisa del Portale (UUID)

### Struttura Preventivo
- **Sezioni**: raggruppamento logico delle voci (es. Hardware, Installazione)
- **Voci**: descrizione dettagliata con:
  - Marca e specifiche tecniche
  - Immagine prodotto
  - Quantità e unità di misura
  - Prezzo unitario e prezzo scontato
  - Totale riga automatico
  - Opzione "escluso da totale" per voci descrittive

### Catalogo Prodotti
- 📚 Database prodotti riutilizzabili
- 🔄 Prefill automatico voci da catalogo
- 💾 Salvataggio voce in catalogo (icona su ogni voce)
- 🖼️ Immagini prodotto

### Generazione PDF
- 📄 PDF professionale con layout formattato
- 🖼️ Immagini voci integrate
- 💰 Totali per sezione e totale generale
- 💸 Prezzi scontati con barrato sul prezzo originale
- 📋 Condizioni di fornitura personalizzabili
- 🏢 Footer con indirizzo FBO Solution
- 📄 Gestione corretta paginazione

## 🔧 Tecnologie

- **Backend**: Django 5.1
- **Database**: SQLite (locale) / PostgreSQL (produzione)
- **PDF**: WeasyPrint
- **Server**: Gunicorn + Nginx
- **Deploy**: VPS Ubuntu con systemd

## 📁 Struttura Progetto

```
FBOPreventivi/
├── accounts/           # Gestione utenti e autenticazione
├── preventivi/         # App principale
│   ├── models.py      # Modelli: Cliente, Preventivo, Sezione, Voce, Prodotto
│   ├── views.py       # Viste CRUD e generazione PDF
│   ├── forms.py       # Form Django
│   └── portal_client.py # Client API per integrazione Portale
├── templates/          # Template HTML
├── static/            # File statici (CSS, JS, immagini)
├── media/             # Upload utente (immagini prodotti/voci)
├── deploy/            # File configurazione VPS
│   ├── README.md
│   ├── preventivi-web.service
│   ├── nginx-preventivi.conf
│   └── nginx-preventivi-ip-provisional.conf
├── deploy.sh          # Script deploy automatico
├── requirements.txt   # Dipendenze Python
├── .env.example       # Template variabili ambiente
└── manage.py
```

## 🌐 Deploy VPS

L'applicazione è deployata su VPS dedicato:
- **URL**: https://94.177.161.127:8445
- **Certificato**: Self-signed (IP nudo)
- **Service**: systemd `preventivi-web.service`
- **Web Server**: Nginx reverse proxy
- **User sistema**: `preventivi`

### Requisiti Sistema (VPS)

```bash
# Librerie per WeasyPrint (generazione PDF)
apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libcairo2
```

Vedi documentazione completa in `deploy/README.md`

## 🔐 Configurazione Ambiente

Variabili principali in `.env`:

```bash
# Django
DJANGO_SECRET_KEY=         # Generare con: python -c "import secrets; print(secrets.token_urlsafe(32))"
DJANGO_DEBUG=true          # false in produzione
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1

# API interna (per Portale)
INTERNAL_API_TOKEN=        # Token autenticazione API accounts/

# Integrazione Portale (anagrafica clienti)
PORTAL_INTERNAL_BASE_URL=  # URL loopback Portale (es. https://127.0.0.1:8443)
PORTAL_API_TOKEN=          # Token API Portale (clienti/api/internal/)
PORTAL_PUBLIC_URL=         # URL pubblico Portale (per link UI)
```

## 📝 Cronologia Sviluppo

- ✅ Scaffold iniziale Django
- ✅ Modello dati (Cliente, Preventivo, Sezione, Voce)
- ✅ Viste CRUD e generazione PDF
- ✅ Catalogo prodotti riutilizzabile
- ✅ Immagini nelle voci
- ✅ Totali per sezione
- ✅ File deploy VPS
- ✅ Fix sovrapposizione PDF
- ✅ Pulsante "Salva in catalogo" su ogni voce
- ✅ Eliminazione preventivi/voci dall'elenco
- ✅ Integrazione anagrafica clienti Portale
- ✅ Correzione footer PDF con indirizzo FBO Solution

## 📄 Licenza

Proprietario: FBO Solution

---

**Sviluppato da**: Fabrizio Lomazzi (f.lomazzi@gmail.com)  
**Repository**: https://github.com/lomax73/FBOPreventivi
