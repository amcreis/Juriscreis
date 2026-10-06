import gzip
import io
import json
import pathlib
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from scripts.import_stj import normalize
from backend.server import app, normalize_tst, cache

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
    def request(self, body, origin='https://amcreis.github.io', path='/api/tjdft/search'):
        raw = json.dumps(body).encode()
        status = []
        output = app({'REQUEST_METHOD': 'POST', 'PATH_INFO': path, 'CONTENT_LENGTH': str(len(raw)), 'wsgi.input': io.BytesIO(raw), 'HTTP_ORIGIN': origin}, lambda s,h: status.append((s,h)))
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

    def test_tst_original_text_and_official_link(self):
        row = {'id': 'abc123', 'tipo': {'codigoTipoJurisprudencia': 'ACORDAO'}, 'orgao': {'sigla': 'TST'},
               'ementa': 'HORAS EXTRAS.\nTexto original.', 'dispositivo': 'Negar provimento.',
               'dtaPublicacao': '2026-10-06T07:00:00-03', 'anoProcInt': 2026, 'numProcInt': 123, 'numInterno': 456,
               'codCPFSignatario': 'não publicar', 'inteiroTeorHtml': '<script>não publicar</script>'}
        record = normalize_tst(row)
        self.assertEqual(record['ementa'], row['ementa'])
        self.assertEqual(record['decision'], row['dispositivo'])
        self.assertIn('consultadocumento.tst.jus.br/consultaDocumento/acordao.do?', record['fullTextUrl'])
        self.assertIn('dtaPublicacaoStr=06%2F10%2F2026+07%3A00%3A00', record['fullTextUrl'])
        self.assertNotIn('codCPFSignatario', record)
        self.assertNotIn('inteiroTeorHtml', record)
        self.assertIsNone(normalize_tst({**row, 'sigiloso': True}))
        with self.assertRaises(ValueError):
            normalize_tst({**row, 'orgao': {'sigla': 'CSJT'}})

    def test_tst_pagination_scope_and_separate_cache(self):
        cache.clear()
        class Remote:
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def read(self, *a): return json.dumps({'totalRegistros': 40, 'registros': [{'registro': {
                'id': 'abc123', 'tipo': {'codigoTipoJurisprudencia': 'ACORDAO'}, 'orgao': {'sigla': 'TST'},
                'ementa': 'Texto oficial', 'numFormatado': 'RR - 123'}}]}).encode()
        with patch('backend.server.urllib.request.urlopen', return_value=Remote()) as call:
            status, data = self.request({'query': 'horas extras', 'page': 2, 'size': 6}, path='/api/tst/search')
            request = call.call_args.args[0]
            self.assertTrue(request.full_url.endswith('/rest/pesquisa-textual/13/6'))
            sent = json.loads(request.data)
            self.assertEqual(sent['tipos'], ['ACORDAO'])
            self.assertEqual(sent['orgao'], 'TST')
            self.assertEqual(sent['e'], 'horas extras')
        self.assertEqual(status[0], '200 OK')
        self.assertEqual(data['source'], 'TST')
        self.assertEqual(data['total'], 40)
        with patch('backend.server.query_tst') as query:
            self.assertEqual(self.request({'query': 'horas extras', 'page': 2, 'size': 6}, path='/api/tst/search')[1]['source'], 'TST')
            query.assert_not_called()
        with patch('backend.server.urllib.request.urlopen', return_value=Remote()) as call:
            self.request({'query': 'horas extras', 'page': 2, 'size': 6})
            self.assertIn('jurisdf.tjdft.jus.br', call.call_args.args[0].full_url)

    def test_tst_unavailable_is_not_empty_success(self):
        cache.clear()
        with patch('backend.server.query_tst', side_effect=ValueError('formato mudou')):
            status, data = self.request({'query': 'horas extras'}, path='/api/tst/search')
        self.assertEqual(status[0], '502 Bad Gateway')
        self.assertIn('error', data)
        self.assertEqual(self.request({'query': 'x'*241}, path='/api/tst/search')[0][0], '400 Bad Request')

if __name__ == '__main__': unittest.main()
