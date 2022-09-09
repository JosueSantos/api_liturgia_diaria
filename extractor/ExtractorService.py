# coding: utf-8

import requests
from bs4 import BeautifulSoup

from .Utils import Utils


class ExtractorService():
    
    def getScrapy(url = "https://liturgia.cancaonova.com/pb/"):
        page = requests.get(url)
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
