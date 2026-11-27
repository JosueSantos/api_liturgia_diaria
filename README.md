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

A resposta da CNBB não usa o wrapper `today`: os campos `date`, `date_formatted`, `date_string`, `title`, `color` e `entry_title` ficam na raiz junto a `objective` e `source`. `celebrations` contém cada celebração e uma lista única `readings`, preservada na ordem da liturgia; rubricas específicas aparecem em `celebration.rubrics`, e rubricas gerais do dia em `rubrics`. Leituras com alternativas incluem `options`, com rótulo (`a`, `b` etc.) e os campos de cada opção. Uma Sequência litúrgica é representada como item `type: "sequence"` em `readings`, preservando sua posição; orientações sobre as formas da Sequência ficam em `sequence.rubrics`. A aclamação ao Evangelho é incorporada aos campos `head` e `head_response` do Evangelho. `details`, `leituras` e `html_full` ficam ao final da resposta, sendo `html_full` o HTML original recebido da CNBB. A rota raiz (`/`) usa o mesmo formato quando a fonte selecionada é a CNBB; os formatos das fontes alternativas permanecem dentro de `today`.

As leituras bíblicas incluem `pre`, `ref`, `start`, `text`, `text_array` e `footer` quando identificados no HTML, além de `footer_response` quando a fonte fornece essa resposta. `text_array` é uma lista ordenada de objetos `{ "verse": "...", "text": "...", "type": "..." }`: trechos numerados recebem `type: "verse"`, rubricas recebem `type: "rubric"` e trechos em itálico recebem `type: "highlight"`. Texto introdutório sem número mantém `verse: ""` e não recebe `type`. Rubricas e destaques também usam `verse: ""`. Repetições e marcadores que indicam a mudança de capítulo (como `19,1` seguido por `2`) permanecem na ordem recebida. Os salmos incluem `ref`, `response` e `content_psalm` sem os marcadores finais `R.`. No Evangelho, `head_response` e `head` precedem `start`, `pre` e `ref`, seguidos pelo texto e pelo rodapé.

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

O servidor local inicia com depuração desativada.

## Testes com a CNBB

A validação ao vivo das datas selecionadas é opcional para não depender da disponibilidade da CNBB na suíte padrão. Ela verifica a estrutura das leituras e as estrofes dos salmos, além dos casos de alternativas, rubricas e Sequência de Pentecostes:

```bash
CNBB_LIVE_TESTS=1 python3 -m pytest -q tests/test_cnbb_live.py
```

O teste consulta 24 de maio, 4 de junho, 15 de setembro, 26 e 29 de novembro de 2026; 24, 25 e 31 de dezembro de 2026; 1º de janeiro de 2027; e os dias 21 a 27 de março de 2027.

## Deploy e verificação de produção

O Vercel detecta a aplicação Flask exportada como `app` em `app.py` e aplica os cabeçalhos de `vercel.json`. A aplicação não depende de Node.js; configure Node.js 26.x nas configurações de build do projeto Vercel para que o deploy seja aceito. Depois de publicar, valide:

- `https://api-liturgia-diaria.vercel.app/healthz` — deve retornar `{"status":"ok"}`.
- `https://api-liturgia-diaria.vercel.app/?date=2026-11-26` — deve retornar HTTP 200 e `source: "CNBB"`.
- `https://api-liturgia-diaria.vercel.app/cnbb?date=2026-11-26` — deve retornar HTTP 200.

### Plugin Wordpress
https://github.com/JosueSantos/wp-liturgia-diaria-plugin
