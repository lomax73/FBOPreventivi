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
