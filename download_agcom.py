#!/usr/bin/env python3

import requests
import optparse
import sys
import logging
from urllib3.exceptions import InsecureRequestWarning
from bs4 import BeautifulSoup
from random import randint
from time import sleep
import ua_generator
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def waitRand():
    """Random wait time to avoid being identified as a bot"""
    waitms = randint(100, 2000)/1000
    sleep(waitms)

def create_session():
    """Create and configure requests session with random user agent"""
    session = requests.Session()
    user_agent = ua_generator.generate(
        device='desktop',
        platform=('windows', 'macos', 'linux'),
        browser=('chrome', 'edge', 'firefox', 'safari')
    ).text
    session.headers.update({
        'User-Agent': user_agent,
        'Referer': 'https://www.agcom.it'
    })
    return session

def get_allegato_b_url(session, provvedimento_url):
    """Extract Allegato B URL from a provvedimento page"""
    try:
        waitRand()
        response = session.get(provvedimento_url, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Find all allegati in the page
        allegati_section = soup.find('ul', class_='elenco-allegati')
        if not allegati_section:
            logger.debug(f"No allegati section found in {provvedimento_url}")
            return None
            
        for allegato in allegati_section.find_all('div', class_='allegato-wrapper'):
            link = allegato.find('a')
            if not link:
                continue
                
            # Check if this is Allegato B
            if 'Allegato B' in link.text:
                url = link['href']
                if not url.startswith('http'):
                    url = 'https://www.agcom.it' + url
                logger.info(f"Found Allegato B: {url}")
                return url
                
        logger.debug(f"No Allegato B found in {provvedimento_url}")
        return None
        
    except Exception as e:
        logger.error(f"Error processing provvedimento page {provvedimento_url}: {str(e)}")
        return None

def download_allegato(session, url, output_file):
    """Download file from URL and save to output_file"""
    try:
        waitRand()
        response = session.get(url, verify=False)
        response.raise_for_status()
        
        with open(output_file, 'wb') as f:
            f.write(response.content)
        logger.info(f"Successfully downloaded Allegato B to {output_file}")
        return True
        
    except Exception as e:
        logger.error(f"Error downloading file from {url}: {str(e)}")
        return False

def main():
    # Parse command line arguments
    usage = "usage: %prog -o output_file"
    parser = optparse.OptionParser(usage)
    parser.add_option("-o", "--output", dest="out_file", help="Output file path")
    parser.add_option("-v", "--verbose", action="store_true", dest="verbose", 
                      help="Enable verbose logging", default=False)

    (options, args) = parser.parse_args()
    
    if options.out_file is None:
        parser.error("Output file path (-o) is required")
        
    if options.verbose:
        logger.setLevel(logging.DEBUG)

    # Disable SSL verification warnings
    requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

    # Base URLs and configuration
    base_url = "https://www.agcom.it"
    provvedimenti_url = f"{base_url}/provvedimenti-a-tutela-del-diritto-d-autore"
    session = create_session()
    
    current_page = 1
    max_pages = 10
    provvedimento_found = False

    logger.info("Starting AGCOM DDA scraper")
    
    while current_page < max_pages and not provvedimento_found:
        try:
            # Add delay between requests
            if current_page > 1:
                waitRand()

            logger.info(f"Processing page {current_page}")
            
            # Construct pagination URL
            url = f"{provvedimenti_url}?page={current_page-1}"
            response = session.get(url, verify=False)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, "html.parser")

            # Find all provvedimenti cards
            cards = soup.find_all('article', class_='card')
            logger.debug(f"Found {len(cards)} cards on page {current_page}")
            
            for card in cards:
                # Check if it's a Determina/Delibera
                category = card.find('span', class_='category')
                if not category or not any(x in category.text.lower() for x in ['determina', 'delibera']):
                    continue

                # Get the title/number of the provvedimento
                title = card.find('h3', class_='card-title')
                title_text = title.get_text(strip=True) if title else "Unknown Provvedimento"
                
                # Get the provvedimento page URL
                link = card.find('a', class_='read-more')
                if not link:
                    continue
                    
                provvedimento_url = base_url + link['href']
                logger.info(f"Checking {title_text} at {provvedimento_url}")
                
                # Find Allegato B URL
                allegato_b_url = get_allegato_b_url(session, provvedimento_url)
                
                if allegato_b_url:
                    logger.info(f"Found Allegato B for {title_text}")
                    if download_allegato(session, allegato_b_url, options.out_file):
                        provvedimento_found = True
                        break

        except requests.exceptions.RequestException as e:
            logger.error(f"Network error on page {current_page}: {str(e)}")
            break
        except Exception as e:
            logger.error(f"Error processing page {current_page}: {str(e)}")
            break

        current_page += 1

    if provvedimento_found:
        logger.info("Successfully found and downloaded an Allegato B")
        return True
    else:
        logger.warning("No Allegato B found after searching all pages")
        return False

if __name__ == '__main__':
    main()