importScripts('search.js');
let data = null;
let loading = null;
async function load(manifestUrl) {
  if (data) return data;
  if (loading) return loading;
  loading = (async () => {
    const response = await fetch(manifestUrl, {cache: 'no-cache'});
    if (!response.ok) throw new Error('Não foi possível carregar a cobertura do STJ.');
    const manifest = await response.json();
    if (manifest.schemaVersion !== 1 || !Array.isArray(manifest.chunks) || manifest.total <= 0) throw new Error('Manifesto de dados inválido.');
    const base = new URL('.', new URL(manifestUrl, self.location.href));
    let records = [], next = 0, completed = 0;
    if (typeof DecompressionStream === 'undefined') throw new Error('Atualize seu navegador para pesquisar o acervo importado.');
    async function runner() {
      while (next < manifest.chunks.length) {
        const chunk = manifest.chunks[next++];
        const url = new URL(chunk.file, base);
        if (url.origin !== self.location.origin || !/^stj-[a-f0-9]{16}\.json\.gz$/.test(chunk.file)) throw new Error('Arquivo de dados inválido.');
        const r = await fetch(url);
        if (!r.ok) throw new Error('Um arquivo de jurisprudência não pôde ser carregado.');
        const compressed = await r.arrayBuffer();
        const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', compressed))].map(x=>x.toString(16).padStart(2,'0')).join('');
        if (hash !== chunk.sha256) throw new Error('Falha na integridade do arquivo de jurisprudência.');
        const json = await new Response(new Blob([compressed]).stream().pipeThrough(new DecompressionStream('gzip'))).json();
        if (!Array.isArray(json) || json.length !== chunk.records) throw new Error('Quantidade de registros inválida.');
        records.push(...json);
        postMessage({type:'progress', completed:++completed, total:manifest.chunks.length});
      }
    }
    await Promise.all([runner(), runner(), runner()]);
    if (records.length !== manifest.total) throw new Error('O acervo não foi carregado por completo.');
    data = records;
    return records;
  })().catch(e=>{loading=null;throw e;});
  return loading;
}
let newest = 0;
self.onmessage = async e => {
  const {id, opts, page, manifestUrl} = e.data;
  newest = id;
  try {
    const rows = await load(manifestUrl);
    if (id !== newest) return;
    const found = JurisSearch.search(rows, opts);
    const size = 6, pages = Math.max(1, Math.ceil(found.length/size));
    const currentPage = Math.min(Math.max(1, page), pages);
    postMessage({type:'results',id,total:found.length,page:currentPage,pages,records:found.slice((currentPage-1)*size,currentPage*size)});
  } catch (error) { if(id===newest) postMessage({type:'error',id,message:error.message}); }
};
