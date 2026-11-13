import uuid
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse

CONDIZIONI_FORNITURA_DEFAULT = (
    "Consegna inclusa\n"
    "Iva esclusa\n"
    "Pagamento Riba o BB a 30 GGDF"
)


class Preventivo(models.Model):
    class Stato(models.TextChoices):
        BOZZA = 'bozza', 'Bozza'
        INVIATO = 'inviato', 'Inviato'
        ACCETTATO = 'accettato', 'Accettato'
        RIFIUTATO = 'rifiutato', 'Rifiutato'

    numero = models.CharField(max_length=20, help_text="Es. 1045_26")
    revisione = models.CharField(max_length=20, blank=True, default='1.0')
    descrizione_interna = models.CharField(
        max_length=200, blank=True,
        help_text="Descrizione breve per identificare rapidamente il preventivo (es. 'WiFi sede Milano'). Non compare nel PDF.",
    )
    progetto = models.CharField(
        max_length=200, blank=True,
        help_text="Nome del progetto/commessa, usato per raggruppare i preventivi correlati nell'elenco.",
    )
    cliente_id = models.UUIDField(
        help_text="Riferimento al cliente nell'anagrafica condivisa del Portale (clienti/api/internal/).",
    )
    data = models.DateField()
    oggetto_titolo = models.CharField(max_length=200, blank=True, default='Offerta')
    oggetto_righe = models.TextField(blank=True, help_text="Un punto elenco per riga.")
    condizioni_fornitura = models.TextField(
        blank=True, default=CONDIZIONI_FORNITURA_DEFAULT, help_text="Un punto elenco per riga.",
    )
    stato = models.CharField(max_length=20, choices=Stato.choices, default=Stato.BOZZA)
    creato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='preventivi_creati',
    )
    creato_il = models.DateTimeField(auto_now_add=True)
    aggiornato_il = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-data', '-numero']
        constraints = [
            models.UniqueConstraint(fields=['numero', 'revisione'], name='unique_preventivo_numero_revisione'),
        ]

    def __str__(self):
        return f"{self.numero} rev. {self.revisione}"

    def get_absolute_url(self):
        return reverse('preventivo-detail', args=[self.pk])

    @property
    def totale(self):
        return sum(
            (sezione.totale for sezione in self.sezioni.all()),
            Decimal('0'),
        )


class CategoriaProdotto(models.Model):
    """Categoria personalizzabile per organizzare il catalogo prodotti (es. Telecamere, Networking)."""

    nome = models.CharField(max_length=100, unique=True)
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordine', 'nome']
        verbose_name_plural = 'categorie prodotto'

    def __str__(self):
        return self.nome


class Prodotto(models.Model):
    """Voce di catalogo riutilizzabile per prefillare le voci ricorrenti (es. antenne Ubiquiti, switch)."""

    categoria = models.ForeignKey(
        CategoriaProdotto, on_delete=models.SET_NULL, null=True, blank=True, related_name='prodotti',
    )
    descrizione = models.CharField(max_length=255)
    marca = models.CharField(max_length=100, blank=True)
    specifiche = models.TextField(blank=True, help_text="Un punto elenco per riga.")
    immagine = models.ImageField(upload_to='preventivi/catalogo/', blank=True, null=True)
    unita_misura = models.CharField(max_length=20, blank=True, default='Cad')
    prezzo_unitario = models.DecimalField(
        'Prezzo di listino', max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))],
    )
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['categoria__ordine', 'categoria__nome', 'descrizione']

    def __str__(self):
        return self.descrizione


class SezionePreventivo(models.Model):
    preventivo = models.ForeignKey(Preventivo, on_delete=models.CASCADE, related_name='sezioni')
    titolo = models.CharField(max_length=200)
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordine', 'id']

    def __str__(self):
        return self.titolo

    @property
    def totale(self):
        return sum((voce.totale_riga for voce in self.voci.all()), Decimal('0'))


class VoceProventivo(models.Model):
    sezione = models.ForeignKey(SezionePreventivo, on_delete=models.CASCADE, related_name='voci')
    prodotto = models.ForeignKey(
        Prodotto, on_delete=models.SET_NULL, null=True, blank=True, related_name='voci',
        help_text="Prodotto di catalogo da cui è stata prefillata questa voce (solo riferimento, non vincolante).",
    )
    ordine = models.PositiveIntegerField(default=0)
    descrizione = models.CharField(max_length=255)
    marca = models.CharField(max_length=100, blank=True)
    specifiche = models.TextField(blank=True, help_text="Un punto elenco per riga.")
    immagine = models.ImageField(upload_to='preventivi/voci/', blank=True, null=True)
    quantita = models.DecimalField(
        max_digits=10, decimal_places=2, default=1, validators=[MinValueValidator(Decimal('0'))],
    )
    unita_misura = models.CharField(max_length=20, blank=True, default='Cad')
    prezzo_unitario = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0'))],
    )
    prezzo_scontato = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[MinValueValidator(Decimal('0'))],
        help_text="Se valorizzato, il prezzo unitario viene mostrato barrato nel PDF.",
    )
    note = models.TextField(blank=True, help_text="Es. \"a vostro carico\", \"manodopera a consuntivo 35€/h\".")
    escluso_da_totale = models.BooleanField(
        default=False,
        help_text="Voce descritta nel preventivo ma non conteggiata nel totale (es. a carico del cliente).",
    )
    in_evidenza = models.BooleanField(
        default=False,
        help_text="Evidenzia la voce con uno sfondo tenue, sia nella scheda che nel PDF, per attirare l'attenzione del cliente.",
    )

    class Meta:
        ordering = ['ordine', 'id']

    def __str__(self):
        return self.descrizione

    @property
    def immagine_uri(self):
        """URI file:// per l'uso nel PDF (WeasyPrint), non l'URL pubblico
        servito da Django."""
        if not self.immagine:
            return None
        return Path(self.immagine.path).as_uri()

    @property
    def prezzo_effettivo(self):
        return self.prezzo_scontato if self.prezzo_scontato is not None else self.prezzo_unitario

    @property
    def totale_riga(self):
        if self.escluso_da_totale:
            return Decimal('0')
        return self.prezzo_effettivo * self.quantita


def allegati_storage():
    # Callable: così la migrazione non incorpora il percorso della macchina.
    return FileSystemStorage(location=settings.ALLEGATI_ROOT)


def allegato_upload_to(instance, filename):
    # Nome casuale su disco: niente collisioni né caratteri strani.
    # Il nome originale resta nel campo nome_originale.
    return f"{uuid.uuid4().hex}{Path(filename).suffix.lower()}"


class AllegatoPreventivo(models.Model):
    class Tipo(models.TextChoices):
        FORNITORE = 'fornitore', 'Preventivo fornitore'
        APPUNTI = 'appunti', 'Appunti'

    ESTENSIONI_IMMAGINE = ('.jpg', '.jpeg', '.png', '.gif', '.webp')
    ESTENSIONI_CONSENTITE = ('.pdf',) + ESTENSIONI_IMMAGINE
    DIMENSIONE_MAX = 10 * 1024 * 1024  # in linea con client_max_body_size di nginx

    preventivo = models.ForeignKey(Preventivo, on_delete=models.CASCADE, related_name='allegati')
    tipo = models.CharField(max_length=20, choices=Tipo.choices, default=Tipo.FORNITORE)
    titolo = models.CharField(
        max_length=200, blank=True,
        help_text="Es. nome del fornitore o argomento dell'appunto. Se vuoto si usa il nome del file.",
    )
    note = models.TextField(blank=True)
    file = models.FileField(upload_to=allegato_upload_to, storage=allegati_storage)
    nome_originale = models.CharField(max_length=255, blank=True)
    caricato_da = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='allegati_caricati',
    )
    caricato_il = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['tipo', '-caricato_il']

    def __str__(self):
        return self.titolo or self.nome_originale

    @property
    def estensione(self):
        return Path(self.file.name).suffix.lower()

    @property
    def is_pdf(self):
        return self.estensione == '.pdf'

    @property
    def is_immagine(self):
        return self.estensione in self.ESTENSIONI_IMMAGINE

    @property
    def etichetta(self):
        return self.titolo or self.nome_originale


@receiver(post_delete, sender=AllegatoPreventivo)
def elimina_file_allegato(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
