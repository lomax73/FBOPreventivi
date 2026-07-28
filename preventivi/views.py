from dataclasses import dataclass
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.files.base import ContentFile
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.utils.text import slugify
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView
from weasyprint import HTML

from . import portal_client
from .forms import PreventivoForm, ProdottoForm, SezionePreventivoForm, VoceProventivoForm
from .models import Preventivo, Prodotto, SezionePreventivo, VoceProventivo


@dataclass
class ClienteInfo:
    """Dati del cliente risolti dall'anagrafica condivisa nel Portale,
    con gli stessi nomi di campo usati nei template quando qui c'era
    ancora un modello Cliente locale."""

    id: str = ''
    ragione_sociale: str = 'Cliente non disponibile'
    indirizzo: str = ''
    cap: str = ''
    citta: str = ''
    provincia: str = ''
    piva: str = ''
    email: str = ''
    telefono: str = ''
    note: str = ''

    def __str__(self):
        return self.ragione_sociale


def _attach_clienti(preventivi):
    """Risolve cliente_id -> dati cliente per una lista di preventivi con
    UNA sola chiamata al Portale (non una per riga). Se il Portale non
    risponde o il cliente non esiste più, ogni preventivo riceve comunque
    un ClienteInfo di fallback invece di far fallire la pagina."""
    preventivi = list(preventivi)
    try:
        by_id = {c['id']: c for c in portal_client.list_clienti()}
    except portal_client.PortalUnavailableError:
        by_id = {}
    for preventivo in preventivi:
        dati = by_id.get(str(preventivo.cliente_id))
        preventivo.cliente = ClienteInfo(**dati) if dati else ClienteInfo()
    return preventivi


class ProdottoListView(LoginRequiredMixin, ListView):
    model = Prodotto
    template_name = 'preventivi/prodotto_list.html'
    context_object_name = 'prodotti'


class ProdottoCreateView(LoginRequiredMixin, CreateView):
    model = Prodotto
    form_class = ProdottoForm
    template_name = 'preventivi/prodotto_form.html'
    success_url = reverse_lazy('prodotto-list')


class ProdottoUpdateView(LoginRequiredMixin, UpdateView):
    model = Prodotto
    form_class = ProdottoForm
    template_name = 'preventivi/prodotto_form.html'
    success_url = reverse_lazy('prodotto-list')


class ProdottoDeleteView(LoginRequiredMixin, DeleteView):
    model = Prodotto
    template_name = 'preventivi/prodotto_confirm_delete.html'
    success_url = reverse_lazy('prodotto-list')


class PreventivoListView(LoginRequiredMixin, ListView):
    model = Preventivo
    template_name = 'preventivi/quote_list.html'
    context_object_name = 'preventivi'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['preventivi'] = _attach_clienti(context['preventivi'])
        return context


class PreventivoCreateView(LoginRequiredMixin, CreateView):
    model = Preventivo
    form_class = PreventivoForm
    template_name = 'preventivi/preventivo_form.html'

    def form_valid(self, form):
        form.instance.creato_da = self.request.user
        return super().form_valid(form)


class PreventivoUpdateView(LoginRequiredMixin, UpdateView):
    model = Preventivo
    form_class = PreventivoForm
    template_name = 'preventivi/preventivo_form.html'


class PreventivoDeleteView(LoginRequiredMixin, DeleteView):
    model = Preventivo
    template_name = 'preventivi/preventivo_confirm_delete.html'
    success_url = reverse_lazy('quote-list')


class PreventivoDetailView(LoginRequiredMixin, DetailView):
    model = Preventivo
    template_name = 'preventivi/preventivo_detail.html'
    context_object_name = 'preventivo'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sezioni'] = self.object.sezioni.prefetch_related('voci')
        context['prodotti_catalogo'] = Prodotto.objects.all()
        _attach_clienti([self.object])
        return context


class SezionePreventivoCreateView(LoginRequiredMixin, CreateView):
    model = SezionePreventivo
    form_class = SezionePreventivoForm
    template_name = 'preventivi/sezione_form.html'

    def get_preventivo(self):
        return get_object_or_404(Preventivo, pk=self.kwargs['preventivo_pk'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['preventivo'] = self.get_preventivo()
        return context

    def form_valid(self, form):
        form.instance.preventivo = self.get_preventivo()
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('preventivo-detail', args=[self.object.preventivo_id])


class SezionePreventivoUpdateView(LoginRequiredMixin, UpdateView):
    model = SezionePreventivo
    form_class = SezionePreventivoForm
    template_name = 'preventivi/sezione_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['preventivo'] = self.object.preventivo
        return context

    def get_success_url(self):
        return reverse('preventivo-detail', args=[self.object.preventivo_id])


class SezionePreventivoDeleteView(LoginRequiredMixin, DeleteView):
    model = SezionePreventivo
    template_name = 'preventivi/sezione_confirm_delete.html'

    def get_success_url(self):
        return reverse('preventivo-detail', args=[self.object.preventivo_id])


class VoceProventivoCreateView(LoginRequiredMixin, CreateView):
    model = VoceProventivo
    form_class = VoceProventivoForm
    template_name = 'preventivi/voce_form.html'

    def get_sezione(self):
        return get_object_or_404(SezionePreventivo, pk=self.kwargs['sezione_pk'])

    def get_prodotto(self):
        prodotto_pk = self.request.POST.get('prodotto_pk') or self.request.GET.get('da_prodotto')
        return Prodotto.objects.filter(pk=prodotto_pk).first() if prodotto_pk else None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sezione'] = self.get_sezione()
        context['prodotto_pk'] = self.request.GET.get('da_prodotto', '')
        return context

    def get_initial(self):
        initial = super().get_initial()
        prodotto = self.get_prodotto()
        if prodotto:
            initial.update(
                descrizione=prodotto.descrizione, marca=prodotto.marca, specifiche=prodotto.specifiche,
                unita_misura=prodotto.unita_misura, prezzo_unitario=prodotto.prezzo_unitario, note=prodotto.note,
            )
        return initial

    def form_valid(self, form):
        form.instance.sezione = self.get_sezione()
        prodotto = self.get_prodotto()
        if prodotto:
            form.instance.prodotto = prodotto
            if prodotto.immagine and not form.instance.immagine:
                form.instance.immagine.save(
                    Path(prodotto.immagine.name).name, ContentFile(prodotto.immagine.read()), save=False,
                )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('preventivo-detail', args=[self.object.sezione.preventivo_id])


class VoceProventivoUpdateView(LoginRequiredMixin, UpdateView):
    model = VoceProventivo
    form_class = VoceProventivoForm
    template_name = 'preventivi/voce_form.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['sezione'] = self.object.sezione
        return context

    def get_success_url(self):
        return reverse('preventivo-detail', args=[self.object.sezione.preventivo_id])


class VoceProventivoDeleteView(LoginRequiredMixin, DeleteView):
    model = VoceProventivo
    template_name = 'preventivi/voce_confirm_delete.html'

    def get_success_url(self):
        return reverse('preventivo-detail', args=[self.object.sezione.preventivo_id])


@login_required
def voce_save_to_catalog(request, pk):
    voce = get_object_or_404(VoceProventivo, pk=pk)
    if request.method == 'POST':
        prodotto = Prodotto.objects.create(
            descrizione=voce.descrizione, marca=voce.marca, specifiche=voce.specifiche,
            unita_misura=voce.unita_misura, prezzo_unitario=voce.prezzo_unitario, note=voce.note,
        )
        if voce.immagine:
            prodotto.immagine.save(
                Path(voce.immagine.name).name, ContentFile(voce.immagine.read()), save=True,
            )
        messages.success(request, f'"{voce.descrizione}" salvata nel catalogo prodotti.')
        return redirect('preventivo-detail', pk=voce.sezione.preventivo_id)
    return render(request, 'preventivi/voce_save_to_catalog_confirm.html', {'voce': voce})


@login_required
def preventivo_duplica(request, pk):
    originale = get_object_or_404(Preventivo, pk=pk)
    if request.method != 'POST':
        return redirect('quote-list')

    revisione_copia = f'{originale.revisione}-copia'
    suffisso = 2
    while Preventivo.objects.filter(numero=originale.numero, revisione=revisione_copia).exists():
        revisione_copia = f'{originale.revisione}-copia{suffisso}'
        suffisso += 1

    copia = Preventivo.objects.create(
        numero=originale.numero,
        revisione=revisione_copia,
        descrizione_interna=originale.descrizione_interna,
        cliente_id=originale.cliente_id,
        data=originale.data,
        oggetto_titolo=originale.oggetto_titolo,
        oggetto_righe=originale.oggetto_righe,
        condizioni_fornitura=originale.condizioni_fornitura,
        creato_da=request.user,
    )

    for sezione in originale.sezioni.prefetch_related('voci'):
        nuova_sezione = SezionePreventivo.objects.create(
            preventivo=copia, titolo=sezione.titolo, ordine=sezione.ordine,
        )
        for voce in sezione.voci.all():
            nuova_voce = VoceProventivo(
                sezione=nuova_sezione,
                prodotto=voce.prodotto,
                ordine=voce.ordine,
                descrizione=voce.descrizione,
                marca=voce.marca,
                specifiche=voce.specifiche,
                quantita=voce.quantita,
                unita_misura=voce.unita_misura,
                prezzo_unitario=voce.prezzo_unitario,
                prezzo_scontato=voce.prezzo_scontato,
                note=voce.note,
                escluso_da_totale=voce.escluso_da_totale,
            )
            if voce.immagine:
                nuova_voce.immagine.save(
                    Path(voce.immagine.name).name, ContentFile(voce.immagine.read()), save=False,
                )
            nuova_voce.save()

    messages.success(request, f'Preventivo duplicato: {copia.numero} rev. {copia.revisione}.')
    return redirect('preventivo-update', pk=copia.pk)


def preventivo_pdf(request, pk):
    preventivo = get_object_or_404(
        Preventivo.objects.prefetch_related('sezioni__voci'), pk=pk,
    )
    _attach_clienti([preventivo])
    logo_path = Path(__file__).resolve().parent.parent / 'static' / 'img' / 'logo.svg'
    logo_uri = logo_path.as_uri() if logo_path.exists() else None
    html_string = render_to_string('preventivi/preventivo_pdf.html', {
        'preventivo': preventivo,
        'sezioni': preventivo.sezioni.all(),
        'logo_uri': logo_uri,
        'now': timezone.localtime(),
    })
    pdf_bytes = HTML(string=html_string, base_url=request.build_absolute_uri('/')).write_pdf()

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    filename = f'preventivo-{slugify(preventivo.numero)}-rev{slugify(preventivo.revisione)}.pdf'
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response
