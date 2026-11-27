import os
import unicodedata
import unittest

from extractor.ExtractorService import ExtractorService


TEST_DATES = (
    '2026-05-24',
    '2026-06-04',
    '2026-09-15',
    '2026-11-26',
    '2026-11-29',
    '2026-12-24',
    '2026-12-25',
    '2026-12-31',
    '2027-01-01',
    '2027-03-21',
    '2027-03-22',
    '2027-03-23',
    '2027-03-24',
    '2027-03-25',
    '2027-03-26',
    '2027-03-27',
)


@unittest.skipUnless(
    os.environ.get('CNBB_LIVE_TESTS') == '1',
    'Defina CNBB_LIVE_TESTS=1 para consultar a API real da CNBB.',
)
class CnbbLiveTests(unittest.TestCase):
    def test_selected_dates_keep_expected_structure(self):
        readings_by_date = {}
        results_by_date = {}
        celebration_titles_by_date = {}
        psalm_stanza_counts_by_date = {}
        scripture_types = {'first_reading', 'second_reading', 'other_reading', 'gospel'}

        for date in TEST_DATES:
            with self.subTest(date=date):
                result = ExtractorService.getLiturgiaCNBB(date)
                self.assertEqual(result['date'], date)
                self.assertTrue(result['celebrations'])
                results_by_date[date] = result
                psalm_stanza_counts_by_date[date] = []
                celebration_titles_by_date[date] = {
                    celebration['title'] for celebration in result['celebrations']
                }

                readings = [
                    reading
                    for celebration in result['celebrations']
                    for reading in celebration['readings']
                ]
                readings_by_date[date] = readings
                for reading in readings:
                    if reading['type'] == 'psalm':
                        psalm_stanza_counts_by_date[date].append(
                            len(reading.get('content_psalm', []))
                        )
                    if reading['type'] not in scripture_types:
                        continue
                    self.assertTrue(reading.get('start'), reading)
                    self.assertTrue(reading.get('text_array'), reading)
                    for entry in reading['text_array']:
                        if entry['verse']:
                            self.assertEqual(entry.get('type'), 'verse', entry)

        self.assertEqual(
            psalm_stanza_counts_by_date,
            {
                '2026-05-24': [4, 3],
                '2026-06-04': [3],
                '2026-09-15': [5],
                '2026-11-26': [4],
                '2026-11-29': [3],
                '2026-12-24': [3, 3, 4],
                '2026-12-25': [2, 4],
                '2026-12-31': [3],
                '2027-01-01': [3],
                '2027-03-21': [4],
                '2027-03-22': [4],
                '2027-03-23': [4],
                '2027-03-24': [3],
                '2027-03-25': [2, 3],
                '2027-03-26': [4],
                '2027-03-27': [5, 3, 4, 3, 3, 4, 4, 3],
                '2026-05-24': [4, 3],
            },
        )

        self.assertEqual(
            celebration_titles_by_date['2027-03-25'],
            {'Missa do Crisma', 'Missa da Ceia do Senhor'},
        )

        good_friday_gospel = next(
            reading
            for reading in readings_by_date['2027-03-26']
            if reading['type'] == 'gospel'
        )
        passion_types = {entry.get('type') for entry in good_friday_gospel['text_array']}
        self.assertIn('rubric', passion_types)
        self.assertIn('highlight', passion_types)

        easter_vigil_readings = readings_by_date['2027-03-27']
        self.assertEqual(len(easter_vigil_readings), 17)

        pentecost = results_by_date['2026-05-24']
        vigil, mass_of_day = pentecost['celebrations']
        self.assertEqual(
            unicodedata.normalize('NFC', vigil['title']),
            'Missa da Vigília',
        )
        vigil_rubric = unicodedata.normalize('NFC', vigil['rubrics'][0])
        self.assertTrue(vigil_rubric.startswith('Estas leituras serão usadas'))
        self.assertIn('Primeiras Vésperas do domingo de Pentecostes.', vigil_rubric)
        self.assertNotIn('rubrics', pentecost)
        vigil_first_reading = next(
            reading for reading in vigil['readings']
            if reading['type'] == 'first_reading'
        )
        self.assertEqual(
            [option['label'] for option in vigil_first_reading['options']],
            ['a', 'b', 'c', 'd'],
        )
        self.assertEqual(
            [option['ref'] for option in vigil_first_reading['options']],
            ['Gn 11,1-9', 'Ex 19,3-8a.16-20b', 'Ez 37,1-14', 'Jl 3,1-5'],
        )
        self.assertEqual(
            [reading['type'] for reading in mass_of_day['readings']],
            ['first_reading', 'psalm', 'second_reading', 'sequence', 'gospel'],
        )
        self.assertNotIn('rubrics', mass_of_day)
        sequence = mass_of_day['readings'][3]
        self.assertTrue(
            unicodedata.normalize('NFC', sequence['text']).startswith(
                'Espírito de Deus, enviai dos céus'
            )
        )

        corpus_christi = results_by_date['2026-06-04']['celebrations'][0]
        corpus_psalm = next(
            reading for reading in corpus_christi['readings']
            if reading['type'] == 'psalm'
        )
        self.assertEqual(corpus_psalm['title'], 'Salmo responsorial')
        corpus_sequence = next(
            reading for reading in corpus_christi['readings']
            if reading['type'] == 'sequence'
        )
        self.assertIn('Na forma mais longa', corpus_sequence['rubrics'][0])
        self.assertTrue(
            unicodedata.normalize('NFC', corpus_sequence['text']).startswith(
                'Terra, exulta de alegria'
            )
        )
        self.assertNotIn(
            'Terra, exulta de alegria',
            next(
                reading for reading in corpus_christi['readings']
                if reading['type'] == 'second_reading'
            )['text'],
        )

        mary_of_sorrows = results_by_date['2026-09-15']['celebrations'][0]
        gospel = next(
            reading for reading in mary_of_sorrows['readings']
            if reading['type'] == 'gospel'
        )
        self.assertEqual(
            [option['label'] for option in gospel['options']],
            ['a', 'b'],
        )
        self.assertIn('João 19,25-27', gospel['options'][0]['start'])
        self.assertIn('Lucas 2,33-35', gospel['options'][1]['start'])


if __name__ == '__main__':
    unittest.main()
