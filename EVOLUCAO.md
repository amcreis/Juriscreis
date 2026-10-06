# Como chegar à pesquisa nacional integrada

Esta entrega é a interface funcional e uma coleção inicial. O objetivo final é que o estudante digite um tema e receba jurisprudência de diversos tribunais dentro do site, sem precisar sair para um buscador externo.

## 1. Levantamento das fontes

Para cada tribunal, documentar o endereço do acervo, os formatos de dados, formas de pesquisa, disponibilidade de APIs/arquivos, restrições de acesso e limites de uso. Confirmar a autorização e as condições técnicas para ingestão. A presença de um tribunal no diretório não confirma uma integração.

Priorizar um piloto com STF, STJ, TST e TJSP. Só marcar uma fonte como integrada depois que a importação, a pesquisa e a identificação da origem estiverem verificadas. Não contornar bloqueios, CAPTCHA ou acessos protegidos.

## 2. Normalizar os documentos

Manter identificador do tribunal e da decisão, número do processo, classe, órgão julgador, relator, datas de julgamento/publicação, ementa original, inteiro teor disponível, temas, URL oficial, data de coleta e histórico de atualização. Separar o conteúdo oficial dos resumos escritos para estudantes.

Deduplicar por tribunal, processo e identificador da decisão. Um processo pode ter várias decisões; o número do processo, sozinho, não é uma chave suficiente. Registrar revisões e cancelamentos quando a fonte disponibilizar esses dados. Evitar dados pessoais desnecessários e não importar conteúdo sob sigilo.

## 3. Importar e indexar

Um coletor deve executar fora do navegador, buscar dados autorizados, validar e normalizar os registros. Não basta usar a API do DataJud: o CNJ descreve metadados processuais, não o acervo integral de textos de decisões.

Para pequenos lotes públicos autorizados, o coletor pode gerar arquivos estáticos pesquisáveis no GitHub, com uma rotina de atualização no GitHub Actions. Antes de fazer isso, medir volume, tempo de coleta e limite de publicação. Segredos ficam no armazenamento de secrets do serviço, nunca no repositório nem na interface.

Para acervos nacionais de grande porte, manter o código no GitHub e usar um serviço externo de backend com banco e índice de busca. O GitHub Pages pode servir a interface, mas não executa um servidor de consultas nem uma coleta contínua. Selecionar o serviço após dimensionar volume e orçamento; nenhuma contratação foi feita nesta entrega.

## 4. Pesquisa por temas

Primeiro implementar busca textual com relevância, vocabulário jurídico e filtros de tribunal, ramo, órgão e datas. Depois avaliar busca semântica com um conjunto de consultas reais de estudantes, comparando resultados contra decisões relevantes já verificadas.

Uma busca por IA só deve aparecer como tal quando realmente existir. Mostrar a origem do documento e distinguir súmula, acórdão, decisão monocrática e precedente qualificado. Um resumo não substitui a decisão e não estabelece, sozinho, vigência ou força vinculante.

## Critério de conclusão

O portal só poderá anunciar cobertura nacional integrada quando houver fontes reais operantes para os tribunais anunciados, rastreabilidade dos registros, monitoramento de falhas e atualização verificável. Até lá, a interface deve mostrar a cobertura efetiva e permitir continuar a pesquisa nas fontes oficiais.
