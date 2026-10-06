"""Consultas restritas às fontes públicas de jurisprudência do TJDFT e TST."""
import collections
import json
import os
import threading
import time
import urllib.error
import urllib.request
import urllib.parse
import datetime
import re

ENDPOINT = 'https://jurisdf.tjdft.jus.br/api/v1/pesquisa'
TST_ENDPOINT = 'https://jurisprudencia-backend.tst.jus.br/rest/pesquisa-textual'
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', 'https://amcreis.github.io')
cache = collections.OrderedDict()
lock = threading.Lock()
slots = threading.BoundedSemaphore(3)

def normalize_tst(row):
    if not isinstance(row, dict):
        raise ValueError('Registro do TST inválido')
    if row.get('segredoJustica') is True or row.get('sigiloso') is True:
        return None
    kind = row.get('tipo') or {}
    court = row.get('orgao') or {}
    if kind.get('codigoTipoJurisprudencia') != 'ACORDAO' or court.get('sigla') != 'TST':
        raise ValueError('Fonte retornou documento fora do escopo TST/ACORDAO')
    identifier = row.get('id')
    if not isinstance(identifier, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', identifier):
        raise ValueError('Identificador inválido')
    portal = 'https://jurisprudencia.tst.jus.br/'
    full_text = ''
    # Mesmo endereço e parâmetros usados pelo portal oficial para acórdãos.
    try:
        published = datetime.date.fromisoformat(str(row.get('dtaPublicacao', ''))[:10])
        params = {key: row[source] for key, source in [('anoProcInt', 'anoProcInt'), ('numProcInt', 'numProcInt'), ('nia', 'numInterno')]}
        if not all(type(v) is int and v > 0 for v in params.values()):
            raise ValueError('Metadados incompletos')
        params['dtaPublicacaoStr'] = published.strftime('%d/%m/%Y') + ' 07:00:00'
        full_text = 'https://consultadocumento.tst.jus.br/consultaDocumento/acordao.do?' + urllib.parse.urlencode(params)
    except (ValueError, KeyError, TypeError):
        pass
    ementa = row.get('ementa') or ''
    decision = row.get('dispositivo') or ''
    if not isinstance(ementa, str) or not isinstance(decision, str):
        raise ValueError('Texto inválido')
    return {'id': 'tst-' + identifier, 'court': 'TST', 'reference': row.get('numFormatado') or identifier,
            'title': row.get('numFormatado') or ('Acórdão ' + identifier), 'ementa': ementa,
            'decision': decision, 'date': row.get('dtaJulgamento') or '', 'publication': row.get('dtaPublicacao') or '',
            'organ': (row.get('orgaoJudicante') or {}).get('descricao') or '', 'relator': row.get('nomRelator') or '',
            'source': portal, 'fullTextUrl': full_text, 'sourceLabel': 'Pesquisa oficial do TST · ' + identifier,
            'note': 'Acórdão retornado pela pesquisa textual oficial do TST. A consulta pesquisa o texto do julgado; consulte a fonte para conferir o inteiro teor.'}

def query_tst(query, page, size):
    payload = {'e': query, 'ou': '', 'termoExato': '', 'naoContem': '', 'ementa': '', 'dispositivo': '',
               'numeracaoUnica': {'numero': '', 'ano': '', 'digito': '', 'orgao': '5', 'tribunal': '', 'vara': ''},
               'orgaosJudicantes': [], 'ministros': [], 'convocados': [], 'classesProcessuais': [],
               'codigosClassesPrecedentes': [], 'indicadores': [], 'assuntos': [], 'tipos': ['ACORDAO'], 'orgao': 'TST',
               'publicacaoInicial': '', 'publicacaoFinal': '', 'julgamentoInicial': '', 'julgamentoFinal': '', 'ordenacao': ''}
    url = TST_ENDPOINT + '/' + str(page * size + 1) + '/' + str(size)
    request = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json', 'User-Agent': 'Juriscreis/1.0'}, method='POST')
    with urllib.request.urlopen(request, timeout=35) as remote:
        raw = remote.read(8 * 1024 * 1024 + 1)
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError('Resposta excedeu o limite')
    source = json.loads(raw)
    if not isinstance(source, dict) or not isinstance(source.get('registros'), list) or type(source.get('totalRegistros')) is not int or source['totalRegistros'] < 0:
        raise ValueError('Resposta do TST fora do formato esperado')
    records = []
    for wrapper in source['registros']:
        row = normalize_tst(wrapper.get('registro') if isinstance(wrapper, dict) else None)
        if row is not None:
            records.append(row)
    return {'source': 'TST', 'total': source['totalRegistros'], 'page': page, 'size': size, 'records': records,
            'searchedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}

def response(start, code, data, origin):
    payload = json.dumps(data, ensure_ascii=False).encode()
    headers = [('Content-Type', 'application/json; charset=utf-8'), ('Content-Length', str(len(payload))),
               ('Cache-Control', 'no-store'), ('Vary', 'Origin')]
    if origin == ALLOWED_ORIGIN:
        headers.extend([('Access-Control-Allow-Origin', ALLOWED_ORIGIN),
                        ('Access-Control-Allow-Methods', 'POST, GET, OPTIONS'),
                        ('Access-Control-Allow-Headers', 'Content-Type')])
    start(code, headers)
    return [payload]

def app(environ, start_response):
    origin = environ.get('HTTP_ORIGIN', '')
    method = environ.get('REQUEST_METHOD')
    path = environ.get('PATH_INFO')
    if path == '/health' and method == 'GET':
        return response(start_response, '200 OK', {'status': 'ok', 'sources': ['TJDFT', 'TST'], 'nationalCoverage': 'partial'}, origin)
    if path not in ['/api/tjdft/search', '/api/tst/search']:
        return response(start_response, '404 Not Found', {'error': 'Rota inexistente'}, origin)
    source_name = 'TST' if path == '/api/tst/search' else 'TJDFT'
    if origin and origin != ALLOWED_ORIGIN:
        return response(start_response, '403 Forbidden', {'error': 'Origem não permitida'}, origin)
    if method == 'OPTIONS':
        return response(start_response, '200 OK', {}, origin)
    if method != 'POST':
        return response(start_response, '405 Method Not Allowed', {'error': 'Use POST'}, origin)
    try:
        length = int(environ.get('CONTENT_LENGTH') or '0')
        if not 0 < length <= 4096:
            raise ValueError('Corpo inválido')
        data = json.loads(environ['wsgi.input'].read(length))
        if not isinstance(data, dict) or set(data) - {'query', 'page', 'size'}:
            raise ValueError('Parâmetros inválidos')
        query = data.get('query', '')
        page, size = data.get('page', 0), data.get('size', 6)
        if not isinstance(query, str) or not 1 <= len(query.strip()) <= 240:
            raise ValueError('Informe um termo de até 240 caracteres')
        if type(page) is not int or not 0 <= page <= 10000 or type(size) is not int or not 1 <= size <= 20:
            raise ValueError('Página ou tamanho inválido')
    except (ValueError, TypeError, json.JSONDecodeError):
        return response(start_response, '400 Bad Request', {'error': 'Parâmetros inválidos'}, origin)
    key = (source_name, query.strip(), page, size)
    with lock:
        entry = cache.get(key)
        if entry and time.monotonic() - entry[0] < 60:
            cache.move_to_end(key)
            return response(start_response, '200 OK', entry[1], origin)
    if not slots.acquire(blocking=False):
        return response(start_response, '429 Too Many Requests', {'error': 'Consulta ocupada. Tente novamente em instantes.'}, origin)
    try:
        if source_name == 'TST':
            result = query_tst(query.strip(), page, size)
            with lock:
                cache[key] = (time.monotonic(), result)
                cache.move_to_end(key)
                while len(cache) > 24:
                    cache.popitem(last=False)
            return response(start_response, '200 OK', result, origin)
        payload = json.dumps({'query': query.strip(), 'pagina': page, 'tamanho': size, 'termosAcessorios': []}).encode()
        request = urllib.request.Request(ENDPOINT, data=payload, headers={'Content-Type': 'application/json', 'User-Agent': 'Juriscreis/1.0'}, method='POST')
        with urllib.request.urlopen(request, timeout=35) as remote:
            raw = remote.read(8 * 1024 * 1024 + 1)
        if len(raw) > 8 * 1024 * 1024:
            raise ValueError('Resposta excedeu o limite')
        source = json.loads(raw)
        if not isinstance(source.get('registros'), list):
            raise ValueError('Resposta da fonte fora do formato esperado')
        hits = source.get('hits', 0)
        total = hits.get('value', 0) if isinstance(hits, dict) else hits
        records = []
        for row in source['registros']:
            if row.get('segredoJustica') is True:
                continue
            records.append({key: row.get(key) for key in ['uuid', 'identificador', 'base', 'subbase', 'dataJulgamento', 'dataPublicacao', 'ementa', 'decisao', 'processo', 'nomeRelator', 'descricaoOrgaoJulgador', 'possuiInteiroTeor']})
        result = {'source': 'TJDFT', 'total': total, 'page': page, 'size': size, 'records': records,
                  'searchedAt': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}
        with lock:
            cache[key] = (time.monotonic(), result)
            cache.move_to_end(key)
            while len(cache) > 24:
                cache.popitem(last=False)
        return response(start_response, '200 OK', result, origin)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError, TypeError, KeyError, AttributeError):
        return response(start_response, '502 Bad Gateway', {'error': 'A fonte oficial está indisponível. Tente novamente mais tarde.'}, origin)
    finally:
        slots.release()

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    make_server('0.0.0.0', int(os.environ.get('PORT', '8000')), app).serve_forever()
