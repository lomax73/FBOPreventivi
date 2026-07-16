from decimal import Decimal

from django.conf import settings
from django.db import models
from django.urls import reverse

CONDIZIONI_FORNITURA_DEFAULT = (
    "Consegna inclusa\n"
    "Iva esclusa\n"
    "Pagamento Riba o BB a 30 GGDF"
)


class Cliente(models.Model):
    ragione_sociale = models.CharField(max_length=200)
    indirizzo = models.CharField(max_length=255, blank=True)
    cap = models.CharField(max_length=10, blank=True)
    citta = models.CharField(max_length=100, blank=True)
    provincia = models.CharField(max_length=2, blank=True)
    piva = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    telefono = models.CharField(max_length=30, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['ragione_sociale']

    def __str__(self):
        return self.ragione_sociale


class Preventivo(models.Model):
    class Stato(models.TextChoices):
        BOZZA = 'bozza', 'Bozza'
        INVIATO = 'inviato', 'Inviato'
        ACCETTATO = 'accettato', 'Accettato'
        RIFIUTATO = 'rifiutato', 'Rifiutato'

    numero = models.CharField(max_length=20, help_text="Es. 1045_26")
    revisione = models.CharField(max_length=20, blank=True, default='1.0')
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name='preventivi')
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
        return f"{self.numero} rev. {self.revisione} — {self.cliente}"

    def get_absolute_url(self):
        return reverse('preventivo-detail', args=[self.pk])

    @property
    def totale(self):
        return sum(
            (voce.totale_riga for sezione in self.sezioni.all() for voce in sezione.voci.all()),
            Decimal('0'),
        )


class Prodotto(models.Model):
    """Voce di catalogo riutilizzabile per prefillare le voci ricorrenti (es. antenne Ubiquiti, switch)."""

    descrizione = models.CharField(max_length=255)
    marca = models.CharField(max_length=100, blank=True)
    specifiche = models.TextField(blank=True, help_text="Un punto elenco per riga.")
    immagine = models.ImageField(upload_to='preventivi/catalogo/', blank=True, null=True)
    unita_misura = models.CharField(max_length=20, blank=True, default='Cad')
    prezzo_unitario = models.DecimalField('Prezzo di listino', max_digits=10, decimal_places=2)
    note = models.TextField(blank=True)

    class Meta:
        ordering = ['descrizione']

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
    quantita = models.DecimalField(max_digits=10, decimal_places=2, default=1)
    unita_misura = models.CharField(max_length=20, blank=True, default='Cad')
    prezzo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    prezzo_scontato = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Se valorizzato, il prezzo unitario viene mostrato barrato nel PDF.",
    )
    note = models.TextField(blank=True, help_text="Es. \"a vostro carico\", \"manodopera a consuntivo 35€/h\".")
    escluso_da_totale = models.BooleanField(
        default=False,
        help_text="Voce descritta nel preventivo ma non conteggiata nel totale (es. a carico del cliente).",
    )

    class Meta:
        ordering = ['ordine', 'id']

    def __str__(self):
        return self.descrizione

    @property
    def prezzo_effettivo(self):
        return self.prezzo_scontato if self.prezzo_scontato is not None else self.prezzo_unitario

    @property
    def totale_riga(self):
        if self.escluso_da_totale:
            return Decimal('0')
        return self.prezzo_effettivo * self.quantita
