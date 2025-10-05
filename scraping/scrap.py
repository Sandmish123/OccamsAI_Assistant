######################################################################################################################
######################################################################################################################

import undetected_chromedriver as uc
from bs4 import BeautifulSoup
import time
import json
import re
import logging
from contextlib import suppress
import os
from config.config_file import DATA_DIR,LOGS_DIR ,OCCAMS_URLS

######################################################################################################################
######################################################################################################################

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOGS_DIR, "master.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)



######################################################################################################################
######################################################################################################################

def scrape_page(url, wait=3):
    """Scrapes a URL and returns structured data with cleaned paragraphs."""
    try:
        options = uc.ChromeOptions()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")

        with uc.Chrome(options=options) as driver:
            driver.get(url)
            time.sleep(wait)  # wait for JavaScript to load
            soup = BeautifulSoup(driver.page_source, 'html.parser')

            # Remove unwanted elements
            for element in soup(['nav', 'footer', 'script', 'style', 'header']):
                element.decompose()

            # Extract paragraphs
            paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if p.get_text(strip=True)]

            structured_data = {
                "url": url,
                "paragraphs": paragraphs
            }

            return structured_data

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return {"url": url, "paragraphs": []}  # Return empty paragraphs on error


######################################################################################################################
######################################################################################################################

def extract_clean_paragraphs_markdown(data):
    """
    Converts structured data into clean Markdown format.
    """
    output = []

    for item in data:
        url = item.get("url")
        paragraphs = item.get("paragraphs", [])

        output.append(f"### Source: {url}\n")

        for para in paragraphs:
            clean_para = re.sub(r'\s+', ' ', para).strip()
            if clean_para:
                output.append(clean_para + "\n")

        output.append("\n")  # spacing between sources

    return "\n".join(output).strip()


######################################################################################################################
######################################################################################################################

def merge_files_to_md(md_file_path, txt_file_path, output_md_path):

    try:
        logger.info(f"Merging files:\nMarkdown: {md_file_path}\nText: {txt_file_path}")
        
        # Read Markdown file
        with open(md_file_path, 'r', encoding='utf-8') as md_file:
            md_content = md_file.read()
        
        # Read Text file
        with open(txt_file_path, 'r', encoding='utf-8') as txt_file:
            txt_content = txt_file.read()
        
        # Merge content with a Markdown-friendly separator
        merged_content = md_content.strip() + "\n\n" + txt_content.strip()
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_md_path), exist_ok=True)
        
        # Save merged content to Markdown file
        with open(output_md_path, 'w', encoding='utf-8') as out_file:
            out_file.write(merged_content)
        
        logger.info(f"Merged content saved as Markdown at {output_md_path}")
    
    except Exception as e:
        logger.error(f"Error merging files to Markdown: {e}")
        raise


######################################################################################################################
######################################################################################################################

# if __name__ == "__main__":
def start_scrap():
    try:
        structured_results = []

        for url in OCCAMS_URLS:
            logger.info(f"Scraping: {url}")
            data = scrape_page(url)
            logger.info(f"Structured data for {url}: {len(data['paragraphs'])} paragraphs")
            structured_results.append(data)
            time.sleep(1)

        # Convert to Markdown
        markdown_text = extract_clean_paragraphs_markdown(structured_results)

        # Save Markdown to file
        with open(os.path.join(DATA_DIR,"scraped.md"), "w", encoding="utf-8") as md_file:
            md_file.write(markdown_text)

        merge_files_to_md(
        md_file_path=os.path.join(DATA_DIR,"scraped.md"),
        txt_file_path=os.path.join(DATA_DIR,"predefined_content.txt"),
        output_md_path= os.path.join(DATA_DIR,"merged_file.md")
        )
    

        logger.info("Scraping complete. Data saved to 'scraped.md' and generated merged file'.")
        return True
    except Exception as e:
        logger.error(f"Error during scraping: {e}", exc_info=True)
        return False

######################################################################################################################
######################################################################################################################