from django import forms

from .models import Cliente, Preventivo, Prodotto, SezionePreventivo, VoceProventivo


class ProdottoForm(forms.ModelForm):
    class Meta:
        model = Prodotto
        fields = ['descrizione', 'marca', 'specifiche', 'immagine', 'unita_misura', 'prezzo_unitario', 'note']
        widgets = {
            'specifiche': forms.Textarea(attrs={'rows': 3}),
            'note': forms.Textarea(attrs={'rows': 2}),
        }


class ClienteForm(forms.ModelForm):
    class Meta:
        model = Cliente
        fields = ['ragione_sociale', 'indirizzo', 'cap', 'citta', 'provincia', 'piva', 'email', 'telefono', 'note']


class PreventivoForm(forms.ModelForm):
    data = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Preventivo
        fields = [
            'numero', 'revisione', 'cliente', 'data',
            'oggetto_titolo', 'oggetto_righe', 'condizioni_fornitura', 'stato',
        ]
        widgets = {
            'oggetto_righe': forms.Textarea(attrs={'rows': 3}),
            'condizioni_fornitura': forms.Textarea(attrs={'rows': 4}),
        }


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
