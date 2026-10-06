import gzip
import io
import json
import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.import_stj import normalize
from backend.server import app

class ImportTests(unittest.TestCase):
    def test_metadata_and_original_ementa(self):
        r = normalize({'id': '99', 'ementa': 'CONSUMIDOR.\nTexto original.', 'dataDecisao': '20260102', 'siglaClasse': 'REsp', 'numeroProcesso': '123', 'numeroRegistro': '202600000001', 'dataPublicacao': 'DJe DATA:03/01/2026'}, {'id': 'r', 'url': 'https://dadosabertos.web.stj.jus.br/f.json', 'name': '20260831.json'}, {'name': 'conjunto', 'license_id': 'cc-by'})
        self.assertEqual(r['ementa'], 'CONSUMIDOR.\nTexto original.')
        self.assertEqual(r['date'], '2026-01-02')
        self.assertEqual(r['area'], '')
        self.assertIn('num_registro=202600000001', r['fullTextUrl'])
    def test_missing_text_rejected(self):
        with self.assertRaises(ValueError):
            normalize({'id': '99'}, {}, {})
    def request(self, body, origin='https://amcreis.github.io'):
        raw = json.dumps(body).encode()
        status = []
        output = app({'REQUEST_METHOD': 'POST', 'PATH_INFO': '/api/tjdft/search', 'CONTENT_LENGTH': str(len(raw)), 'wsgi.input': io.BytesIO(raw), 'HTTP_ORIGIN': origin}, lambda s,h: status.append((s,h)))
        return status[0], json.loads(b''.join(output))
    def test_invalid_query_and_origin(self):
        self.assertEqual(self.request({'query': 'x'*241})[0][0], '400 Bad Request')
        self.assertEqual(self.request({'query': 'fraude', 'page': -1})[0][0], '400 Bad Request')
        self.assertEqual(self.request({'query': 'fraude'}, 'https://other.invalid')[0][0], '403 Forbidden')
    def test_official_response_and_secret_exclusion(self):
        class Remote:
            def __enter__(self): return self
            def __exit__(self,*a): pass
            def read(self,*a): return json.dumps({'hits': {'value': 3}, 'registros': [{'uuid': '1','processo':'123','ementa':'Texto','segredoJustica':False},{'uuid':'2','segredoJustica':True}]}).encode()
        with patch('backend.server.urllib.request.urlopen', return_value=Remote()):
            status, data = self.request({'query': 'teste fixture único','page':0,'size':6})
        self.assertEqual(status[0], '200 OK')
        self.assertIn(('Access-Control-Allow-Origin','https://amcreis.github.io'),status[1])
        self.assertEqual(data['total'],3)
        self.assertEqual(len(data['records']),1)
        self.assertNotIn('segredoJustica',data['records'][0])

if __name__ == '__main__': unittest.main()
