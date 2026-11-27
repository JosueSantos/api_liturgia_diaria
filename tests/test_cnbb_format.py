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

    def test_psalm_content_stops_at_font_wrapped_reading_heading(self):
        body = (
            '<center>PRIMEIRA LEITURA</center><p>Leitura.</p>'
            + responsorial_psalm('Sl 30(31),2.6.12-13').replace(
                'min-width:30px',
                'min-width: 30px',
            )
            + '<font color="red"><center>SEGUNDA LEITURA</center></font>'
            + verse_row('14', 'Irmãos: temos um sumo sacerdote eminente.')
            + verse_row('15', 'Ele se compadece de nossas fraquezas.')
            + '<center>EVANGELHO</center><p>Evangelho.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2027-03-26', body))

        self.assertEqual(
            readings_of(result, 'psalm')[0]['content_psalm'],
            ['Texto do salmo.'],
        )
        self.assertEqual(
            [entry['text'] for entry in readings_of(result, 'second_reading')[0]['text_array']],
            [
                'Irmãos: temos um sumo sacerdote eminente.',
                'Ele se compadece de nossas fraquezas.',
            ],
        )

    def test_psalm_stops_before_numbered_hidden_reading_heading(self):
        body = (
            '<center>PRIMEIRA LEITURA</center><p>Leitura.</p>'
            '<font color="red">Salmo responsorial</font>'
            '<font color="tomato">Sl 147,12-13.14-15.19-20</font><br>'
            '<font color="red">R.</font>Glorifica o Senhor.<br><br>'
            + verse_row('12', 'Glorifica o Senhor, Jerusalém.')
            + verse_row('13', 'Seus filhos em teu seio abençoou.')
            + '<div><h3 class="title-leitura">2ª Leitura - 1Cor 10,16-17</h3></div>'
            + '<center>SEGUNDA LEITURA</center><p>Leitura seguinte.</p>'
            + '<center>EVANGELHO</center><p>Evangelho.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2026-06-04', body))
        psalm = readings_of(result, 'psalm')[0]

        self.assertEqual(psalm['title'], 'Salmo responsorial')
        self.assertEqual(psalm['ref'], 'Sl 147,12-13.14-15.19-20')
        self.assertEqual(
            psalm['content_psalm'],
            ['Glorifica o Senhor, Jerusalém. Seus filhos em teu seio abençoou.'],
        )

    def test_psalm_with_35px_verse_columns_keeps_stanzas_and_response(self):
        def psalm_row(number, text, has_refrain=False):
            refrain = (
                '<span class="refrao_salmo"><font color="#ff0000">R.</font></span>'
                if has_refrain else ''
            )
            return (
                '<div><div style="display:flex;flex-direction:row;align-items:flex-start">'
                f'<div style="text-align:left;min-width:35px">{number}</div>'
                f'<div><div style="flex:1"><div>{text}{refrain}</div></div></div>'
                '</div></div>'
            )

        body = (
            '<center>PRIMEIRA LEITURA</center><p>Leitura.</p>'
            '<font color="red">Salmo responsorial</font>'
            '<font color="tomato">Sl 115(116B),12-13.15-16bc.17-18</font><br>'
            '<br><span class="refrao_salmo"><font color="#ff0000">R.</font>'
            'Refrão do salmo.<br><br>'
            + psalm_row('12', 'Primeiro verso.')
            + '</span>'
            + psalm_row('13', 'Segundo verso.', has_refrain=True)
            + psalm_row('15', 'Terceiro verso.')
            + psalm_row('16bc', 'Quarto verso.', has_refrain=True)
            + '<font color="red"><center>SEGUNDA LEITURA</center></font>'
            '<p>Texto da segunda leitura.</p>'
            '<center>EVANGELHO</center><p>Evangelho.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2027-03-25', body))
        psalm = readings_of(result, 'psalm')[0]

        self.assertEqual(psalm['response'], 'Refrão do salmo.')
        self.assertEqual(
            psalm['content_psalm'],
            [
                'Primeiro verso. Segundo verso.',
                'Terceiro verso. Quarto verso.',
            ],
        )

    def test_psalm_without_verse_markup_does_not_count_reference_or_refrain(self):
        body = (
            '<center>PRIMEIRA LEITURA</center><p>Leitura.</p>'
            '<font color="red">Salmo responsorial</font>'
            '<font color="tomato">Sl 18B(19),8.9.10.11</font><br>'
            '<font color="#ff0000">R.</font>Senhor, tens palavras de vida eterna.<br><br>'
            '<center>SEGUNDA LEITURA</center><p>Leitura.</p>'
            '<center>EVANGELHO</center><p>Evangelho.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2027-03-27', body))
        psalm = readings_of(result, 'psalm')[0]

        self.assertEqual(psalm['ref'], 'Sl 18B(19),8.9.10.11')
        self.assertEqual(psalm['response'], 'Senhor, tens palavras de vida eterna.')
        self.assertEqual(psalm['content_psalm'], [])

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

    def test_scopes_rubrics_and_groups_optional_readings_and_sequence(self):
        body = (
            '<p class="MsoNormal"><span style="color:red">Rubrica do dia.</span></p>'
            '<b>Missa da Vigília</b>'
            '<p class="MsoNormal"><span style="color:red">'
            'Rubrica da celebração.</span></p>'
            '<center>PRIMEIRA LEITURA</center>'
            '<p align="right"><i>Criação.</i></p>'
            'Leitura do Livro do Gênesis '
            '<font color="#ff6666">1,1-2</font>'
            f'{verse_row("1", "Texto da primeira opção.")}'
            '<div><i><font color="#ff0000">Todos se ajoelham.</font></i></div>'
            '<font color="#ff0000">Ou, b:</font>'
            '<p align="right"><i>Libertação.</i></p>'
            'Leitura do Livro do Êxodo '
            '<font color="#ff6666">3,1-2</font>'
            f'{verse_row("1", "Texto da segunda opção.")}'
            '<center>SEGUNDA LEITURA</center><p>Texto da segunda leitura.</p>'
            '<font color="#ff0000">Sequência</font>'
            'Espírito de Deus, enviai dos céus um raio de luz!'
            '<center>EVANGELHO</center><p>Texto do Evangelho.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2026-05-24', body))
        vigil = result['celebrations'][0]
        first_reading = readings_of(result, 'first_reading')[0]
        sequence = next(reading for reading in vigil['readings'] if reading['type'] == 'sequence')

        self.assertEqual(result['rubrics'], ['Rubrica do dia.'])
        self.assertEqual(vigil['rubrics'], ['Rubrica da celebração.'])
        self.assertEqual(
            [option['label'] for option in first_reading['options']],
            ['a', 'b'],
        )
        self.assertEqual(
            [option['ref'] for option in first_reading['options']],
            ['Gn 1,1-2', 'Ex 3,1-2'],
        )
        self.assertEqual(
            [option['text'] for option in first_reading['options']],
            [
                'Texto da primeira opção. Todos se ajoelham.',
                'Texto da segunda opção.',
            ],
        )
        self.assertIn(
            {'verse': '', 'text': 'Todos se ajoelham.', 'type': 'rubric'},
            first_reading['options'][0]['text_array'],
        )
        self.assertEqual(
            [reading['type'] for reading in vigil['readings']],
            ['first_reading', 'second_reading', 'sequence', 'gospel'],
        )
        self.assertEqual(sequence['text'], 'Espírito de Deus, enviai dos céus um raio de luz!')
        self.assertEqual(
            sequence['text_array'],
            [{'verse': '', 'text': sequence['text']}],
        )
        self.assertNotIn(
            'Espírito de Deus',
            readings_of(result, 'second_reading')[0]['text'],
        )

    def test_extracts_sequence_with_its_form_rubric(self):
        body = (
            '<center>SEGUNDA LEITURA</center><p>Texto da leitura.</p>'
            '<b>Sequência</b><br><br>'
            '<sup><font color="#ff0000">(Na forma mais longa; ou na forma abreviada, '
            'a partir de: **</font></sup><sup> Eis o pão</sup>'
            '<sup><font color="#ff0000">...)</font></sup><br><br>'
            'Terra, exulta de alegria,<br>louva teu pastor e guia com teus hinos!'
            '<center>EVANGELHO</center><p>Texto do Evangelho.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2026-06-04', body))
        sequence = next(
            reading for reading in readings_for(result)
            if reading['type'] == 'sequence'
        )

        self.assertIn('Na forma mais longa', sequence['rubrics'][0])
        self.assertIn('Eis o pão', sequence['rubrics'][0])
        self.assertTrue(sequence['text'].startswith('Terra, exulta de alegria'))
        self.assertNotIn('Eis o pão', sequence['text'])
        self.assertEqual(
            [reading['type'] for reading in readings_for(result)],
            ['second_reading', 'sequence', 'gospel'],
        )

    def test_groups_optional_gospels_into_options(self):
        body = (
            '<center>EVANGELHO</center>'
            '<p align="right"><i>Maria junto à cruz.</i></p>'
            '<b>Proclamação do Evangelho segundo João</b>'
            '<font color="tomato">19,25-27</font>'
            f'{verse_row("25", "Perto da cruz estava sua mãe.")}'
            '<p>Palavra da Salvação.</p>'
            '<font color="#ff6666"><i>Ou</i></font>'
            '<font color="#ff6666">:</font>'
            '<p align="right"><i>Uma espada te traspassará a alma.</i></p>'
            '<b>Proclamação do Evangelho segundo Lucas</b>'
            '<font color="tomato">2,33-35</font>'
            f'{verse_row("33", "O pai e a mãe estavam admirados.")}'
            '<p>Palavra da Salvação.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2026-09-15', body))
        gospel = readings_of(result, 'gospel')[0]

        self.assertEqual(
            [option['label'] for option in gospel['options']],
            ['a', 'b'],
        )
        self.assertIn('João 19,25-27', gospel['options'][0]['start'])
        self.assertIn('Lucas 2,33-35', gospel['options'][1]['start'])
        self.assertEqual(
            gospel['options'][0]['text'],
            'Perto da cruz estava sua mãe.',
        )
        self.assertEqual(
            gospel['options'][1]['text'],
            'O pai e a mãe estavam admirados.',
        )

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

    def test_splits_unnumbered_vigil_psalm_at_red_refrain_markers(self):
        body = (
            '<div align="center">Vigília Pascal na Noite Santa</div>'
            '<center>CARTA</center><p>Carta.</p>'
            '<font color="red">Salmo responsorial</font>'
            '<font color="tomato">Sl 117(118),1-2.16ab-17.22-23</font><br>'
            '<font color="red">R.</font> Aleluia.<br><br>'
            'Primeira estrofe.'
            '<span><font color="#ff0000">R.</font> Segunda estrofe.</span>'
            '<span><font color="#ff0000">R.</font> Terceira estrofe.</span>'
            '<center>EVANGELHO</center><p>Evangelho.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2027-03-27', body))

        self.assertEqual(
            readings_of(result, 'psalm')[0]['content_psalm'],
            ['Primeira estrofe.', 'Segunda estrofe.', 'Terceira estrofe.'],
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

    def test_skips_note_font_before_first_reading_citation(self):
        body = (
            '<font color="red"><center>PRIMEIRA LEITURA</center></font>'
            '<p align="right"><i>Eu te farei luz das nações, para que minha salvação '
            'chegue até aos confins da terra.<br> </i>'
            '<font size="-1">(Segundo canto do Servo do Senhor).</font></p>'
            'Leitura do Livro do Profeta Isaías '
            '<font color="#ff6666">49,1-6</font>'
            f'{verse_row("1", "Nações marinhas, ouvi-me.")}'
            '<p>Palavra do Senhor.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2027-03-23', body))
        first_reading = readings_of(result, 'first_reading')[0]

        self.assertEqual(
            first_reading['pre'],
            'Eu te farei luz das nações, para que minha salvação chegue até aos confins da terra. '
            '(Segundo canto do Servo do Senhor).',
        )
        self.assertEqual(first_reading['ref'], 'Is 49,1-6')
        self.assertEqual(
            first_reading['start'],
            'Leitura do Livro do Profeta Isaías 49,1-6',
        )
        self.assertEqual(first_reading['text'], 'Nações marinhas, ouvi-me.')
        self.assertEqual(
            first_reading['text_array'],
            [{'verse': '1', 'text': 'Nações marinhas, ouvi-me.', 'type': 'verse'}],
        )

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
                {'verse': '1', 'text': 'vi outro anjo descendo do céu.', 'type': 'verse'},
                {'verse': '2', 'text': 'Ele gritou com voz poderosa.', 'type': 'verse'},
                {'verse': '3', 'text': 'Ouvi uma voz poderosa.', 'type': 'verse'},
                {'verse': '21', 'text': 'Um anjo poderoso levantou uma pedra.', 'type': 'verse'},
                {'verse': '22', 'text': 'A cidade foi lançada ao mar.', 'type': 'verse'},
                {'verse': '23', 'text': 'Nunca mais será encontrada.', 'type': 'verse'},
                {'verse': '19,1', 'text': 'E um anjo me disse:', 'type': 'verse'},
                {'verse': '2', 'text': 'Felizes são os convidados.', 'type': 'verse'},
                {'verse': '9a', 'text': 'para o banquete das núpcias do Cordeiro.', 'type': 'verse'},
            ],
        )

        gospel = readings_of(result, 'gospel')[0]
        self.assertEqual(
            gospel['text_array'],
            [
                {'verse': '', 'text': 'Naquele tempo,'},
                {'verse': '20', 'text': 'Jerusalém será cercada por exércitos.', 'type': 'verse'},
                {'verse': '21', 'text': 'Então, os que estiverem na Judeia fujam para as montanhas.', 'type': 'verse'},
            ],
        )

    def test_marks_passion_verses_rubrics_and_highlights(self):
        body = (
            '<center>EVANGELHO</center>'
            '<p align="right"><i>Preparação do Evangelho.</i></p>'
            '<b>Paixão de Nosso Senhor Jesus Cristo segundo João </b>'
            '<font color="tomato">19,30-31</font>'
            '<p>Eu, João,</p>'
            '<p><i>A prisão de Jesus.</i></p>'
            f'{verse_row("30", "Ele tomou o vinagre e disse: Tudo está consumado.")}'
            '<div><span class="tabulacao"><i><font color="#ff0000">'
            'Todos se ajoelham e faz-se uma pausa.'
            '</font></i></span></div>'
            '<div><span class="tabulacao"><i>E logo saiu sangue e água.</i></span></div>'
            f'{verse_row("31", "Era o dia da preparação para a Páscoa.")}'
            '<p>Palavra da Salvação.</p>'
        )

        result = ExtractorService._formatLiturgiaCNBB(make_content('2027-03-26', body))
        gospel = readings_of(result, 'gospel')[0]

        self.assertEqual(
            gospel['text_array'],
            [
                {'verse': '', 'text': 'Eu, João,'},
                {
                    'verse': '',
                    'text': 'A prisão de Jesus.',
                    'type': 'highlight',
                },
                {
                    'verse': '30',
                    'text': 'Ele tomou o vinagre e disse: Tudo está consumado.',
                    'type': 'verse',
                },
                {
                    'verse': '',
                    'text': 'Todos se ajoelham e faz-se uma pausa.',
                    'type': 'rubric',
                },
                {
                    'verse': '',
                    'text': 'E logo saiu sangue e água.',
                    'type': 'highlight',
                },
                {
                    'verse': '31',
                    'text': 'Era o dia da preparação para a Páscoa.',
                    'type': 'verse',
                },
            ],
        )
        self.assertEqual(gospel['footer'], 'Palavra da Salvação.')

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
            [{'verse': '1', 'text': 'Texto da leitura.', 'type': 'verse'}],
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
