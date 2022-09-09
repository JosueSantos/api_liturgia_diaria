# coding: utf-8
 
import re
import datetime


class Utils():
    def parseMonth(month):
        month_list = {
            'Jan': '01', 'Fev': '02', 'Mar': '03', 'Abr': '04', 'Mai': '05', 'Jun': '06',
            'Jul': '07', 'Ago': '08', 'Set': '09', 'Out': '10', 'Nov': '11', 'Dez': '12'
        }
        
        return month_list[month]
    
    def parseDay(day):
        if (len(day) == 1):
            day = '0' + day
        
        return day

    def clearText(text):
        if(text != None):
            return text.strip()
        else:
            return ''
    
    
    def clearDate(date_text):
        if(date_text != None):
            date = datetime.datetime.fromisoformat(date_text)
            return date.strftime('%d/%m/%Y')
        else:
            return ''
    
    def clean_html(html):
        if (html):
            cleaned = re.sub(r"(?is)<(script|style).*?>.*?(</\1>)", "", html.strip())
            cleaned = re.sub(r"(?s)<!--(.*?)-->[\n]?", "", cleaned)
            cleaned = re.sub(r"(?s)<.*?>", " ", cleaned)
            cleaned = re.sub(r"&nbsp;", " ", cleaned)
            
            cleaned = cleaned.replace(";",":")
            cleaned = cleaned.replace("\n"," ")
            cleaned = cleaned.replace("\r"," ")
            cleaned = cleaned.replace("\t"," ")

            for i in range(10):
                cleaned = cleaned.replace("  "," ")
            
            cleaned = cleaned.strip()
        return cleaned
