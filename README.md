## API_LITURGIA_DIARIA

@Josué.Santos

## Tecnologias
- Python
- Biblioteca Flask
- Biblioteca Beautiful Soup

## Objetivo
A API_LITURGIA_DIARIA visa disponibilizar via api as leituras para facilitar a criação de aplicações que almejam a evangelização.

## URL
https://api-liturgia-diaria.vercel.app/

## Parametros
https://api-liturgia-diaria.vercel.app/?date=2024-11-25

A rota raiz (`/`) usa a CNBB como fonte principal. Se ela estiver indisponível, a API tenta a Sagrada Liturgia e, em seguida, a Canção Nova. O parâmetro `date` aceita o formato `YYYY-MM-DD`.

## URL Canção Nova
https://api-liturgia-diaria.vercel.app/cn

## URL Canção Nova Santo do Dia
https://api-liturgia-diaria.vercel.app/santo-do-dia

## URL CNBB
https://api-liturgia-diaria.vercel.app/cnbb

Para consultar uma data específica, use o parâmetro `date` no formato `YYYY-MM-DD`:
https://api-liturgia-diaria.vercel.app/cnbb?date=2026-12-24

A rota informa `source` como `CNBB`, mantém os campos originais da fonte (inclusive `body` em HTML), exceto `filename`, e acrescenta `date_formatted`, `date_string`, `entry_title`, `readings` e `celebrations`. As leituras são listas organizadas por tipo para preservar repetições em celebrações especiais; `sections` mantém a ordem original. As leituras bíblicas incluem `pre`, `ref`, `start`, `text`, `text_array` e `footer` quando identificados no HTML, além de `footer_response` quando a fonte fornece essa resposta. `text_array` é uma lista ordenada de objetos `{ "verse": "...", "text": "..." }`, incluindo `verse: ""` para texto não numerado anterior aos versículos. Repetições e marcadores que indicam a mudança de capítulo (como `19,1` seguido por `2`) permanecem na ordem recebida. Os salmos incluem `ref`, `response` e `content_psalm` sem os marcadores finais `R.`, mantendo `text` integral. Os evangelhos agrupam a aclamação em `ref`, `head`, `head_response` e a preparação/proclamação em `pre`, `start`, `text`, `text_array` e `footer`.

## Visualizador HTML

O arquivo único `public/liturgia-cnbb.html` oferece um calendário navegável e exibe as leituras, salmos, aclamações e celebrações especiais usando a API. O endereço padrão é `https://api-liturgia-diaria.vercel.app`; ele pode ser alterado na própria página para usar outra API. O CSS do Tailwind é compilado dentro do HTML, sem dependência de CDN para o layout.

No deploy Vercel, o arquivo fica disponível em:
https://api-liturgia-diaria.vercel.app/liturgia-cnbb.html

Se alterar o layout, com Node.js 14 ou superior, gere novamente o CSS embutido com `npm --prefix tools/tailwind ci && npm --prefix tools/tailwind run build:html`.

## Fonte
1. CNBB
2. https://sagradaliturgia.com.br/ (alternativa)
3. Canção Nova (alternativa)

A rota `/cnbb` continua disponível para consultar explicitamente os dados da CNBB. A rota `/cn` continua consultando diretamente a Canção Nova.

## Executar localmente
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py
```

O servidor local inicia com depuração desativada. Para usar o visualizador localmente, substitua o endereço da API na página por `http://localhost:5000`.

## Deploy e verificação de produção

O Vercel carrega a aplicação Flask exportada como `app` em `app.py`, publica os arquivos de `public/` como conteúdo estático e aplica as configurações de função e cabeçalhos de `vercel.json`. Depois de publicar o deploy de produção, valide:

- `https://api-liturgia-diaria.vercel.app/healthz` — deve retornar `{"status":"ok"}`.
- `https://api-liturgia-diaria.vercel.app/?date=2026-11-26` — deve retornar HTTP 200 e `source: "CNBB"`.
- `https://api-liturgia-diaria.vercel.app/cnbb?date=2026-11-26` — deve retornar HTTP 200.
- `https://api-liturgia-diaria.vercel.app/liturgia-cnbb.html` — deve abrir o visualizador.

### Plugin Wordpress
https://github.com/JosueSantos/wp-liturgia-diaria-plugin
