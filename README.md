# Juris Estudo

Portal de pesquisa jurídica para estudantes de Direito, preparado para GitHub Pages. HTML, CSS e JavaScript, sem dependências de produção, chaves de API ou instalação obrigatória.

## O que funciona nesta versão

- Pesquisa local em sete resumos editoriais verificados em fontes oficiais: seis súmulas do STJ e o Tema 786 do STF, referenciado por página oficial do TJDFT.
- Pesquisa por termos, todos os termos, qualquer termo ou expressão exata; normalização de acentos e algumas relações explícitas de palavras.
- Filtros de tribunal e ramo do Direito, ordenação e fichas de estudo com origem identificada.
- Diretório de 92 tribunais: STF, quatro tribunais superiores, 27 TJs, seis TRFs, 24 TRTs, 27 TREs e três TJMs estaduais.
- Busca externa pelo Google, limitada a páginas `jus.br`, com tema e tribunal escolhidos; atalhos para bases oficiais.
- Interface responsiva, navegação por teclado e URLs que preservam os filtros da pesquisa.

**O objetivo nacional ainda não está completo.** O diretório não significa que os 92 acervos estejam integrados. Os sete registros são resumos, não uma base de ementas ou inteiro teor. A pesquisa externa pode retornar notícias ou omitir julgados não indexados. Não há ingestão, atualização automática, backend ou busca por IA. Não é preciso fingir uma cobertura inexistente para usar a interface e evoluir o projeto.

## Publicar pelo GitHub sem programar

1. Extraia o ZIP em uma pasta no computador. Não envie o ZIP fechado para o repositório.
2. No GitHub, crie um repositório chamado `juris-estudo`. Para usar GitHub Pages com GitHub Free, escolha um repositório público. A disponibilidade em repositórios privados depende do plano.
3. Clique em **Add file → Upload files** e envie `index.html`, a pasta `assets`, `README.md` e os demais arquivos extraídos. Mantenha `index.html` na raiz do repositório, não dentro de outra pasta `juris-estudo`.
4. Confirme com **Commit changes**.
5. Abra **Settings → Pages**. Em **Build and deployment → Source**, escolha **Deploy from a branch**. Selecione a branch que contém os arquivos (normalmente `main`) e a pasta **/(root)**. Clique em **Save**.
6. Aguarde o GitHub concluir a publicação. O endereço será exibido em **Settings → Pages**. Abra esse endereço, e não o endereço do repositório.

Esse caminho não depende de enviar a pasta oculta `.github`. Se o site apresentar erro 404, confira se `index.html` está na raiz da branch selecionada e se a publicação terminou.

## Publicação automática com GitHub Actions

O projeto também inclui `.github/workflows/pages.yml`. Se enviar o projeto por Git/GitHub Desktop preservando essa pasta, escolha **Settings → Pages → Source → GitHub Actions**. O workflow testa a pesquisa, prepara apenas os arquivos do site e publica a cada envio à branch `main`. Se sua branch principal tiver outro nome, ajuste o campo `branches` do workflow.

Não é necessário criar um token pessoal: a publicação usa o `GITHUB_TOKEN` temporário do workflow. Não coloque senhas ou credenciais no JavaScript público.

## Abrir no computador

Abra `index.html` no navegador. Os dados estão em um arquivo JavaScript e não dependem de `fetch`, portanto essa versão funciona também diretamente no computador.

Para servir por HTTP, se tiver Python instalado:

```sh
python -m http.server 8000
```

Abra `http://localhost:8000`.

## Estrutura

| Arquivo | Função |
| --- | --- |
| `index.html` | Estrutura da interface |
| `assets/style.css` | Aparência e adaptação para celular |
| `assets/data.js` | Seleção de precedentes e diretório de tribunais |
| `assets/search.js` | Motor de busca local e preparação da consulta externa |
| `assets/app.js` | Filtros, resultados e fichas |
| `tests/search.test.cjs` | Verificações de pesquisa e integridade dos dados |
| `.github/workflows/pages.yml` | Teste e publicação no Pages |
| `EVOLUCAO.md` | Etapas para integrar os acervos nacionais |

## Adicionar jurisprudência

Adicione um registro ao array `JURIS_DATA` de `assets/data.js`, com identificador único, sigla do tribunal, referência, natureza, ramo, título, resumo, nota de estudo, data de julgamento (`AAAA-MM-DD`), órgão, termos e URL oficial. Use apenas fontes conferidas. Não chame o resumo editorial de ementa oficial.

Exemplo de campos (valores ilustrativos, não inserir como jurisprudência real):

```js
{
  id: 'identificador-unico',
  court: 'TJSP',
  reference: 'Número conferido na fonte',
  type: 'Acórdão',
  area: 'Civil',
  title: 'Tema central',
  summary: 'Resumo escrito após ler a decisão.',
  note: 'Limites e contexto relevantes.',
  date: '2026-10-06',
  organ: 'Órgão conferido',
  tags: ['termo central'],
  source: 'URL HTTPS oficial verificada',
  sourceLabel: 'Tribunal · Acórdão oficial'
}
```

Atualize também a data de conferência exibida na interface quando realizar uma revisão da coleção. Essa data é de consulta, não uma garantia de vigência do entendimento.

## Verificação

Com Node.js 22 ou posterior:

```sh
node tests/search.test.cjs
node --check assets/app.js
```

O teste cobre acentos, termos relacionados, correspondência, filtros, ordenação, consulta externa, integridade dos registros e referências de arquivos. A publicação real depende da configuração e permissões do repositório. A interface WebMCP tem detecção de suporte; sua validação em navegador compatível não foi realizada nesta entrega.

## Fontes e documentação

Referências da coleção estão em cada registro e aparecem nas fichas. Consulta inicial: 06/10/2026.

- [API Pública do DataJud — CNJ](https://www.cnj.jus.br/sistemas/datajud/api-publica/): metadados de capas e movimentações processuais; não é uma base completa de ementas.
- [Banco Nacional de Precedentes — CNJ](https://www.cnj.jus.br/tecnologia-da-informacao-e-comunicacao/justica-4-0/banco-nacional-de-precedentes-bnp/): precedentes enviados pelos tribunais.
- [Jurisprudência do STJ](https://scon.stj.jus.br/SCON/).
- [Tema 786 do STF em página oficial do TJDFT](https://www.tjdft.jus.br/consultas/jurisprudencia/jurisprudencia-em-temas/precedentes-qualificados-na-visao-do-tjdft/direito-administrativo-e-constitucional/direitos-fundamentais/tema-786-do-stf-direito-ao-esquecimento).
- [Configurar a publicação do GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site).
- [Workflows personalizados do GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages).
