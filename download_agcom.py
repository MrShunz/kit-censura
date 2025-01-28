#!/usr/bin/env python3

import sys
import requests
import optparse
import ua_generator

from bs4 import BeautifulSoup
from time import sleep
from random import randint
from urllib3.exceptions import InsecureRequestWarning

def attesa_casuale():
   """Tempo di attesa casuale per evitare di essere identificati come bot"""
   sleep(randint(100, 2000)/1000)

def crea_sessione():
   """Crea e configura una sessione requests con user agent casuale"""
   sessione = requests.Session()
   user_agent = ua_generator.generate(
       device='desktop',
       platform=('windows', 'macos', 'linux'),
       browser=('chrome', 'edge', 'firefox', 'safari')
   ).text
   sessione.headers.update({
       'User-Agent': user_agent,
       'Referer': 'https://www.agcom.it'
   })
   return sessione

def trova_url_allegato_b(sessione, url_provvedimento):
   """Estrae l'URL dell'Allegato B dalla pagina del provvedimento"""
   try:
       attesa_casuale()
       risposta = sessione.get(url_provvedimento, verify=False)
       risposta.raise_for_status()
       
       soup = BeautifulSoup(risposta.content, "html.parser")
       sezione_allegati = soup.find('ul', class_='elenco-allegati')
       if not sezione_allegati:
           return None
           
       for allegato in sezione_allegati.find_all('div', class_='allegato-wrapper'):
           link = allegato.find('a')
           if not link:
               continue
               
           if 'Allegato B' in link.text:
               url = link['href']
               return f'https://www.agcom.it{url}' if not url.startswith('http') else url
               
       return None
       
   except Exception:
       return None

def scarica_allegato(sessione, url, file_output):
   """Scarica il file dall'URL e lo salva nel file di output"""
   try:
       attesa_casuale()
       risposta = sessione.get(url, verify=False)
       risposta.raise_for_status()
       
       with open(file_output, 'wb') as f:
           f.write(risposta.content)
       return True
       
   except Exception:
       return False

def main():
   parser = optparse.OptionParser(usage="uso: %prog -o file_output")
   parser.add_option("-o", "--output", dest="file_output", help="Percorso file di output")
   parser.add_option("-v", "--verbose", action="store_true", dest="verbose", 
                     help="Abilita log dettagliati", default=False)

   (opzioni, args) = parser.parse_args()
   
   if opzioni.file_output is None:
       parser.error("Il percorso del file di output (-o) è obbligatorio")

   requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

   url_base = "https://www.agcom.it"
   url_provvedimenti = f"{url_base}/provvedimenti-a-tutela-del-diritto-d-autore"
   sessione = crea_sessione()
   
   pagina_corrente = 1
   max_pagine = 10

   while pagina_corrente < max_pagine:
       try:
           if pagina_corrente > 1:
               attesa_casuale()
           
           url = f"{url_provvedimenti}?page={pagina_corrente-1}"
           risposta = sessione.get(url, verify=False)
           risposta.raise_for_status()
           
           soup = BeautifulSoup(risposta.content, "html.parser")
           schede = soup.find_all('article', class_='card')
           
           for scheda in schede:
               categoria = scheda.find('span', class_='category')
               if not categoria or not any(x in categoria.text.lower() for x in ['determina', 'delibera']):
                   continue

               link = scheda.find('a', class_='read-more')
               if not link:
                   continue
                   
               url_provvedimento = url_base + link['href']
               url_allegato_b = trova_url_allegato_b(sessione, url_provvedimento)
               
               if url_allegato_b and scarica_allegato(sessione, url_allegato_b, opzioni.file_output):
                   return True

       except requests.exceptions.RequestException:
           break
       except Exception:
           break

       pagina_corrente += 1

   return False

if __name__ == '__main__':
   sys.exit(0 if main() else 1)