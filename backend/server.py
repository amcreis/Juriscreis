"""Proxy restrito à API pública de jurisprudência do TJDFT (WSGI)."""
import collections
import json
import os
import threading
import time
import urllib.error
import urllib.request

ENDPOINT = 'https://jurisdf.tjdft.jus.br/api/v1/pesquisa'
ALLOWED_ORIGIN = os.environ.get('ALLOWED_ORIGIN', 'https://amcreis.github.io')
cache = collections.OrderedDict()
lock = threading.Lock()
slots = threading.BoundedSemaphore(3)

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
        return response(start_response, '200 OK', {'status': 'ok', 'sources': ['TJDFT'], 'nationalCoverage': 'partial'}, origin)
    if path != '/api/tjdft/search':
        return response(start_response, '404 Not Found', {'error': 'Rota inexistente'}, origin)
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
    key = (query.strip(), page, size)
    with lock:
        entry = cache.get(key)
        if entry and time.monotonic() - entry[0] < 60:
            cache.move_to_end(key)
            return response(start_response, '200 OK', entry[1], origin)
    if not slots.acquire(blocking=False):
        return response(start_response, '429 Too Many Requests', {'error': 'Consulta ocupada. Tente novamente em instantes.'}, origin)
    try:
        payload = json.dumps({'query': key[0], 'pagina': page, 'tamanho': size, 'termosAcessorios': []}).encode()
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
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return response(start_response, '502 Bad Gateway', {'error': 'A fonte oficial está indisponível. Tente novamente mais tarde.'}, origin)
    finally:
        slots.release()

if __name__ == '__main__':
    from wsgiref.simple_server import make_server
    make_server('0.0.0.0', int(os.environ.get('PORT', '8000')), app).serve_forever()
