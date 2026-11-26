# coding: utf-8

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import datetime
import re
import unicodedata

from .Utils import Utils


class ExtractorService():

    @staticmethod
    def getLiturgiaCNBB(date=None):
        if date is None:
            date = datetime.date.today().isoformat()

        try:
            parsed_date = datetime.datetime.strptime(date, '%Y-%m-%d')
        except ValueError as error:
            raise ValueError("A data deve estar no formato YYYY-MM-DD") from error

        if parsed_date.strftime('%Y-%m-%d') != date:
            raise ValueError("A data deve estar no formato YYYY-MM-DD")

        url = f"https://api-liturgia.edicoescnbb.com.br/contents/in/date/{date}"
        response = requests.get(
            url,
            headers={
                'Accept': 'application/json, text/plain, */*',
                'Origin': 'https://liturgiadiaria.edicoescnbb.com.br',
                'Referer': 'https://liturgiadiaria.edicoescnbb.com.br/',
                'User-Agent': 'Mozilla/5.0',
            },
            timeout=(5, 20),
        )
        response.raise_for_status()

        content = response.json().get('content')
        if not isinstance(content, dict):
            raise ValueError("A resposta da API da CNBB não contém o conteúdo esperado")

        return ExtractorService._formatLiturgiaCNBB(content)

    @staticmethod
    def _formatLiturgiaCNBB(content):
        data = dict(content)
        data.pop('filename', None)
        date = datetime.date.fromisoformat(content['date'])
        month_abbreviations = (
            'Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun',
            'Jul', 'Ago', 'Set', 'Out', 'Nov', 'Dez'
        )
        data['date_formatted'] = date.strftime('%d/%m/%Y')
        data['date_string'] = {
            'day': date.strftime('%d'),
            'month': month_abbreviations[date.month - 1],
            'year': date.strftime('%Y'),
        }

        def normalize(value):
            decomposed = unicodedata.normalize('NFKD', value)
            return ''.join(char for char in decomposed if not unicodedata.combining(char)).lower()

        def citation_signature(value):
            return re.sub(r'[^0-9a-z]', '', normalize(value))

        reference_candidates = []
        for field in ('leituras', 'details'):
            reference_soup = BeautifulSoup(content.get(field, ''), 'html.parser')
            for line in reference_soup.get_text('\n', strip=True).splitlines():
                line = ' '.join(line.split())
                line = re.sub(r'^Evangelho:\s*', '', line, flags=re.IGNORECASE)
                if line and not normalize(line).startswith('leituras'):
                    reference_candidates.append(line)

        book_abbreviations = {
            'apocalipse': 'Ap', 'genesis': 'Gn', 'exodo': 'Ex',
            'levitico': 'Lv', 'numeros': 'Nm', 'deuteronomio': 'Dt',
            'josue': 'Js', 'juizes': 'Jz', 'rute': 'Rt', 'samuel': 'Sm',
            'reis': 'Rs', 'cronicas': 'Cr', 'esdras': 'Esd',
            'neemias': 'Ne', 'tobias': 'Tb', 'judite': 'Jt', 'ester': 'Est',
            'macabeus': 'Mc', 'jo': 'Jo', 'salmo': 'Sl', 'salmos': 'Sl',
            'proverbios': 'Pr', 'eclesiastes': 'Ecl', 'sabedoria': 'Sb',
            'siracida': 'Eclo', 'eclesiastico': 'Eclo', 'isaias': 'Is',
            'jeremias': 'Jr', 'lamentacoes': 'Lm', 'baruc': 'Br',
            'ezequiel': 'Ez', 'daniel': 'Dn', 'oseias': 'Os', 'joel': 'Jl',
            'amos': 'Am', 'abdias': 'Ab', 'jonas': 'Jn', 'miqueias': 'Mq',
            'naum': 'Na', 'habacuc': 'Hab', 'sofonias': 'Sf', 'ageu': 'Ag',
            'zacarias': 'Zc', 'malaquias': 'Ml', 'mateus': 'Mt',
            'marcos': 'Mc', 'lucas': 'Lc', 'joao': 'Jo',
            'atos dos apostolos': 'At', 'romanos': 'Rm', 'corintios': 'Cor',
            'galatas': 'Gl', 'efesios': 'Ef', 'filipenses': 'Fl',
            'colossenses': 'Cl', 'tessalonicenses': 'Ts', 'timoteo': 'Tm',
            'tito': 'Tt', 'filemon': 'Fm', 'hebreus': 'Hb', 'tiago': 'Tg',
            'pedro': 'Pd', 'judas': 'Jd',
        }

        def book_abbreviation(start):
            normalized = normalize(start)
            for book_name, abbreviation in book_abbreviations.items():
                match = re.search(r'\b' + re.escape(book_name) + r'\b', normalized)
                if not match:
                    continue
                if abbreviation in ('Sm', 'Rs', 'Cr', 'Mc', 'Cor', 'Ts', 'Tm', 'Pd', 'Jo'):
                    preceding_text = normalized[:match.start()]
                    if re.search(r'\b(segundo|segunda|2[oa]?)\b', preceding_text):
                        return '2' + abbreviation
                    if re.search(r'\b(primeiro|primeira|1[oa]?)\b', preceding_text):
                        return '1' + abbreviation
                return abbreviation
            return None

        def full_reference(citation, start):
            target = citation_signature(citation)
            for reference in reference_candidates:
                match = re.search(r'\b(\d+[,.].*?)(?=\s*\(R\.|$)', reference, re.IGNORECASE)
                if match and citation_signature(match.group(1)) == target:
                    return reference
            abbreviation = book_abbreviation(start)
            return f'{abbreviation} {citation}' if abbreviation else None

        details_text = BeautifulSoup(content.get('details', ''), 'html.parser').get_text(' ', strip=True)
        month_names = (
            'janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
            'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'
        )
        date_label = f"{date.day} de {month_names[date.month - 1]} de {date.year}"
        date_end = re.search(re.escape(date_label), details_text, re.IGNORECASE)
        if date_end:
            title_text = details_text[date_end.end():]
            entry_title = re.split(r'\bLeituras\s*:', title_text, maxsplit=1, flags=re.IGNORECASE)[0]
            data['entry_title'] = re.sub(r'\s+([,.;:])', r'\1', ' '.join(entry_title.split())).strip(' ,')
        else:
            data['entry_title'] = ''

        soup = BeautifulSoup(content.get('body', ''), 'html.parser')
        tokens = []
        has_responsorial_markers = any(
            normalize(' '.join(str(marker).split())) == 'salmo responsorial'
            for marker in soup.find_all(string=True)
        )

        def psalm_parts(markup, title=None):
            fragment = BeautifulSoup(markup, 'html.parser')
            if not title:
                heading = fragment.find('h3', class_='title-leitura')
                if heading:
                    title = ' '.join(heading.get_text(' ', strip=True).split())

            reference = None
            for tag in fragment.find_all('font'):
                tag_text = ' '.join(tag.get_text(' ', strip=True).split())
                color = (tag.get('color') or '').lower()
                if tag_text and color and normalize(tag_text).replace('.', '').strip() != 'r':
                    reference = tag_text
                    break
            if reference:
                reference = re.sub(r'^SI(?=\s*\d)', 'Sl', reference)
                reference = re.sub(r'\s+,', ',', reference)

            if not reference and title:
                title_match = re.match(r'^Salmo\s*-\s*(.+)$', title, re.IGNORECASE)
                if title_match:
                    reference = title_match.group(1).strip()

            response = None
            refrain = fragment.select_one('.refrao_salmo')
            response_marker = None
            if refrain:
                response = re.sub(r'^R\.?\s*', '', refrain.get_text(' ', strip=True)).strip()
            else:
                for marker in fragment.find_all(['font', 'span']):
                    color = (marker.get('color') or marker.get('style') or '').lower()
                    marker_text = normalize(marker.get_text(' ', strip=True)).replace('.', '').strip()
                    if marker_text not in ('r',) or ('red' not in color and '#ff0000' not in color):
                        continue

                    response_marker = marker
                    response_parts = []
                    consecutive_breaks = 0
                    for sibling in marker.next_siblings:
                        if isinstance(sibling, Tag) and sibling.name == 'div' and sibling.find(
                            'div', style=lambda style: style and 'min-width: 30px' in style
                        ):
                            break
                        if isinstance(sibling, Tag) and sibling.name == 'br':
                            consecutive_breaks += 1
                            if consecutive_breaks >= 2:
                                break
                            continue
                        if isinstance(sibling, Tag):
                            sibling_text = sibling.get_text(' ', strip=True)
                        elif str(sibling).strip():
                            sibling_text = str(sibling).strip()
                        else:
                            continue
                        if sibling_text:
                            response_parts.append(sibling_text)
                            consecutive_breaks = 0
                    response = ' '.join(' '.join(response_parts).split()) or None
                    break

            content_psalm = []
            number_blocks = fragment.find_all(
                'div',
                style=lambda style: style and 'min-width: 30px' in style,
            )
            for number_block in number_blocks:
                verse_row = number_block.parent
                text_columns = verse_row.find_all(
                    'div',
                    style=lambda style: style and re.search(r'flex\s*:\s*1', style, re.IGNORECASE),
                )
                if text_columns:
                    verse_text = text_columns[-1].get_text(' ', strip=True)
                    if verse_text:
                        content_psalm.append(verse_text)

            if not content_psalm:
                if refrain:
                    refrain.decompose()
                if response_marker:
                    response_marker.decompose()
                current_parts = []
                consecutive_breaks = 0
                for child in fragment.contents:
                    if isinstance(child, Tag) and child.name == 'br':
                        consecutive_breaks += 1
                        if consecutive_breaks >= 2 and current_parts:
                            content_psalm.append(' '.join(current_parts).strip())
                            current_parts = []
                        continue
                    child_text = child.get_text(' ', strip=True) if isinstance(child, Tag) else str(child).strip()
                    if child_text:
                        current_parts.append(child_text)
                        consecutive_breaks = 0
                if current_parts:
                    content_psalm.append(' '.join(current_parts).strip())

            stanzas = []
            stanza_verses = []
            for verse in content_psalm:
                has_refrain_marker = re.search(r'\sR\s*\.?\s*$', verse, re.IGNORECASE)
                verse = re.sub(r'\s*\bR\s*\.?\s*$', '', verse, flags=re.IGNORECASE).strip()
                if verse:
                    stanza_verses.append(verse)
                if has_refrain_marker and stanza_verses:
                    stanzas.append(' '.join(stanza_verses))
                    stanza_verses = []
            if stanza_verses:
                stanzas.append(' '.join(stanza_verses))
            return reference, response, stanzas

        def verse_row(node):
            number_block = node.find(
                'div',
                style=lambda style: style and re.search(r'min-width\s*:\s*30px', style, re.IGNORECASE),
                recursive=False,
            )
            if not number_block:
                return None

            number = ' '.join(number_block.get_text(' ', strip=True).split())
            if not re.fullmatch(r'\d+(?:,\d+[a-z]?)?[a-z]?(?:-\d+[a-z]?)?', number, re.IGNORECASE):
                return None

            text_columns = node.find_all(
                'div',
                style=lambda style: style and re.search(r'flex\s*:\s*1', style, re.IGNORECASE),
            )
            verse_text = text_columns[-1].get_text(' ', strip=True) if text_columns else ''
            return {
                'number': number,
                'text': ' '.join(verse_text.split()),
            }

        def psalm_siblings_markup(marker):
            markup = []
            has_psalm_content = False
            included_psalm_heading = False
            for sibling in marker.parent.next_siblings:
                if isinstance(sibling, Tag):
                    sibling_text = ' '.join(sibling.get_text(' ', strip=True).split())
                    if sibling.name == 'center' and heading_marker(sibling_text):
                        break
                    if sibling.name == 'b' and normalize(sibling_text).startswith('missa '):
                        break
                    if sibling.name == 'font':
                        normalized = normalize(sibling_text)
                        if normalized in ('salmo responsorial', 'aclamacao ao evangelho'):
                            break
                    if sibling.name == 'div':
                        heading = sibling.find('h3', class_='title-leitura', recursive=False)
                        if heading:
                            if (
                                not normalize(heading.get_text(' ', strip=True)).startswith('salmo -')
                                or has_psalm_content
                                or included_psalm_heading
                            ):
                                break
                            included_psalm_heading = True
                        if sibling.find(
                            'div',
                            style=lambda style: style and re.search(r'min-width\s*:\s*30px', style, re.IGNORECASE),
                        ):
                            has_psalm_content = True
                    if sibling.name == 'font' and (sibling.get('color') or '').lower() == 'tomato':
                        has_psalm_content = True
                markup.append(str(sibling))
            return ''.join(markup)

        def heading_marker(label):
            normalized = normalize(label)
            if normalized.startswith('evangelho'):
                return {'kind': 'gospel', 'title': label}
            if normalized.startswith('salmo'):
                return {'kind': 'psalm', 'title': label}

            ordinals = {
                'primeira': 'first_reading',
                'segunda': 'second_reading',
                'terceira': 'other_reading',
                'quarta': 'other_reading',
                'quinta': 'other_reading',
                'sexta': 'other_reading',
                'setima': 'other_reading',
                'oitava': 'other_reading',
                'nona': 'other_reading',
                'decima': 'other_reading',
            }
            match = re.match(r'^(primeira|segunda|terceira|quarta|quinta|sexta|setima|oitava|nona|decima)\s+leitura\b', normalized)
            if match:
                return {'kind': ordinals[match.group(1)], 'title': label}
            if normalized.startswith('carta'):
                return {'kind': 'other_reading', 'title': label}
            return None

        def add_center_markers(label):
            mass_match = re.match(
                r'^(Missa\b.+?)(?=\s+(?:PRIMEIRA|SEGUNDA|TERCEIRA|QUARTA|QUINTA|SEXTA|S[ÉE]TIMA|OITAVA|NONA|D[ÉE]CIMA|CARTA|EVANGELHO)\b)',
                label,
                re.IGNORECASE,
            )
            if mass_match:
                tokens.append({'kind': 'celebration', 'title': mass_match.group(1).strip()})
                label = label[mass_match.end():].strip()
            marker = heading_marker(label)
            if marker:
                tokens.append(marker)
                return True
            return mass_match is not None

        def walk(node):
            if isinstance(node, NavigableString):
                text = ' '.join(str(node).split())
                normalized = normalize(text)
                if normalized.startswith('missa '):
                    tokens.append({'kind': 'celebration', 'title': text})
                elif normalized == 'salmo responsorial':
                    psalm_markup = psalm_siblings_markup(node)
                    reference, response, content_psalm = psalm_parts(psalm_markup)
                    heading = BeautifulSoup(psalm_markup, 'html.parser').find(
                        'h3',
                        class_='title-leitura',
                    )
                    tokens.append({
                        'kind': 'psalm',
                        'title': (
                            ' '.join(heading.get_text(' ', strip=True).split())
                            if heading
                            else text
                        ),
                        'ref': reference,
                        'response': response,
                        'content_psalm': content_psalm,
                    })
                elif normalized == 'aclamacao ao evangelho':
                    tokens.append({'kind': 'acclamation', 'title': text})
                elif text:
                    tokens.append({'kind': 'text', 'text': text})
                return

            if not isinstance(node, Tag) or node.name in ('meta', 'script', 'style'):
                return

            text = ' '.join(node.get_text(' ', strip=True).split())
            if node.name == 'div':
                verse = verse_row(node)
                if verse:
                    tokens.append({'kind': 'verse', **verse})
            if (
                node.name == 'center'
                and not node.find('center')
                and add_center_markers(text)
            ):
                return
            if node.name == 'div' and node.get('align') == 'center' and normalize(text).startswith('vigilia pascal'):
                tokens.append({'kind': 'celebration', 'title': text})
                return
            if node.name == 'div':
                psalm_heading = node.find('h3', class_='title-leitura', recursive=False)
                if psalm_heading and normalize(psalm_heading.get_text(' ', strip=True)).startswith('salmo -'):
                    if has_responsorial_markers:
                        return
                    markup = ''.join(str(child) for child in node.children if child is not psalm_heading)
                    title = ' '.join(psalm_heading.get_text(' ', strip=True).split())
                    reference, response, content_psalm = psalm_parts(markup, title)
                    tokens.append({
                        'kind': 'psalm',
                        'title': title,
                        'ref': reference,
                        'response': response,
                        'content_psalm': content_psalm,
                    })
                    for child in node.children:
                        if child is not psalm_heading:
                            walk(child)
                    return
            if node.name == 'h3':
                marker = heading_marker(text)
                if marker and marker['kind'] == 'psalm':
                    if not has_responsorial_markers:
                        tokens.append(marker)
                    return
                if 'title-leitura' in node.get('class', []):
                    return
            if node.name == 'b' and normalize(text).startswith('missa '):
                tokens.append({'kind': 'celebration', 'title': text})
                return
            if node.name == 'title' and 'vigilia pascal' in normalize(text):
                tokens.append({'kind': 'celebration', 'title': text})
                return

            for child in node.children:
                walk(child)

        for child in soup.contents:
            walk(child)

        sections = []
        current_section = None
        current_celebration = soup.title.get_text(' ', strip=True) if soup.title else data['entry_title']
        if 'vigilia pascal' not in normalize(current_celebration):
            current_celebration = data['entry_title'] or 'Liturgia do dia'

        def finish_section():
            if current_section is None:
                return
            current_section['text'] = ' '.join(current_section.pop('_text_parts')).strip()
            sections.append(current_section)

        for token in tokens:
            if token['kind'] == 'text':
                if current_section is not None:
                    current_section['_text_parts'].append(token['text'])
                continue
            if token['kind'] == 'verse':
                if current_section is not None:
                    if '_verse_entries' not in current_section:
                        current_section['_before_first_verse'] = ' '.join(current_section['_text_parts']).strip()
                        current_section['_verse_entries'] = []
                    current_section['_verse_entries'].append(token)
                continue
            if token['kind'] == 'celebration':
                finish_section()
                current_section = None
                current_celebration = token['title']
                continue

            finish_section()
            current_section = {
                'type': token['kind'],
                'title': token['title'],
                'celebration': current_celebration,
                '_text_parts': [],
            }
            if token['kind'] == 'psalm':
                current_section['ref'] = token.get('ref')
                current_section['response'] = token.get('response')
                current_section['content_psalm'] = token.get('content_psalm', [])
        finish_section()

        def acclamation_fields(acclamation):
            fields = {'ref': None, 'head': None, 'head_response': None}
            if not acclamation:
                return fields

            text = acclamation['text']
            response_match = re.search(r'\bR\.\s*(.*?)(?=\s+\bV\.\s*)', text)
            verse_match = re.search(r'\bV\.\s*(.*)$', text)
            if response_match:
                fields['ref'] = text[:response_match.start()].strip() or None
                fields['head_response'] = response_match.group(1).strip() or None
            elif verse_match:
                fields['ref'] = text[:verse_match.start()].strip() or None
            if verse_match:
                fields['head'] = verse_match.group(1).strip() or None
            return fields

        gospel_centers = [
            center for center in soup.find_all('center')
            if normalize(center.get_text(' ', strip=True)).startswith('evangelho')
        ]
        acclamations_by_celebration = {}
        for section in sections:
            if section['type'] == 'acclamation':
                acclamations_by_celebration.setdefault(section['celebration'], []).append(section)

        gospel_index = 0
        for section in sections:
            if section['type'] != 'gospel':
                continue

            acclamations = acclamations_by_celebration.get(section['celebration'], [])
            acclamation = acclamations.pop(0) if acclamations else None
            fields = acclamation_fields(acclamation)

            center = gospel_centers[gospel_index] if gospel_index < len(gospel_centers) else None
            gospel_index += 1
            pre_tag = center.find_next('p', align='right') if center else None
            start_tag = center.find_next('b') if center else None
            citation_tag = start_tag.find_next('font') if start_tag else None
            pre = ' '.join(pre_tag.get_text(' ', strip=True).split()) if pre_tag else None
            start_parts = [
                ' '.join(tag.get_text(' ', strip=True).split())
                for tag in (start_tag, citation_tag)
                if tag
            ]
            start = ' '.join(start_parts) or None

            raw_text = section['text']
            text_start = 0
            for prefix in (pre, start):
                if prefix:
                    prefix_index = raw_text.find(prefix, text_start)
                    if prefix_index >= 0:
                        text_start = prefix_index + len(prefix)

            gospel_text = raw_text[text_start:].strip()
            footer_matches = list(re.finditer(r'\bPalavra da Salvação[.!]?', gospel_text, re.IGNORECASE))
            footer = footer_matches[-1].group(0) if footer_matches else None
            if footer_matches:
                gospel_text = gospel_text[:footer_matches[-1].start()].strip()

            section.update(fields)
            section.update({
                'pre': pre,
                'start': start,
                'text': gospel_text,
                'footer': footer,
            })

        reading_centers = {
            'first_reading': [],
            'second_reading': [],
            'other_reading': [],
        }
        for center in soup.find_all('center'):
            if center.find('center'):
                continue
            label = ' '.join(center.get_text(' ', strip=True).split())
            normalized_label = normalize(label)
            mass_match = re.match(
                r'^(missa\b.+?)(?=\s+(?:primeira|segunda|terceira|quarta|quinta|sexta|setima|oitava|nona|decima|carta|evangelho)\b)',
                normalized_label,
            )
            if mass_match:
                label = label[mass_match.end():].strip()
            marker = heading_marker(label)
            if marker and marker['kind'] in reading_centers:
                reading_centers[marker['kind']].append(center)

        reading_center_indexes = {kind: 0 for kind in reading_centers}
        for section in sections:
            section_type = section['type']
            if section_type not in reading_centers:
                continue
            center_index = reading_center_indexes[section_type]
            centers = reading_centers[section_type]
            reading_center_indexes[section_type] += 1
            if center_index >= len(centers):
                continue

            center = centers[center_index]
            first_following = center.find_next(['center', 'p'])
            if not first_following or first_following.name != 'p' or first_following.get('align') != 'right':
                continue
            pre_tag = first_following
            citation_tag = pre_tag.find_next('font')
            if not citation_tag or citation_tag.find_previous('center') is not center:
                continue

            pre = ' '.join(pre_tag.get_text(' ', strip=True).split())
            citation = ' '.join(citation_tag.get_text(' ', strip=True).split())
            raw_text = section['text']
            pre_index = raw_text.find(pre)
            if not pre or pre_index != 0:
                continue
            after_pre = raw_text[pre_index + len(pre):].strip()
            citation_index = after_pre.find(citation)
            if not citation or citation_index < 0:
                continue

            start_prefix = after_pre[:citation_index].strip()
            start = ' '.join(part for part in (start_prefix, citation) if part) or None
            reading_text = after_pre[citation_index + len(citation):].strip()

            footer_response_match = re.search(
                r'(Graças a Deus[.!]?)\s*$',
                reading_text,
                re.IGNORECASE,
            )
            footer_response = footer_response_match.group(1) if footer_response_match else None
            if footer_response_match:
                reading_text = reading_text[:footer_response_match.start()].strip()

            footer_match = re.search(
                r'(Palavra do Senhor[.!]?|Palavra da Salvação[.!]?)\s*$',
                reading_text,
                re.IGNORECASE,
            )
            footer = footer_match.group(1) if footer_match else None
            if footer_match:
                reading_text = reading_text[:footer_match.start()].strip()

            section.update({
                'pre': pre,
                'ref': full_reference(citation, start_prefix),
                'start': start,
                'text': reading_text,
                'footer': footer,
                'footer_response': footer_response,
            })

        def text_array_for(section):
            entries = section.pop('_verse_entries', [])
            before_first_verse = section.pop('_before_first_verse', '')
            text_array = []

            if not entries:
                text = section.get('text', '').strip()
                return [{'verse': '', 'text': text}] if text else text_array

            preamble = before_first_verse
            for prefix in (section.get('pre'), section.get('start')):
                if prefix and preamble.startswith(prefix):
                    preamble = preamble[len(prefix):].strip()
            if preamble:
                text_array.append({'verse': '', 'text': preamble})
            for entry in entries:
                text = entry['text'].strip()
                if entry is entries[-1]:
                    for footer in (section.get('footer_response'), section.get('footer')):
                        if footer:
                            text = re.sub(
                                r'\s*' + re.escape(footer) + r'\s*$',
                                '',
                                text,
                                flags=re.IGNORECASE,
                            ).strip()
                text_array.append({'verse': entry['number'], 'text': text})
            return text_array

        scripture_types = {'first_reading', 'second_reading', 'other_reading', 'gospel'}
        for section in sections:
            if section['type'] in scripture_types:
                section['text_array'] = text_array_for(section)
            else:
                section.pop('_verse_entries', None)
                section.pop('_before_first_verse', None)

        readings = {
            'first_readings': [],
            'psalms': [],
            'second_readings': [],
            'other_readings': [],
            'gospels': [],
            'sections': sections,
        }
        category_by_type = {
            'first_reading': 'first_readings',
            'psalm': 'psalms',
            'second_reading': 'second_readings',
            'other_reading': 'other_readings',
            'gospel': 'gospels',
        }
        celebrations = {}
        for section in sections:
            if section['type'] == 'acclamation':
                continue
            readings[category_by_type[section['type']]].append(section)
            celebration = section['celebration']
            celebrations.setdefault(celebration, []).append(section)

        data['readings'] = readings
        data['celebrations'] = [
            {'title': title, 'sections': celebration_sections}
            for title, celebration_sections in celebrations.items()
        ]
        return data

    @staticmethod
    def getScrapySantoCancaoNova(url="https://santo.cancaonova.com/"):
        page = requests.get(url, timeout=(5, 20))
        if page.status_code != 200:
            return {"error": f"Não foi possível acessar {url}, status {page.status_code}"}

        soup = BeautifulSoup(page.content, 'html.parser')

        data = {}

        # data
        data["day"] = soup.select_one("#date-post .dia").get_text(strip=True) if soup.select_one("#date-post .dia") else None
        data["month"] = soup.select_one("#date-post .mes").get_text(strip=True) if soup.select_one("#date-post .mes") else None
        data["year"] = soup.select_one("#date-post .ano").get_text(strip=True) if soup.select_one("#date-post .ano") else None

        # título
        title_tag = soup.find("h1", class_="entry-title")
        data["title"] = title_tag.get_text(strip=True) if title_tag else None

        # imagem
        first_img = soup.select_one(".entry-content img")
        data["image"] = first_img["src"] if first_img and first_img.has_attr("src") else None

        # texto principal
        entry_content = soup.select_one(".entry-content")
        if entry_content:
            paragraphs = [p.get_text(" ", strip=True) for p in entry_content.find_all("p")]
            data["full_text"] = "\n\n".join(paragraphs)
        else:
            data["full_text"] = None

        # lista de outros santos (se houver)
        outros_santos = []
        ul = entry_content.find("ul") if entry_content else None
        if ul:
            for li in ul.find_all("li"):
                outros_santos.append(li.get_text(" ", strip=True))
        data["outros_santos"] = outros_santos if outros_santos else None

        return data
    
    def getScrapySagradaLiturgia(date):
        if date == None:
            today = datetime.date.today()
            date = today.strftime('%Y-%m-%d')
        
        url = "https://sagradaliturgia.com.br/liturgia_diaria.php?date=" + date

        page = requests.get(url, timeout=(5, 20))
        if page.status_code != 200:
            raise requests.exceptions.HTTPError(
                f"Não foi possível acessar {url}, status {page.status_code}"
            )
        soup = BeautifulSoup(page.content, 'html.parser')

        data = {}
        
        body = soup.find_all(class_ ='ui-body')[1]

        header = body.find('center')

        img_color = header.find('img')
        img_src = img_color['src']
        color = img_src.split('/')[-1].split('.')[0]
        data["color"] = color

        data_texto_c = header.find('b')
        data_texto = data_texto_c.text.lower().split(', ')[1]
        date_match = re.search(r'(\d{1,2}) de ([^ ]+) de (\d{4})', data_texto)
        if not date_match:
            raise ValueError("Não foi possível interpretar a data da liturgia")

        months = {
            'janeiro': 1, 'fevereiro': 2, 'marco': 3, 'março': 3,
            'abril': 4, 'maio': 5, 'junho': 6, 'julho': 7,
            'agosto': 8, 'setembro': 9, 'outubro': 10,
            'novembro': 11, 'dezembro': 12
        }
        day, month_name, year = date_match.groups()
        data_formatada = datetime.datetime(int(year), months[month_name], int(day))

        data["date"] = data_formatada.strftime("%d/%m/%Y")
        data["date_string"] = {
            "day": data_formatada.strftime("%d"),
            "month": data_formatada.strftime("%b"),
            "year": data_formatada.strftime("%Y")
        }

        img_color.decompose()
        data_texto_c.decompose()

        data["entry_title"] = str(header).replace("<br/><br/>", "").replace("<center>", "").replace("</center>", "")

        header.decompose()

        data['readings'] = {}

        all_body = str(body).split("\n")
        
        string_to_remove = "<br/>"
        all_body = [item for item in all_body if item != string_to_remove]
        string_to_remove = ""
        all_body = [item for item in all_body if item != string_to_remove]

        all_body.pop(0)
        all_body.pop(0)
        all_body.pop()

        data['extra'] = all_body
        index = all_body.index("<b>")

        if "Primeira leitura:" in all_body[index + 1]:
            first_reading = {}

            all_body.pop(index)
            first_reading['title'] = all_body.pop(index).replace("<br/>", "")
            all_body.pop(index)
            first_reading['head'] = all_body.pop(index).replace("<br/>", "")
            first_reading['text'] = all_body.pop(index).replace("<br/>", "")
            first_reading['footer'] = all_body.pop(index).replace("<br/>", "")
            first_reading['footer_response'] = all_body.pop(index).replace("<br/>", "")

            data['readings']['first_reading'] = first_reading
        
        
        index = all_body.index("<b>")
        if "Salmo" in all_body[index + 1]:
            psalm = {}

            all_body.pop(index)
            psalm['title'] = all_body.pop(index).replace("<br/>", "")
            all_body.pop(index)

            content_psalm = []
            while (all_body[index] != '<b>'):
                content_psalm.append(all_body.pop(index).replace("<br/>", ""))
                psalm['response'] = all_body.pop(index).replace("<br/>", "")

            psalm['content_psalm'] = content_psalm

            data['readings']['psalm'] = psalm

        index = all_body.index("<b>")
        if "Segunda leitura:" in all_body[index + 1]:
            second_reading = {}

            all_body.pop(index)
            second_reading['title'] = all_body.pop(index).replace("<br/>", "")
            all_body.pop(index)
            second_reading['head'] = all_body.pop(index).replace("<br/>", "")
            second_reading['text'] = all_body.pop(index).replace("<br/>", "")
            second_reading['footer'] = all_body.pop(index).replace("<br/>", "")
            second_reading['footer_response'] = all_body.pop(index).replace("<br/>", "")

            data['readings']['second_reading'] = second_reading

        index = all_body.index("<b>")
        if "Evangelho de" in all_body[index + 1]:
            gospel = {}
            
            all_body.pop(index)
            gospel['head_title'] = all_body.pop(index).replace("<br/>", "")
            all_body.pop(index)
            gospel['head_response'] = all_body.pop(index).replace("<br/>", "")
            gospel['head'] = all_body.pop(index).replace("<br/>", "")
            all_body.pop(index)
            gospel['title'] = all_body.pop(index).replace("<br/>", "")
            all_body.pop(index)
            gospel['text'] = all_body.pop(index).replace("<br/>", "")
            gospel['footer'] = all_body.pop(index).replace("<br/>", "")
            gospel['footer_response'] = all_body.pop(index).replace("<br/>", "")

            data['readings']['gospel'] = gospel

        return data

    
    def getScrapyCancaoNova(url = "https://liturgia.cancaonova.com/pb/"):
        page = requests.get(url, timeout=(5, 20))
        page.raise_for_status()
        soup = BeautifulSoup(page.content, 'html.parser')

        data = {}

        data['date_string'] = {}

        data['date_string']['day'] = soup.find(id='dia-calendar').get_text()
        data['date_string']['month'] = soup.find(id='mes-calendar').get_text()
        data['date_string']['year'] = soup.find(id='ano-calendar').get_text()

        data['date'] = Utils.parseDay(data['date_string']['day']) + '/' + Utils.parseMonth(data['date_string']['month']) + '/' + data['date_string']['year']

        data['color'] = soup.find(class_ ='cor-liturgica').get_text()
        data['color'] = Utils.clean_html(data['color'].split(":")[1] if len(data['color'].split(":")) > 0 else data['color'])

        data['entry_title'] = Utils.clean_html(soup.find(class_='entry-title').get_text())
        
        data['readings'] = {}
        
        find_first_reading = soup.find(id='liturgia-1')
        if (find_first_reading):
            all_first_reading = find_first_reading.find_all('p')
            
            first_reading = {}
            
            first_reading['title'] = all_first_reading[0].get_text()
            first_reading['head'] = all_first_reading[1].get_text()
            first_reading['footer'] = all_first_reading[-2].get_text().replace("- ","")
            first_reading['footer_response'] = all_first_reading[-1].get_text().replace("- ","")
            
            first_reading['all_html'] = ' '.join(p.prettify() for p in all_first_reading)

            text = all_first_reading[2:-2]
            for phrase in text:
                for strong in phrase.find_all('strong'):
                    strong.decompose()

            first_reading['text'] = ' '.join(p.get_text() for p in text)
            first_reading['text'] = first_reading['text'].replace("  "," ")

            data['readings']['first_reading'] = first_reading
        
        fild_psalm = soup.find(id='liturgia-2')
        if (fild_psalm):
            all_psalm = fild_psalm.find_all('p')
            
            psalm = {}

            psalm['title'] = all_psalm[0].get_text()
            psalm['response'] = all_psalm[1].get_text().replace("— ","")

            psalm['all_html'] = ' '.join(p.prettify() for p in all_psalm)
            
            list_content_psalm = []

            content_psalm = all_psalm[2:]
            for phrase in content_psalm:
                for strong in phrase.find_all('strong'):
                    strong.decompose()
                
                text = phrase.get_text().replace("— ","")
                if (text):
                    list_content_psalm.append(text)

            psalm['content_psalm'] = list_content_psalm

            data['readings']['psalm'] = psalm
        
        find_second_reading = soup.find(id='liturgia-3')
        if (find_second_reading):
            all_second_reading = find_second_reading.find_all('p')
            
            second_reading = {}
            
            second_reading['title'] = all_second_reading[0].get_text()
            second_reading['head'] = all_second_reading[1].get_text()
            second_reading['footer'] = all_second_reading[-2].get_text().replace("- ","")
            second_reading['footer_response'] = all_second_reading[-1].get_text().replace("- ","")
            
            second_reading['all_html'] = ' '.join(p.prettify() for p in all_second_reading)

            text = all_second_reading[2:-2]
            for phrase in text:
                for strong in phrase.find_all('strong'):
                    strong.decompose()

            second_reading['text'] = ' '.join(p.get_text() for p in text)
            second_reading['text'] = second_reading['text'].replace("  "," ")

            data['readings']['second_reading'] = second_reading
        
        find_gospel = soup.find(id='liturgia-4')
        if (find_gospel):
            all_gospel = find_gospel.find_all('p')

            gospel = {}
            
            gospel['title'] = all_gospel[0].get_text()
            gospel['head'] = all_gospel[3].get_text().replace("— ","")
            gospel['head_response'] = all_gospel[4].get_text().replace("— ","")
            gospel['footer'] = all_gospel[-2].get_text().replace(" — ","")
            gospel['footer_response'] = all_gospel[-1].get_text().replace(" — ","")
            
            gospel['all_html'] = ' '.join(p.prettify() for p in all_gospel)

            text = all_gospel[5:-2]
            for phrase in text:
                for strong in phrase.find_all('strong'):
                    strong.decompose()

            gospel['text'] = ' '.join(p.get_text() for p in text)
            gospel['text'] = gospel['text'].replace("  "," ")

            data['readings']['gospel'] = gospel

        return data
