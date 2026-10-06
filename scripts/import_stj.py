"""Importa arquivos oficiais do STJ. Sem scraping de portais de pesquisa."""
import argparse
import concurrent.futures
import datetime as dt
import gzip
import hashlib
import json
import pathlib
import re
import time
import urllib.parse
import urllib.request

PORTAL = 'https://dadosabertos.web.stj.jus.br'
ORGANS = ['corte-especial', 'primeira-secao', 'segunda-secao', 'terceira-secao',
          'primeira-turma', 'segunda-turma', 'terceira-turma', 'quarta-turma',
          'quinta-turma', 'sexta-turma']
MAX_FILE = 40 * 1024 * 1024

def download(url, cache):
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != 'https' or parsed.hostname != 'dadosabertos.web.stj.jus.br':
        raise ValueError('Fonte fora do portal oficial permitido')
    key = hashlib.sha256(url.encode()).hexdigest()
    path = cache / key
    if path.exists() and not parsed.path.startswith('/api/3/action/') and time.time() - path.stat().st_mtime < 86400:
        return path.read_bytes()
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Juriscreis/1.0 (pesquisa academica; dados abertos)'})
            with urllib.request.urlopen(req, timeout=90) as response:
                if urllib.parse.urlparse(response.url).hostname != parsed.hostname:
                    raise ValueError('Redirecionamento fora da fonte oficial')
                raw = response.read(MAX_FILE + 1)
            if len(raw) > MAX_FILE:
                raise ValueError('Arquivo excede limite de segurança da importação gratuita')
            temp = path.with_suffix('.tmp')
            temp.write_bytes(raw)
            temp.replace(path)
            return raw
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1 + attempt)

def plain(value):
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value).strip()

def normalize(row, resource, package):
    ementa = plain(row.get('ementa'))
    identifier = plain(row.get('id'))
    if not identifier or not ementa:
        raise ValueError('Registro sem identificador ou ementa')
    raw_date = plain(row.get('dataDecisao'))
    date = dt.datetime.strptime(raw_date, '%Y%m%d').date().isoformat() if re.fullmatch(r'\d{8}', raw_date) else ''
    reference = ' '.join(filter(None, [plain(row.get('siglaClasse')), plain(row.get('numeroProcesso'))]))
    organ = plain(row.get('nomeOrgaoJulgador'))
    # O ramo não é fornecido nesses arquivos. Não inventamos uma classificação.
    heading = ementa.split('\n')[0].strip()
    title = reference or 'Acórdão STJ ' + identifier
    snippet = re.sub(r'\s+', ' ', ementa).strip()
    pub_match = re.search(r'\d{2}/\d{2}/\d{4}', plain(row.get('dataPublicacao')))
    register = plain(row.get('numeroRegistro'))
    source = resource['url']
    full_url = ''
    if register and pub_match:
        full_url = 'https://scon.stj.jus.br/SCON/GetInteiroTeorDoAcordao?' + urllib.parse.urlencode({'num_registro': register, 'dt_publicacao': pub_match.group()})
    return {'id': 'stj-acordao-' + identifier, 'court': 'STJ', 'reference': reference,
            'title': title, 'heading': heading, 'summary': snippet[:450] + ('…' if len(snippet) > 450 else ''),
            'ementa': ementa, 'decision': plain(row.get('decisao')), 'date': date,
            'publication': plain(row.get('dataPublicacao')), 'organ': organ,
            'relator': plain(row.get('ministroRelator')), 'register': register,
            'area': '', 'tags': [], 'type': plain(row.get('tipoDeDecisao')) or 'Acórdão',
            'source': source, 'fullTextUrl': full_url, 'sourceLabel': 'STJ · Arquivo oficial de dados abertos',
            'dataset': package['name'], 'resourceId': resource['id'],
            'resourceName': resource.get('name'), 'license': package.get('license_id'),
            'note': 'Ementa original importada do arquivo oficial. O recorte de cada conjunto e a data de extração estão disponíveis em Cobertura.'}

def ingest(organ, cache, months):
    pid = 'espelhos-de-acordaos-' + organ
    package = json.loads(download(PORTAL + '/api/3/action/package_show?' + urllib.parse.urlencode({'id': pid}), cache))['result']
    if package.get('license_id') != 'cc-by':
        raise ValueError(pid + ': licença não reconhecida; revise a fonte')
    resources = sorted([r for r in package['resources'] if r.get('format', '').upper() == 'JSON'
                        and re.fullmatch(r'\d{8}\.json', r.get('name', ''))], key=lambda r: r['name'])[-months:]
    if not resources:
        raise ValueError(pid + ': nenhum arquivo JSON de espelhos encontrado')
    result = {}
    rejected = 0
    for resource in resources:
        raw = download(resource['url'], cache)
        rows = json.loads(raw.decode('utf-8-sig'))
        if not isinstance(rows, list):
            raise ValueError(pid + ': formato inesperado')
        for row in rows:
            try:
                record = normalize(row, resource, package)
                result[record['id']] = record
            except (ValueError, TypeError):
                rejected += 1
    coverage = {'court': 'STJ', 'dataset': pid, 'label': package['title'], 'status': 'partial',
                'records': len(result), 'rejected': rejected, 'license': package['license_id'],
                'catalogUrl': PORTAL + '/dataset/' + pid,
                'resources': [{'name': r['name'], 'id': r['id'], 'url': r['url']} for r in resources]}
    print(json.dumps({'dataset': pid, 'records': len(result), 'rejected': rejected}, ensure_ascii=False), flush=True)
    return result, coverage

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='data')
    parser.add_argument('--cache', default='.source-cache')
    parser.add_argument('--months', type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.months <= 12:
        parser.error('O recorte gratuito permite entre 1 e 12 arquivos mensais por conjunto')
    cache = pathlib.Path(args.cache)
    out = pathlib.Path(args.output)
    cache.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    records, sources = {}, []
    # Falha em qualquer fonte impede a publicação de um manifesto novo incompleto.
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        for result, coverage in pool.map(lambda organ: ingest(organ, cache, args.months), ORGANS):
            records.update(result)
            sources.append(coverage)
    rows = sorted(records.values(), key=lambda r: (r['date'], r['id']), reverse=True)
    if not rows:
        raise ValueError('A importação retornou uma base vazia')
    chunks = []
    for i in range(0, len(rows), 350):
        payload = json.dumps(rows[i:i+350], ensure_ascii=False, separators=(',', ':')).encode()
        compressed = gzip.compress(payload, mtime=0)
        digest = hashlib.sha256(compressed).hexdigest()
        filename = 'stj-' + digest[:16] + '.json.gz'
        (out / filename).write_bytes(compressed)
        chunks.append({'file': filename, 'records': len(rows[i:i+350]), 'sha256': digest, 'bytes': len(compressed)})
    manifest = {'schemaVersion': 1, 'generatedAt': dt.datetime.now(dt.timezone.utc).isoformat(),
                'total': len(rows), 'court': 'STJ', 'coverage': 'partial', 'monthsPerDataset': args.months,
                'scope': 'Espelhos de acórdãos: os últimos ' + str(args.months) + ' arquivos JSON mensais publicados em cada um dos 10 conjuntos. Não inclui o ZIP histórico nem o acervo integral do STJ.',
                'dateMin': min(r['date'] for r in rows if r['date']), 'dateMax': max(r['date'] for r in rows if r['date']),
                'license': 'CC BY — atribuição ao Superior Tribunal de Justiça', 'sources': sources, 'chunks': chunks}
    temp = out / 'manifest.json.tmp'
    temp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    temp.replace(out / 'manifest.json')
    # Arquivos imutáveis só são removidos depois que o novo manifesto está pronto.
    wanted = {x['file'] for x in chunks}
    for old in out.glob('stj-*.json.gz'):
        if old.name not in wanted:
            old.unlink()
    print(json.dumps({'total': len(rows), 'shards': len(chunks), 'compressedBytes': sum(c['bytes'] for c in chunks)}), flush=True)

if __name__ == '__main__':
    main()
