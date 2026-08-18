# Deploy sul VPS

Stesso pattern già in uso per MKRemote, il Portale e Collaudi Fibra (repo
separato, utente di sistema dedicato, venv proprio). Al momento nessun
dominio è configurato sul VPS: si usa l'IP nudo su una porta dedicata
(vedi `nginx-preventivi-ip-provisional.conf`), da sostituire con un
sottodominio quando ci sarà un dominio reale.

**Dipendenza in più rispetto al Portale**: il PDF è generato con
WeasyPrint, che richiede librerie di sistema (non pacchetti Python) —
già installate sul VPS per Collaudi Fibra, ma da verificare/installare
se questo è il primo deploy WeasyPrint sul server:

```
apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libcairo2
```

## Provisioning iniziale (una tantum)

```
# da root sul VPS
adduser --system --group --home /opt/preventivi preventivi
mkdir -p /opt/preventivi/app
chown preventivi:preventivi /opt/preventivi/app

apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libcairo2

sudo -u preventivi git clone https://github.com/lomax73/FBOPreventivi.git /opt/preventivi/app
cd /opt/preventivi/app
sudo -u preventivi python3 -m venv venv
sudo -u preventivi venv/bin/pip install -r requirements.txt

cp .env.example .env   # poi valorizzare DJANGO_SECRET_KEY, DJANGO_ALLOWED_HOSTS, INTERNAL_API_TOKEN
                        # DJANGO_DEBUG=false — .env.example lo lascia a "true", NON dimenticarlo:
                        # con DEBUG=True qualunque eccezione espone tutte le variabili
                        # d'ambiente (SECRET_KEY, INTERNAL_API_TOKEN, credenziali cifrate)
sudo -u preventivi venv/bin/python manage.py migrate
sudo -u preventivi venv/bin/python manage.py collectstatic --noinput
sudo -u preventivi venv/bin/python manage.py createsuperuser
mkdir -p /opt/preventivi/app/media && chown preventivi:preventivi /opt/preventivi/app/media

cp deploy/preventivi-web.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now preventivi-web.service

# Certificato self-signed (IP nudo, nessun dominio):
mkdir -p /etc/ssl/preventivi
openssl req -x509 -nodes -days 3650 -newkey rsa:2048 \
    -keyout /etc/ssl/preventivi/selfsigned.key \
    -out /etc/ssl/preventivi/selfsigned.crt \
    -subj "/CN=94.177.161.127"

cp deploy/nginx-preventivi-ip-provisional.conf /etc/nginx/sites-available/preventivi
ln -s /etc/nginx/sites-available/preventivi /etc/nginx/sites-enabled/preventivi
nginx -t && systemctl reload nginx
ufw allow 8445/tcp comment 'FBOPreventivi HTTPS'
```

Ricorda anche: `chmod 751 /opt/preventivi` (come per `/opt/portal` e
`/opt/fiberreport`) perché Nginx/www-data possa attraversare la home e
servire `staticfiles/` e `media/` (le immagini prodotto/voce caricate).

## API interna di gestione utenti (per il Portale)

Come per le altre app, questa app espone `accounts/` sotto
`api/internal/` per permettere al Portale FBO di creare/modificare/
eliminare utenti da remoto. **Va esposta solo in locale**, mai
pubblicamente — il location block dedicato è già incluso in
`nginx-preventivi-ip-provisional.conf`, prima di quello generico
`location /`.

1. `INTERNAL_API_TOKEN` va già valorizzato in `.env` (vedi sopra).
2. `systemctl restart preventivi-web.service` dopo aver aggiornato `.env`.
3. Configurare lo stesso token nel Portale (admin → AppLink di
   FBOPreventivi → campo "API token"), insieme a `internal_base_url =
   https://127.0.0.1:8445`.

## Deploy di un aggiornamento

```
ssh mkremote-vps
cd /opt/preventivi/app
sudo -u preventivi git pull origin main
sudo -u preventivi venv/bin/pip install -r requirements.txt
sudo -u preventivi venv/bin/python manage.py migrate
sudo -u preventivi venv/bin/python manage.py collectstatic --noinput
systemctl restart preventivi-web.service
```
