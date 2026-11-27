import unittest
from unittest.mock import patch

from requests.exceptions import ConnectionError, Timeout

from app import app as flask_app
from extractor.ExtractorService import ExtractorService


def make_content(date, body, details='', leituras='Leituras: teste'):
    return {
        'date': date,
        'filename': 'test.htm',
        'title': 'Tempo Comum',
        'color': 'verde',
        'details': details,
        'leituras': leituras,
        'body': body,
    }


def verse_row(number, text):
    return (
        '<div><div style="display:flex;flex-direction:row;align-items:flex-start">'
        f'<div style="text-align:left;min-width:30px">{number}</div>'
        f'<div><div style="flex:1"><div>{text}</div></div></div>'
        '</div></div>'
    )


def responsorial_psalm(reference):
    return (
        '<font color="red">Salmo responsorial</font>'
        f'<font color="tomato">{reference}</font><br>'
        '<font color="red">R.</font>Refrão do salmo.<br><br>'
        f'{verse_row("1", "Texto do salmo.")}'
    )


def readings_for(result, celebration_index=0):
    return result['celebrations'][celebration_index]['readings']


def readings_of(result, reading_type, celebration_index=0):
    return [
        reading
        for reading in readings_for(result, celebration_index)
        if reading['type'] == reading_type
    ]


class CnbbFormattingTests(unittest.TestCase):
    def test_formats_weekday_and_sunday_readings(self):
        body = (
            '<center>PRIMEIRA LEITURA</center><p>Texto da primeira leitura.</p>'
            '<font color="red">Salmo responsorial</font>'
            '<font color="tomato">Sl 1 (R. 2)</font><br>'
            '<font color="red">R.</font> Refrão do salmo.<br>'
            '<div><div style="display:flex"><div style="min-width: 30px">1</div>'
            '<div><div style="flex: 1"><div>Verso do salmo. R.</div></div></div></div></div>'
            '<center>SEGUNDA LEITURA</center><p>Texto da segunda leitura.</p>'
            '<font color="red">Aclamação ao Evangelho</font>'
            '<font color="tomato">Lc 21,28</font><font color="red">R.</font>'
            ' Aleluia, Aleluia, Aleluia.<font color="red">V.</font>'
            ' Levantai vossa cabeça e olhai, pois a vossa redenção se aproxima!'
            '<center>EVANGELHO</center><p align="right"><i>Preparação da leitura.</i></p>'
            '<b>Proclamação do Evangelho de Jesus Cristo segundo Lucas </b>'
            '<font color="tomato">21,20-28</font><p>Naquele tempo, texto bíblico.</p>'
            '<p>Palavra da Salvação.</p>'
        )
        content = make_content(
            '2026-11-29',
            body,
            'Domingo, 29 de Novembro de 2026 1º Domingo do Advento, Ano B Leituras: Is 63',
        )
        content['source_metadata'] = 'Campo original adicional.'

        result = ExtractorService._formatLiturgiaCNBB(content)

        self.assertEqual(result['date_formatted'], '29/11/2026')
        self.assertEqual(result['entry_title'], '1º Domingo do Advento, Ano B')
        self.assertNotIn('filename', result)
        self.assertEqual(result['title'], 'Tempo Comum')
        self.assertEqual(result['color'], 'verde')
        self.assertEqual(result['details'], content['details'])
        self.assertEqual(result['leituras'], content['leituras'])
        self.assertEqual(result['html_full'], body)
        self.assertEqual(result['source_metadata'], 'Campo original adicional.')
        self.assertEqual(list(result)[-3:], ['details', 'leituras', 'html_full'])
        self.assertNotIn('body', result)
        self.assertEqual(
            [reading['type'] for reading in readings_for(result)],
            ['first_reading', 'psalm', 'second_reading', 'gospel'],
        )
        self.assertEqual(readings_of(result, 'psalm')[0]['response'], 'Refrão do salmo.')
        self.assertEqual(readings_of(result, 'psalm')[0]['content_psalm'], ['Verso do salmo.'])
        gospel = readings_of(result, 'gospel')[0]
        self.assertEqual(
            list(gospel),
            [
                'title', 'type', 'head_response', 'head', 'start', 'pre',
                'ref', 'text_array', 'text', 'footer',
            ],
        )
        self.assertEqual(gospel['ref'], 'Lc 21,28')
        self.assertEqual(gospel['head'], 'Levantai vossa cabeça e olhai, pois a vossa redenção se aproxima!')
        self.assertEqual(gospel['head_response'], 'Aleluia, Aleluia, Aleluia.')
        self.assertEqual(gospel['pre'], 'Preparação da leitura.')
        self.assertEqual(gospel['start'], 'Proclamação do Evangelho de Jesus Cristo segundo Lucas 21,20-28')
        self.assertEqual(gospel['text'], 'Naquele tempo, texto bíblico.')
        self.assertEqual(gospel['footer'], 'Palavra da Salvação.')

    def test_keeps_each_mass_on_special_celebration_day(self):
        body = (
            '<center><b>Missa da manhã</b><br>PRIMEIRA LEITURA</center>'
            '<p>Leitura da manhã.</p><font>Salmo responsorial</font>'
            '<font color="red">R.</font>Resposta da manhã.'
            '<b>Missa da Vigília</b><center>PRIMEIRA LEITURA</center>'
            '<p>Leitura da vigília.</p><font>Salmo responsorial</font>'
            '<font color="red">R.</font>Resposta da vigília.'
            '<center>SEGUNDA LEITURA</center><p>Segunda leitura.</p>'
            '<center>EVANGELHO</center><p>Evangelho da vigília.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2026-12-24', body))

        self.assertEqual(
            [celebration['title'] for celebration in result['celebrations']],
            ['Missa da manhã', 'Missa da Vigília'],
        )
        self.assertEqual(len(readings_of(result, 'first_reading', 0)), 1)
        self.assertEqual(len(readings_of(result, 'first_reading', 1)), 1)
        self.assertEqual(len(readings_of(result, 'psalm', 0)), 1)
        self.assertEqual(len(readings_of(result, 'psalm', 1)), 1)
        self.assertEqual(readings_of(result, 'psalm', 0)[0]['response'], 'Resposta da manhã.')
        self.assertEqual(readings_of(result, 'psalm', 1)[0]['response'], 'Resposta da vigília.')
        self.assertEqual(
            sum(
                len(readings_of(result, 'gospel', index))
                for index in range(len(result['celebrations']))
            ),
            1,
        )

    def test_groups_psalm_verses_until_each_refrain_marker(self):
        def psalm_verse(number, text, has_refrain=False):
            refrain = (
                '<span class="tabulacao"><font color="red">R.</font></span>'
                if has_refrain else ''
            )
            return (
                '<div><div style="display:flex;flex-direction:row;align-items:flex-start">'
                f'<div style="text-align:left;min-width: 30px">{number}</div>'
                f'<div><div style="flex:1"><div>{text}{refrain}</div></div></div>'
                '</div></div>'
            )

        body = (
            '<center>PRIMEIRA LEITURA</center><p>Leitura.</p>'
            '<font color="red">Salmo responsorial</font>'
            '<font color="tomato">SI 96(97),1.6.11-12</font><br>'
            '<font color="red">R.</font>Refrão do salmo.<br><br>'
            + psalm_verse('1', 'Primeiro verso.')
            + psalm_verse('6', 'Segundo verso.', has_refrain=True)
            + psalm_verse('11', 'Terceiro verso.')
            + psalm_verse('12', 'Quarto verso.', has_refrain=True)
            + '<center>EVANGELHO</center><p>Evangelho.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2026-12-25', body))

        self.assertEqual(
            readings_of(result, 'psalm')[0]['content_psalm'],
            [
                'Primeiro verso. Segundo verso.',
                'Terceiro verso. Quarto verso.',
            ],
        )
        self.assertEqual(readings_of(result, 'psalm')[0]['ref'], 'Sl 96(97),1.6.11-12')

    def test_separates_nested_christmas_mass_options(self):
        body = (
            '<center>NATAL DO SENHOR</center>'
            '<center><font><br></font><div><font>Missa da aurora</font>'
            '<center>PRIMEIRA LEITURA</center>'
            '<p align="right"><i>Chegando o Salvador.</i></p>'
            'Leitura do Livro do Profeta Isaías '
            '<font color="#ff6666">62,11-12</font><p>Leitura da aurora.</p>'
            + responsorial_psalm('Sl 96(97),1.6.11-12')
            + '<center>SEGUNDA LEITURA</center><p>Segunda leitura da aurora.</p>'
            '<font color="red">Aclamação ao Evangelho</font>'
            '<font color="tomato">Lc 2,14</font><font color="red">R.</font>'
            'Aleluia.<font color="red">V.</font>Glória a Deus nos céus.'
            + '<center>EVANGELHO</center>'
            '<p align="right"><i>Boa-nova da aurora.</i></p>'
            '<b>Proclamação do Evangelho segundo Lucas </b>'
            '<font color="tomato">2,15-20</font><p>Evangelho da aurora.</p>'
            '</div><font><center><font>Missa do dia</font><br></center></font></center>'
            '<center>PRIMEIRA LEITURA</center>'
            '<p align="right"><i>Salvação do Senhor.</i></p>'
            'Leitura do Livro do Profeta Isaías '
            '<font color="#ff6666">52,7-10</font><p>Leitura do dia.</p>'
            + responsorial_psalm('Sl 97(98),1-2')
            + '<center>SEGUNDA LEITURA</center><p>Segunda leitura do dia.</p>'
            '<font color="red">Aclamação ao Evangelho</font>'
            '<font color="tomato">Lc 2,14</font><font color="red">R.</font>'
            'Aleluia.<font color="red">V.</font>Glória a Deus nos céus.'
            '<center>EVANGELHO</center>'
            '<p align="right"><i>Boa-nova do dia.</i></p>'
            '<b>Proclamação do Evangelho segundo João </b>'
            '<font color="tomato">1,1-18</font><p>Evangelho do dia.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2026-12-25', body))

        self.assertEqual(
            [celebration['title'] for celebration in result['celebrations']],
            ['Missa da aurora', 'Missa do dia'],
        )
        self.assertEqual(
            [
                [reading['type'] for reading in celebration['readings']]
                for celebration in result['celebrations']
            ],
            [
                ['first_reading', 'psalm', 'second_reading', 'gospel'],
                ['first_reading', 'psalm', 'second_reading', 'gospel'],
            ],
        )
        self.assertEqual(result['celebrations'][0]['readings'][0]['ref'], 'Is 62,11-12')
        self.assertEqual(result['celebrations'][1]['readings'][0]['ref'], 'Is 52,7-10')
        self.assertIn('Leitura da aurora.', result['celebrations'][0]['readings'][0]['text'])
        self.assertIn('Leitura do dia.', result['celebrations'][1]['readings'][0]['text'])

    def test_keeps_vigil_readings_and_psalm_citations(self):
        body = (
            '<div align="center"><font>Vigília Pascal na Noite Santa</font></div>'
            '<center>PRIMEIRA LEITURA (mais longa)</center><p>Primeira leitura.</p>'
            '<font>Salmo responsorial</font>'
            '<div id="psalm-1"><h3 class="title-leitura">Salmo - Sl 1</h3>'
            '<span class="refrao_salmo">R. Resposta do salmo.</span>'
            '<div><div style="display:flex"><div style="min-width: 30px">1</div>'
            '<div><div style="flex: 1"><div>Versículo do salmo. R.</div></div></div></div></div></div>'
            '<center>SEGUNDA LEITURA (mais longa)</center><p>Segunda leitura.</p>'
            '<center>TERCEIRA LEITURA</center><p>Terceira leitura.</p>'
            '<center>CARTA</center><p>Epístola.</p>'
            '<center>EVANGELHO</center><p>Evangelho.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2027-03-27', body))

        self.assertEqual(result['celebrations'][0]['title'], 'Vigília Pascal na Noite Santa')
        self.assertEqual(len(readings_of(result, 'psalm')), 1)
        self.assertEqual(readings_of(result, 'psalm')[0]['ref'], 'Sl 1')
        self.assertEqual(readings_of(result, 'psalm')[0]['title'], 'Salmo - Sl 1')
        self.assertEqual(readings_of(result, 'psalm')[0]['response'], 'Resposta do salmo.')
        self.assertEqual(readings_of(result, 'psalm')[0]['content_psalm'], ['Versículo do salmo.'])
        self.assertEqual(len(readings_of(result, 'other_reading')), 2)
        self.assertEqual(readings_for(result)[-1]['type'], 'gospel')

    def test_interleaves_vigil_psalms_after_each_reading(self):
        body = (
            '<div align="center">Vigília Pascal na Noite Santa</div>'
            '<center>PRIMEIRA LEITURA (mais longa)</center><p>Leitura 1.</p>'
            + responsorial_psalm('Sl 103(104),1-2a (R. cf. 30)')
            + ''.join(
                f'<div><h3 class="title-leitura">Salmo - Sl {number}</h3></div>'
                for number in range(32, 40)
            )
            + '<center>SEGUNDA LEITURA (mais longa)</center><p>Leitura 2.</p>'
            + responsorial_psalm('Sl 15(16),5.8.9-10.11 (R. 1a)')
            + '<center>TERCEIRA LEITURA</center><p>Leitura 3.</p>'
            + responsorial_psalm('Ex 15,1-2.3-4 (R. 1a)')
            + '<center>QUARTA LEITURA</center><p>Leitura 4.</p>'
            + responsorial_psalm('Sl 29,2.4.5-6 (R. 2a)')
            + '<center>QUINTA LEITURA</center><p>Leitura 5.</p>'
            + responsorial_psalm('Is 12,2-3.4bcd (R. 3)')
            + '<center>SEXTA LEITURA</center><p>Leitura 6.</p>'
            + responsorial_psalm('Sl 18,8.9.10.11 (R. Jo 6,68c)')
            + '<center>SÉTIMA LEITURA</center><p>Leitura 7.</p>'
            + responsorial_psalm('Sl 41,3.5bcd;42,3.4 (R. 3a)')
            + '<center>CARTA</center><p>Carta.</p>'
            + responsorial_psalm('Sl 117(118) ,1-2.16ab-17.22-23')
            + '<center>EVANGELHO</center><p>Evangelho.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2027-03-27', body))
        expected_types = [
            'first_reading', 'psalm',
            'second_reading', 'psalm',
            'other_reading', 'psalm',
            'other_reading', 'psalm',
            'other_reading', 'psalm',
            'other_reading', 'psalm',
            'other_reading', 'psalm',
            'other_reading', 'psalm',
            'gospel',
        ]
        expected_psalm_refs = [
            'Sl 103(104),1-2a (R. cf. 30)',
            'Sl 15(16),5.8.9-10.11 (R. 1a)',
            'Ex 15,1-2.3-4 (R. 1a)',
            'Sl 29,2.4.5-6 (R. 2a)',
            'Is 12,2-3.4bcd (R. 3)',
            'Sl 18,8.9.10.11 (R. Jo 6,68c)',
            'Sl 41,3.5bcd;42,3.4 (R. 3a)',
            'Sl 117(118),1-2.16ab-17.22-23',
        ]

        self.assertEqual(
            [reading['type'] for reading in readings_for(result)],
            expected_types,
        )
        self.assertEqual(
            [reading['type'] for reading in result['celebrations'][0]['readings']],
            expected_types,
        )
        self.assertEqual(
            [reading['ref'] for reading in readings_of(result, 'psalm')],
            expected_psalm_refs,
        )

    def test_extracts_reference_and_liturgy_fields_from_readings(self):
        body = (
            '<center>PRIMEIRA LEITURA</center>'
            '<p align="right"><i>Caiu Babilônia, a grande!</i></p>'
            'Leitura do Livro do Apocalipse de São João '
            '<font color="#ff6666">18,1-2.21-23; 19,1-3.9a</font>'
            '<p>Texto da primeira leitura.</p><p>Palavra do Senhor.</p>'
            '<font color="red">Salmo responsorial</font>'
            '<font color="tomato">Sl 99(100),2.3.4.5 (R. Ap 19,9a)</font>'
            '<center>SEGUNDA LEITURA</center>'
            '<p align="right"><i>Deus nos reconciliou consigo.</i></p>'
            'Leitura da Carta de São Paulo aos Romanos '
            '<font color="#ff6666">8,1-5</font>'
            '<p>Texto da segunda leitura.</p><p>Palavra do Senhor.</p>'
            '<p>Graças a Deus.</p>'
        )
        leituras = (
            '<div>Ap 18,1-2.21-23.19,1-3.9a</div>'
            '<div>Sl 99(100),2.3.4.5 (R. Ap 19,9a)</div>'
            '<div>Rm 8,1-5</div>'
        )

        result = ExtractorService._formatLiturgiaCNBB(
            make_content('2026-11-26', body, leituras=leituras)
        )

        first = readings_of(result, 'first_reading')[0]
        self.assertEqual(first['pre'], 'Caiu Babilônia, a grande!')
        self.assertEqual(first['ref'], 'Ap 18,1-2.21-23.19,1-3.9a')
        self.assertEqual(
            first['start'],
            'Leitura do Livro do Apocalipse de São João 18,1-2.21-23; 19,1-3.9a',
        )
        self.assertEqual(first['text'], 'Texto da primeira leitura.')
        self.assertEqual(first['footer'], 'Palavra do Senhor.')

        psalm = readings_of(result, 'psalm')[0]
        self.assertEqual(psalm['ref'], 'Sl 99(100),2.3.4.5 (R. Ap 19,9a)')

        second = readings_of(result, 'second_reading')[0]
        self.assertEqual(second['ref'], 'Rm 8,1-5')
        self.assertEqual(second['footer'], 'Palavra do Senhor.')
        self.assertEqual(second['footer_response'], 'Graças a Deus.')

    def test_builds_text_array_for_readings_and_gospel(self):
        body = (
            '<center>PRIMEIRA LEITURA</center>'
            '<p align="right"><i>Caiu Babilônia, a grande!</i></p>'
            'Leitura do Livro do Apocalipse de São João '
            '<font color="#ff6666">18,1-3.21-23; 19,1-2.9a</font>'
            '<p><span class="tab_num"></span>Eu, João,</p>'
            f'{verse_row("1", "vi outro anjo descendo do céu.")}'
            f'{verse_row("2", "Ele gritou com voz poderosa.")}'
            f'{verse_row("3", "Ouvi uma voz poderosa.")}'
            f'{verse_row("21", "Um anjo poderoso levantou uma pedra.")}'
            f'{verse_row("22", "A cidade foi lançada ao mar.")}'
            f'{verse_row("23", "Nunca mais será encontrada.")}'
            f'{verse_row("19,1", "E um anjo me disse:")}'
            f'{verse_row("2", "Felizes são os convidados.")}'
            f'{verse_row("9a", "para o banquete das núpcias do Cordeiro.")}'
            '<p>Palavra do Senhor.</p>'
            '<center>EVANGELHO</center>'
            '<p align="right"><i>Preparação do Evangelho.</i></p>'
            '<b>Proclamação do Evangelho de Jesus Cristo segundo Lucas </b>'
            '<font color="tomato">21,20-21</font>'
            '<p>Naquele tempo,</p>'
            f'{verse_row("20", "Jerusalém será cercada por exércitos.")}'
            f'{verse_row("21", "Então, os que estiverem na Judeia fujam para as montanhas.")}'
            '<p>Palavra da Salvação.</p>'
        )
        leituras = '<div>Ap 18,1-3.21-23.19,1-2.9a</div>'

        result = ExtractorService._formatLiturgiaCNBB(
            make_content('2026-11-26', body, leituras=leituras)
        )

        first = readings_of(result, 'first_reading')[0]
        self.assertEqual(
            first['text_array'],
            [
                {'verse': '', 'text': 'Eu, João,'},
                {'verse': '1', 'text': 'vi outro anjo descendo do céu.'},
                {'verse': '2', 'text': 'Ele gritou com voz poderosa.'},
                {'verse': '3', 'text': 'Ouvi uma voz poderosa.'},
                {'verse': '21', 'text': 'Um anjo poderoso levantou uma pedra.'},
                {'verse': '22', 'text': 'A cidade foi lançada ao mar.'},
                {'verse': '23', 'text': 'Nunca mais será encontrada.'},
                {'verse': '19,1', 'text': 'E um anjo me disse:'},
                {'verse': '2', 'text': 'Felizes são os convidados.'},
                {'verse': '9a', 'text': 'para o banquete das núpcias do Cordeiro.'},
            ],
        )

        gospel = readings_of(result, 'gospel')[0]
        self.assertEqual(
            gospel['text_array'],
            [
                {'verse': '', 'text': 'Naquele tempo,'},
                {'verse': '20', 'text': 'Jerusalém será cercada por exércitos.'},
                {'verse': '21', 'text': 'Então, os que estiverem na Judeia fujam para as montanhas.'},
            ],
        )

    def test_builds_text_array_when_source_has_no_verse_markup(self):
        body = (
            '<center>EVANGELHO</center>'
            '<p align="right"><i>Preparação do Evangelho.</i></p>'
            '<b>Proclamação do Evangelho de Jesus Cristo segundo Marcos </b>'
            '<font color="tomato">16,1-7</font>'
            '<br>Texto sem marcação de versículos.'
            '<p>Palavra da Salvação.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2027-03-27', body))

        self.assertEqual(
            readings_of(result, 'gospel')[0]['text_array'],
            [{'verse': '', 'text': 'Texto sem marcação de versículos.'}],
        )

    def test_removes_reading_footer_from_last_verse_entry(self):
        body = (
            '<center>PRIMEIRA LEITURA</center>'
            '<p align="right"><i>Resumo da leitura.</i></p>'
            'Leitura do Livro do Profeta Isaías '
            '<font color="#ff6666">1,1-2</font>'
            f'{verse_row("1", "Texto da leitura. Palavra do Senhor.")}'
            '<p>Palavra do Senhor.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2026-11-26', body))
        first_reading = readings_of(result, 'first_reading')[0]

        self.assertEqual(first_reading['footer'], 'Palavra do Senhor.')
        self.assertEqual(
            first_reading['text_array'],
            [{'verse': '1', 'text': 'Texto da leitura.'}],
        )

    def test_cnbb_route_uses_short_source_label(self):
        liturgy = {
            'date': '2026-11-26',
            'celebrations': [{
                'title': 'Liturgia',
                'readings': [{
                    'title': 'EVANGELHO',
                    'type': 'gospel',
                    'head_response': 'Aleluia.',
                    'head': 'Levantai vossa cabeça...',
                    'start': 'Proclamação do Evangelho...',
                    'pre': 'Preparação da leitura.',
                    'ref': 'Lc 21,20-28',
                    'text_array': [],
                    'text': 'Naquele tempo.',
                    'footer': 'Palavra da Salvação.',
                }],
            }],
            'details': 'Detalhes',
            'leituras': 'Leituras',
            'html_full': '<p>HTML</p>',
        }
        with patch('app.ExtractorService.getLiturgiaCNBB', return_value=liturgy):
            response = flask_app.test_client().get('/cnbb?date=2026-11-26')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers['Access-Control-Allow-Origin'], '*')
        payload = response.get_json()
        self.assertEqual(payload['source'], 'CNBB')
        self.assertNotIn('today', payload)
        self.assertEqual(
            list(payload),
            ['objective', 'source', 'date', 'celebrations', 'details', 'leituras', 'html_full'],
        )
        self.assertEqual(
            list(payload['celebrations'][0]['readings'][0]),
            [
                'title', 'type', 'head_response', 'head', 'start', 'pre',
                'ref', 'text_array', 'text', 'footer',
            ],
        )

    def test_invalid_date_is_rejected_as_bad_request(self):
        response = flask_app.test_client().get('/cnbb?date=2026-02-30')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'error': 'A data deve estar no formato YYYY-MM-DD.'})

    def test_upstream_request_failure_returns_gateway_error(self):
        with patch(
            'app.ExtractorService.getLiturgiaCNBB',
            side_effect=Timeout('CNBB timed out'),
        ):
            response = flask_app.test_client().get('/cnbb?date=2026-11-26')

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.get_json(),
            {'error': 'Não foi possível consultar a fonte litúrgica no momento.'},
        )

    def test_health_endpoint_does_not_depend_on_upstream_sources(self):
        response = flask_app.test_client().get('/healthz')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {'status': 'ok'})

    def test_homepage_uses_cnbb_as_primary_source(self):
        with (
            patch('app.ExtractorService.getLiturgiaCNBB', return_value={'title': 'CNBB'}) as cnbb,
            patch('app.ExtractorService.getScrapySagradaLiturgia') as sagrada,
            patch('app.ExtractorService.getScrapyCancaoNova') as cancao_nova,
        ):
            response = flask_app.test_client().get('/?date=2026-12-25')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['source'], 'CNBB')
        self.assertEqual(response.get_json()['title'], 'CNBB')
        self.assertNotIn('today', response.get_json())
        cnbb.assert_called_once_with('2026-12-25')
        sagrada.assert_not_called()
        cancao_nova.assert_not_called()

    def test_homepage_falls_back_when_cnbb_is_unavailable(self):
        with (
            patch(
                'app.ExtractorService.getLiturgiaCNBB',
                side_effect=ConnectionError('CNBB unavailable'),
            ),
            patch(
                'app.ExtractorService.getScrapySagradaLiturgia',
                return_value={'title': 'Sagrada Liturgia'},
            ) as sagrada,
        ):
            response = flask_app.test_client().get('/?date=2026-12-25')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['source'], 'https://sagradaliturgia.com.br/')
        self.assertEqual(response.get_json()['today'], {'title': 'Sagrada Liturgia'})
        sagrada.assert_called_once_with('2026-12-25')

    def test_homepage_falls_back_to_cancao_nova_when_other_sources_fail(self):
        with (
            patch(
                'app.ExtractorService.getLiturgiaCNBB',
                side_effect=ConnectionError('CNBB unavailable'),
            ),
            patch(
                'app.ExtractorService.getScrapySagradaLiturgia',
                side_effect=ConnectionError('Sagrada Liturgia unavailable'),
            ),
            patch(
                'app.ExtractorService.getScrapyCancaoNova',
                return_value={'title': 'Canção Nova'},
            ) as cancao_nova,
        ):
            response = flask_app.test_client().get('/?date=2026-12-25')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['source'], 'Canção Nova')
        self.assertEqual(response.get_json()['today'], {'title': 'Canção Nova'})
        cancao_nova.assert_called_once_with()


if __name__ == '__main__':
    unittest.main()
