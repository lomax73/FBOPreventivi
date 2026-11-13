import io
import shutil
import tempfile
import uuid
from datetime import date
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import AllegatoPreventivo, Preventivo

TMP = tempfile.mkdtemp()


def _png():
    buf = io.BytesIO()
    Image.new('RGB', (4, 4), 'red').save(buf, 'PNG')
    return buf.getvalue()


@override_settings(ALLEGATI_ROOT=Path(TMP))
class AllegatiTests(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TMP, ignore_errors=True)

    def setUp(self):
        self.user = get_user_model().objects.create_user('t', password='x')
        self.preventivo = Preventivo.objects.create(numero='1_26', cliente_id=uuid.uuid4(), data=date.today())
        self.url = reverse('allegato-create', args=[self.preventivo.pk])

    def _upload(self, name, content, **extra):
        data = {'tipo': 'fornitore', 'titolo': 'Fornitore X', 'file': SimpleUploadedFile(name, content), **extra}
        return self.client.post(self.url, data)

    def test_richiede_login(self):
        r = self._upload('a.pdf', b'%PDF-1.4 x')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/login/', r['Location'])
        self.assertEqual(AllegatoPreventivo.objects.count(), 0)

    def test_upload_pdf_e_immagine(self):
        self.client.force_login(self.user)
        self.assertEqual(self._upload('Offerta Rossi.pdf', b'%PDF-1.4 x').status_code, 302)
        self.assertEqual(self._upload('foto.png', _png(), tipo='appunti').status_code, 302)
        pdf, img = AllegatoPreventivo.objects.order_by('pk')
        self.assertTrue(pdf.is_pdf and img.is_immagine)
        self.assertEqual(pdf.nome_originale, 'Offerta Rossi.pdf')
        self.assertEqual(pdf.caricato_da, self.user)
        self.assertNotIn('Rossi', pdf.file.name)

    def test_rifiuta_formati_e_contenuti_non_validi(self):
        self.client.force_login(self.user)
        self.assertEqual(self._upload('x.exe', b'MZ').status_code, 200)
        self.assertEqual(self._upload('x.html', b'<script>').status_code, 200)
        self.assertEqual(self._upload('finto.pdf', b'<html>').status_code, 200)
        self.assertEqual(self._upload('finta.png', b'non immagine').status_code, 200)
        self.assertEqual(AllegatoPreventivo.objects.count(), 0)

    def test_rifiuta_file_troppo_grande(self):
        self.client.force_login(self.user)
        r = self._upload('big.pdf', b'%PDF-' + b'0' * AllegatoPreventivo.DIMENSIONE_MAX)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(AllegatoPreventivo.objects.count(), 0)

    def test_download_protetto_e_inline(self):
        self.client.force_login(self.user)
        self._upload('a.pdf', b'%PDF-1.4 x')
        a = AllegatoPreventivo.objects.get()
        url = reverse('allegato-file', args=[a.pk])
        r = self.client.get(url)
        self.assertEqual(r['Content-Type'], 'application/pdf')
        self.assertTrue(r['Content-Disposition'].startswith('inline'))
        self.assertEqual(r['X-Frame-Options'], 'SAMEORIGIN')
        self.assertEqual(b''.join(r.streaming_content), b'%PDF-1.4 x')
        r.close()
        r = self.client.get(url + '?download=1')
        self.assertTrue(r['Content-Disposition'].startswith('attachment'))
        r.close()
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_elimina_rimuove_il_file_dal_disco(self):
        self.client.force_login(self.user)
        self._upload('a.pdf', b'%PDF-1.4 x')
        a = AllegatoPreventivo.objects.get()
        path = Path(a.file.path)
        self.assertTrue(path.exists())
        self.client.post(reverse('allegato-delete', args=[a.pk]))
        self.assertFalse(path.exists())

    def test_dettaglio_mostra_allegati(self):
        self.client.force_login(self.user)
        self._upload('a.pdf', b'%PDF-1.4 x')
        r = self.client.get(reverse('preventivo-detail', args=[self.preventivo.pk]))
        self.assertContains(r, 'Fornitore X')
        self.assertContains(r, 'preview-dialog')


class StatoTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user('t', password='x')
        self.p = Preventivo.objects.create(numero='2_26', cliente_id=uuid.uuid4(), data=date.today())
        self.url = reverse('preventivo-cambia-stato', args=[self.p.pk])
        self.detail = reverse('preventivo-detail', args=[self.p.pk])

    def test_richiede_login(self):
        self.assertEqual(self.client.post(self.url, {'stato': 'accettato'}).status_code, 302)
        self.p.refresh_from_db()
        self.assertEqual(self.p.stato, 'bozza')

    def test_cambia_stato_e_mostra_banner(self):
        self.client.force_login(self.user)
        self.assertNotContains(self.client.get(self.detail), 'PREVENTIVO CONFERMATO')
        self.client.post(self.url, {'stato': 'accettato'})
        self.p.refresh_from_db()
        self.assertEqual(self.p.stato, 'accettato')
        self.assertContains(self.client.get(self.detail), 'PREVENTIVO CONFERMATO')

    def test_stato_non_valido_e_get_rifiutati(self):
        self.client.force_login(self.user)
        self.client.post(self.url, {'stato': 'boh'})
        self.p.refresh_from_db()
        self.assertEqual(self.p.stato, 'bozza')
        self.assertEqual(self.client.get(self.url).status_code, 405)


class SezioniConfermateTests(TestCase):
    def setUp(self):
        from decimal import Decimal
        from .models import SezionePreventivo, VoceProventivo
        self.user = get_user_model().objects.create_user('t', password='x')
        self.p = Preventivo.objects.create(numero='3_26', cliente_id=uuid.uuid4(), data=date.today())
        self.a = SezionePreventivo.objects.create(preventivo=self.p, titolo='A')
        self.b = SezionePreventivo.objects.create(preventivo=self.p, titolo='B')
        VoceProventivo.objects.create(sezione=self.a, descrizione='x', quantita=1, prezzo_unitario=Decimal('100'))
        VoceProventivo.objects.create(sezione=self.b, descrizione='y', quantita=2, prezzo_unitario=Decimal('50'))

    def test_totale_senza_conferme_e_complessivo(self):
        self.assertEqual(self.p.totale, 200)
        self.assertFalse(self.p.ha_sezioni_confermate)

    def test_totale_solo_sezioni_confermate(self):
        self.client.force_login(self.user)
        self.client.post(reverse('sezione-toggle-confermata', args=[self.b.pk]))
        p = Preventivo.objects.get(pk=self.p.pk)
        self.assertEqual(p.totale, 100)
        self.assertEqual(p.totale_complessivo, 200)
        r = self.client.get(reverse('preventivo-detail', args=[p.pk]))
        self.assertContains(r, 'Totale confermato')
        self.client.post(reverse('sezione-toggle-confermata', args=[self.b.pk]))
        self.assertEqual(Preventivo.objects.get(pk=self.p.pk).totale, 200)

    def test_toggle_richiede_login_e_post(self):
        url = reverse('sezione-toggle-confermata', args=[self.a.pk])
        self.assertEqual(self.client.post(url).status_code, 302)
        self.a.refresh_from_db()
        self.assertFalse(self.a.confermata)
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(url).status_code, 405)

    def test_excel_solo_sezioni_confermate(self):
        import openpyxl
        self.client.force_login(self.user)
        self.client.post(reverse('sezione-toggle-confermata', args=[self.b.pk]))
        r = self.client.get(reverse('preventivo-excel', args=[self.p.pk]))
        rows = list(openpyxl.load_workbook(io.BytesIO(r.content)).active.values)
        self.assertEqual([row[0] for row in rows[1:-1]], ['y'])
        self.assertEqual(rows[-1][-1], 100)


    def test_sezione_disattiva_esclusa_da_totali_excel_pdf(self):
        import openpyxl
        self.client.force_login(self.user)
        self.client.post(reverse('sezione-toggle-attiva', args=[self.b.pk]))
        p = Preventivo.objects.get(pk=self.p.pk)
        self.assertEqual(p.totale, 100)
        self.assertEqual(p.totale_complessivo, 100)
        r = self.client.get(reverse('preventivo-excel', args=[p.pk]))
        rows = list(openpyxl.load_workbook(io.BytesIO(r.content)).active.values)
        self.assertEqual([row[0] for row in rows[1:-1]], ['x'])
        pdf = self.client.get(reverse('preventivo-pdf', args=[p.pk]))
        self.assertEqual(pdf.status_code, 200)
        self.assertNotIn(b'Disattivata', pdf.content)

    def test_sezione_confermata_ma_disattiva_non_conta(self):
        self.client.force_login(self.user)
        self.client.post(reverse('sezione-toggle-confermata', args=[self.b.pk]))
        self.client.post(reverse('sezione-toggle-attiva', args=[self.b.pk]))
        p = Preventivo.objects.get(pk=self.p.pk)
        self.assertFalse(p.ha_sezioni_confermate)
        self.assertEqual(p.totale, 100)


    def test_totale_confermato_concordato(self):
        import openpyxl
        from decimal import Decimal
        self.client.force_login(self.user)
        url = reverse('sezione-totale-confermato', args=[self.b.pk])
        self.client.post(reverse('sezione-toggle-confermata', args=[self.b.pk]))
        self.client.post(url, {'totale_confermato': '90,50'})
        p = Preventivo.objects.get(pk=self.p.pk)
        self.assertEqual(p.totale, Decimal('90.50'))        # accordo, non il calcolo (100)
        self.assertEqual(p.totale_complessivo, 200)
        r = self.client.get(reverse('preventivo-excel', args=[p.pk]))
        rows = list(openpyxl.load_workbook(io.BytesIO(r.content)).active.values)
        self.assertEqual(rows[-1][-1], Decimal('90.50'))
        self.assertEqual(sum(row[-1] for row in rows[1:-1]), Decimal('90.50'))  # le righe sommano
        # svuotando il campo si torna al calcolo
        self.client.post(url, {'totale_confermato': ''})
        self.assertEqual(Preventivo.objects.get(pk=self.p.pk).totale, 100)

    def test_totale_confermato_ignorato_se_sezione_non_confermata_e_no_negativi(self):
        from decimal import Decimal
        self.client.force_login(self.user)
        url = reverse('sezione-totale-confermato', args=[self.b.pk])
        self.client.post(url, {'totale_confermato': '10'})
        self.assertEqual(Preventivo.objects.get(pk=self.p.pk).totale, 200)  # non confermata: vale il calcolo
        self.client.post(url, {'totale_confermato': '-5'})
        self.b.refresh_from_db()
        self.assertEqual(self.b.totale_confermato, Decimal('10'))
        self.client.post(url, {'totale_confermato': 'abc'})
        self.b.refresh_from_db()
        self.assertEqual(self.b.totale_confermato, Decimal('10'))
