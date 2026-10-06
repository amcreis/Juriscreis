# Integrações do Juriscreis

## Cobertura efetiva

O objetivo de integrar completamente todos os tribunais **não está concluído**. Esta versão acrescenta dados reais do STJ e um conector da API oficial do TJDFT, sem tratar o diretório de tribunais como base integrada.

| Fonte | Situação | Alcance |
| --- | --- | --- |
| STJ — dez conjuntos de espelhos de acórdãos | Importação verificada | Último arquivo mensal JSON de cada conjunto; 9.531 acórdãos na primeira importação |
| TJDFT — API pública de jurisprudência | Consulta direta ativada via https://juriscreis-api.onrender.com | Consulta sob demanda, com total e paginação fornecidos pela API |
| STF | Pesquisa externa oficial; acesso automático bloqueado nas fontes testadas | Nenhum documento importado; copiar tema e consultar no portal do STF |
| Demais tribunais | Sem conector verificado | Somente pesquisa externa no portal; não anunciados como integrados |

Os dados do STJ são uma seleção de espelhos tratados pela Secretaria de Jurisprudência. Nem mesmo baixar todo esse conjunto significa obter todos os julgados do tribunal. O JSON mensal é incremental; o ZIP mais antigo contém histórico. O recorte gratuito aqui importa apenas o último JSON mensal de cada conjunto. Não substitui esse histórico.

## Serviço gratuito do TJDFT

O serviço está ativo em https://juriscreis-api.onrender.com e configurado em `assets/integration-config.json`. A consulta real e a permissão de acesso do domínio do GitHub Pages foram verificadas.

### Recriar o serviço, se necessário

O código e a configuração já estão preparados em `backend/server.py` e `render.yaml`.

1. Abra [Implantar serviço do Juriscreis no Render](https://render.com/deploy?repo=https://github.com/amcreis/Juriscreis).
2. Entre ou crie sua conta. Se solicitado, autorize o acesso ao repositório `amcreis/Juriscreis`.
3. Confira que o único serviço é `juriscreis-api`, com plano **Free**. Não adicione banco de dados ou serviços pagos.
4. Confirme a criação do serviço e aguarde a implantação.
5. Copie a URL HTTPS atribuída pelo Render e forneça-a para configurar o site. Não é possível prever o endereço antes da criação.
6. Em `assets/integration-config.json`, defina `apiBase` com essa URL e mantenha `manifestUrl` como `data/manifest.json`.

Após a publicação da configuração, a seção TJDFT passa a consultar a API oficial. A fonte não permite a leitura direta a partir do domínio do GitHub Pages na verificação feita; o servidor intermediário resolve esse acesso sem esconder a origem. O servidor não contém chaves de API nem depende de banco de dados. Ele aceita consultas somente ao endpoint fixo do TJDFT, não funciona como proxy genérico e não registra os textos das pesquisas em logs próprios.

O plano gratuito do Render suspende serviços após inatividade, e a primeira consulta pode demorar. O cache é temporário e não há promessa de disponibilidade contínua. A API de origem também pode limitar, alterar ou interromper o acesso. Consulte as condições do plano na tela antes de criar a conta; nenhuma assinatura foi contratada por esta entrega.

## Atualizar o recorte do STJ

No GitHub, abra **Actions → Atualizar acervo oficial do STJ → Run workflow**. A rotina importa os arquivos oficiais e publica o novo recorte. A rotina é manual; não foi agendada. Uma falha de download impede substituir os dados por uma base incompleta.

Também é possível executar localmente:

```sh
python scripts/import_stj.py --output data --months 1
```

`--months` aceita de 1 a 12 arquivos mensais por conjunto. Isso amplia o recorte, mas exige mais memória e transferência no navegador. Não use essa opção para anunciar cobertura histórica completa. O site lê os arquivos comprimidos em um Web Worker, verifica os hashes e pesquisa o texto completo da ementa dentro do recorte. A busca por ramo fica indisponível nesses arquivos porque não foi fornecida uma classificação uniforme pela fonte.

## Verificação

```sh
node tests/search.test.cjs
node tests/worker.test.cjs
python -m unittest discover -s tests -p 'test_import.py'
```

O teste do worker usa os arquivos realmente importados. Os testes do servidor verificam parâmetros, CORS, resposta da API e exclusão de registros marcados como sigilosos. A implantação do serviço no Render depende da conta do proprietário e só é considerada concluída depois que sua URL responder a uma consulta real.

## O que falta para cobertura nacional completa

1. Mapear e verificar canais de acesso aos textos de cada tribunal. Uma API de metadados processuais não equivale a ementas e inteiro teor.
2. Para cada fonte acessível, criar um conector específico, deduplicar decisões, registrar origem e data de coleta, e verificar atualização e falhas.
3. Para acervos volumosos, usar armazenamento persistente e índice de busca no servidor. O navegador e o GitHub Pages não substituem essa infraestrutura.
4. Confirmar orçamento e capacidade antes de contratar serviços. A opção gratuita atual não dimensiona um acervo nacional completo.

## Referências oficiais

- [Catálogo de jurisprudência do STJ](https://dadosabertos.web.stj.jus.br/dataset/?groups=jurisprudencia).
- [Exemplo de conjunto e descrição do recorte — STJ](https://dadosabertos.web.stj.jus.br/dataset/espelhos-de-acordaos-terceira-secao).
- [API pública de jurisprudência — TJDFT](https://www.tjdft.jus.br/transparencia/tecnologia-da-informacao-e-comunicacao/dados-abertos/webservice-ou-api).
- [Documentação oficial da API do TJDFT](https://www.tjdft.jus.br/transparencia/tecnologia-da-informacao-e-comunicacao/dados-abertos/documentos/documentacao_api_seti_transparencia.pdf).
- [Planos gratuitos — Render](https://render.com/docs/free).
- [Implantar com blueprint — Render](https://render.com/docs/deploy-to-render).

## STF: limite verificado e próximo passo

Em 06/10/2026, as solicitações ao portal de jurisprudência e aos PDFs oficiais de súmulas retornaram HTTP 403 no ambiente de execução. Nenhuma proteção foi contornada. Não foi ativado um conector automático nem anunciada cobertura do acervo do STF.

Ao selecionar STF, o site oferece o tema pesquisado como texto, um botão de copiar e links para a pesquisa oficial e para as súmulas. Nenhuma consulta ao STF ocorre automaticamente. Esse acesso externo também está disponível na aba Busca nacional externa.

Para importar textos, é necessário obter uma fonte oficial acessível, um canal autorizado de acesso automatizado ou arquivos oficiais fornecidos pelo usuário. Uma eventual importação de súmulas deverá informar edição, origem e situação dos enunciados, preservando os cancelamentos e as alterações; ela não equivale ao acervo completo de acórdãos.
