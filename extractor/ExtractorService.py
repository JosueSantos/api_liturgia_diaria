# coding: utf-8

import locale
import requests
from bs4 import BeautifulSoup
import datetime

from .Utils import Utils


class ExtractorService():
    
    def getScrapySagradaLiturgia(date):
        if date == None:
            today = datetime.date.today()
            date = today.strftime('%Y-%m-%d')
        
        url = "https://sagradaliturgia.com.br/liturgia_diaria.php?date=" + date

        page = requests.get(url)
        soup = BeautifulSoup(page.content, 'html.parser')

        locale.setlocale(locale.LC_TIME, 'pt_BR.utf8')
        
        data = {}
        
        body = soup.find_all(class_ ='ui-body')[1]

        header = body.find('center')

        img_color = header.find('img')
        img_src = img_color['src']
        color = img_src.split('/')[-1].split('.')[0]
        data["color"] = color

        data_texto_c = header.find('b')
        data_texto = data_texto_c.text.lower().split(', ')[1]
        data_formatada = datetime.datetime.strptime(data_texto, '%d de %B de %Y')

        data["date"] = data_formatada.strftime("%d/%m/%Y")
        data["date_string"] = {
            "day": data_formatada.strftime("%d"),
            "month": data_formatada.strftime("%b"),
            "year": data_formatada.strftime("%Y")
        }

        img_color.decompose()
        data_texto_c.decompose()

        data["entry_title"] = header.get_text(strip=True)

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
