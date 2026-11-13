from pathlib import Path

from django import forms
from PIL import Image, UnidentifiedImageError

from . import portal_client
from .models import AllegatoPreventivo, CategoriaProdotto, Preventivo, Prodotto, SezionePreventivo, VoceProventivo


class ProdottoForm(forms.ModelForm):
    class Meta:
        model = Prodotto
        fields = ['categoria', 'descrizione', 'marca', 'specifiche', 'immagine', 'unita_misura', 'prezzo_unitario', 'note']
        widgets = {
            'specifiche': forms.Textarea(attrs={'rows': 3}),
            'note': forms.Textarea(attrs={'rows': 2}),
        }


class CategoriaProdottoForm(forms.ModelForm):
    class Meta:
        model = CategoriaProdotto
        fields = ['nome', 'ordine']


class PreventivoForm(forms.ModelForm):
    data = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    cliente = forms.ChoiceField(label='Cliente')

    class Meta:
        model = Preventivo
        fields = [
            'numero', 'revisione', 'descrizione_interna', 'progetto', 'data',
            'oggetto_titolo', 'oggetto_righe', 'condizioni_fornitura', 'stato',
        ]
        widgets = {
            'oggetto_righe': forms.Textarea(attrs={'rows': 3}),
            'condizioni_fornitura': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            clienti = portal_client.list_clienti()
        except portal_client.PortalUnavailableError as exc:
            self.fields['cliente'].choices = []
            self.fields['cliente'].help_text = (
                f'Impossibile contattare l\'anagrafica clienti nel Portale: {exc}'
            )
        else:
            self.fields['cliente'].choices = [(c['id'], c['ragione_sociale']) for c in clienti]
        if self.instance and self.instance.pk and self.instance.cliente_id:
            self.fields['cliente'].initial = str(self.instance.cliente_id)

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.cliente_id = self.cleaned_data['cliente']
        if commit:
            instance.save()
        return instance


class SezionePreventivoForm(forms.ModelForm):
    class Meta:
        model = SezionePreventivo
        fields = ['titolo', 'ordine']


class VoceProventivoForm(forms.ModelForm):
    class Meta:
        model = VoceProventivo
        fields = [
            'descrizione', 'marca', 'specifiche', 'immagine',
            'quantita', 'unita_misura', 'prezzo_unitario', 'prezzo_scontato',
            'note', 'escluso_da_totale', 'ordine',
        ]
        widgets = {
            'specifiche': forms.Textarea(attrs={'rows': 3}),
            'note': forms.Textarea(attrs={'rows': 2}),
        }


class AllegatoPreventivoForm(forms.ModelForm):
    class Meta:
        model = AllegatoPreventivo
        fields = ['tipo', 'titolo', 'note', 'file']
        widgets = {'note': forms.Textarea(attrs={'rows': 2})}

    def clean_file(self):
        f = self.cleaned_data['file']
        ext = Path(f.name).suffix.lower()
        if ext not in AllegatoPreventivo.ESTENSIONI_CONSENTITE:
            raise forms.ValidationError('Formato non consentito: usa PDF, JPG, PNG, GIF o WEBP.')
        if f.size > AllegatoPreventivo.DIMENSIONE_MAX:
            raise forms.ValidationError('File troppo grande (massimo 10 MB).')
        # Controllo sul contenuto reale, non solo sull'estensione.
        f.seek(0)
        if ext == '.pdf':
            if f.read(5) != b'%PDF-':
                raise forms.ValidationError('Il file non è un PDF valido.')
        else:
            try:
                Image.open(f).verify()
            except (UnidentifiedImageError, OSError, SyntaxError):
                raise forms.ValidationError('Il file non è un\'immagine valida.')
        f.seek(0)
        return f


class SezioneTotaleConfermatoForm(forms.ModelForm):
    class Meta:
        model = SezionePreventivo
        fields = ['totale_confermato']

    def __init__(self, data=None, *args, **kwargs):
        if data is not None:
            data = data.copy()
            valore = (data.get('totale_confermato') or '').strip().replace(',', '.')
            data['totale_confermato'] = valore
        super().__init__(data, *args, **kwargs)
