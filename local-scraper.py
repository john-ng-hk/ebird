from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.options import Options
from webdriver_manager.microsoft import EdgeChromiumDriverManager
import time
from bs4 import BeautifulSoup
from io import StringIO
import csv

def setup_driver():
    edge_options = Options()
    # Comment out headless mode for debugging
    edge_options.add_argument("--headless")
    edge_options.add_argument('--disable-gpu')
    edge_options.add_argument('--window-size=1920,1080')
    edge_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
    try:
        from selenium.webdriver.edge.service import Service as EdgeService
        driver = webdriver.Edge(service=EdgeService(EdgeChromiumDriverManager().install()), options=edge_options)
    except (ImportError, AttributeError):
        driver = webdriver.Edge(executable_path=EdgeChromiumDriverManager().install(), options=edge_options)
    driver.maximize_window()
    return driver

def switch_to_chinese(driver):
    url = "https://ebird.org/region/HK/bird-list?yr=curM"
    driver.get(url)
    
    try:
        print("Waiting for language dropdown...")
        dropdown = driver.find_element(By.CLASS_NAME, "Header-list--dropdown")
        print("Dropdown found, clicking...")
        dropdown.click()
        
        print("Waiting for Chinese (繁體) option...")
        zh_hk_option = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((By.XPATH, "//*[contains(text(), '中文 (繁體)') or @data-lang='zh_HK']"))
        )
        print("Chinese option found, clicking...")
        zh_hk_option.click()
        
        print("Waiting for page to reload in Chinese...")
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "BirdList-list"))
        )
        time.sleep(2)  # Small delay for page stability
        print("Page loaded in Chinese.")
    except Exception as e:
        print(f"Error switching language: {e}")
        driver.quit()
        return False
    return True

def scrape_bird_list(driver, top_n=None):
    bird_data = []
    
    try:
        print("Parsing bird list...")
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        bird_list_div = soup.find('div', class_='BirdList-list')
        
        if not bird_list_div:
            print("Error: Could not find 'BirdList-list' div.")
            return bird_data
        
        # Find all observation rows
        obs_items = bird_list_div.find_all('div', class_='Obs')
        # Filter out header rows (those without a valid species link)
        obs_items = [
            obs for obs in obs_items
            if obs.find('div', class_='Obs-species') and obs.find('div', class_='Obs-species').find('a', class_='Species')
        ]
        max_birds = len(obs_items) if top_n == 0 else min(top_n, len(obs_items))
        print(f"Found {len(obs_items)} birds, scraping {max_birds}.")
        
        for i, obs_item in enumerate(obs_items[:max_birds]):
            species_div = obs_item.find('div', class_='Obs-species')
            species_link = species_div.find('a', class_='Species') if species_div else None
            if not species_link:
                continue
            try:
                chinese_name = species_link.find('span', class_='Species-common').get_text(strip=True)
                # Get English name from the list page
                english_name_element = species_link.find('span', class_='Species-sci Species-sub')
                english_name = english_name_element.get_text(strip=True) if english_name_element else 'N/A'
                bird_url = species_link.get('href')
                if not bird_url.startswith('http'):
                    bird_url = 'https://ebird.org' + bird_url
                
                # Get location from the same Obs div
                location_div = obs_item.find('div', class_='Obs-location')
                location = 'N/A'
                if location_div:
                    location_name = location_div.find('span', class_='Obs-location-name')
                    if location_name:
                        specific = location_name.find('a')
                        parent = location_name.find('span', class_='Obs-location-name-parents')
                        
                        specific_text = specific.get_text(strip=True) if specific else ''
                        parent_text = parent.get_text(strip=True) if parent else ''
                        
                        location = f"{specific_text}, {parent_text}".strip(', ')
                
                # Get date from the Obs-date div
                date_div = obs_item.find('div', class_='Obs-date')
                date = 'N/A'
                if date_div:
                    date_element = date_div.find('time')
                    date = date_element.get_text(strip=True) if date_element else 'N/A'
                
                print(f"Processing bird {i+1}/{max_birds}: {chinese_name}")
                
                # Get description from bird's page
                driver.get(bird_url)
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'Species-identification-text'))
                )
                
                bird_soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                description_div = bird_soup.find('div', class_='Species-identification-text')
                bird_description = description_div.get_text(strip=True) if description_div else '無描述。'
                
                bird_data.append({
                    'chinese_name': chinese_name,
                    'english_name': english_name,
                    'description': bird_description,
                    'location': location,
                    'date': date,
                    'url': bird_url
                })
                
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing bird {i}: {e}")
                bird_data.append({
                    'chinese_name': chinese_name,
                    'english_name': 'N/A',
                    'description': '抓取描述時出錯。',
                    'location': 'N/A',
                    'date': 'N/A',
                    'url': bird_url
                })
                continue
                
    except Exception as e:
        print(f"Error scraping bird list: {e}")
    
    return bird_data

def save_to_csv(data, filename='ibird.cmpapp.top/hk_birds.csv'):
    csv_buffer = StringIO()
    writer = csv.DictWriter(csv_buffer, fieldnames=['Chinese Name', 'English Name', 'Description', 'Location', 'Date', 'URL'])
    writer.writeheader()
    writer.writerow({
        'Chinese Name': '備註: 中文名稱若為 "N/A"，則使用英文名稱作為備用。',
        'English Name': '',
        'Description': '',
        'Location': '',
        'Date': '',
        'URL': ''
    })
    for bird in data:
        writer.writerow({
            'Chinese Name': bird['chinese_name'] if bird['chinese_name'] != 'N/A' else bird['english_name'],
            'English Name': bird['english_name'],
            'Description': bird['description'],
            'Location': bird['location'],
            'Date': bird['date'],
            'URL': bird['url']
        })
    
    with open(filename, 'w', encoding='utf-8-sig') as f:
        f.write(csv_buffer.getvalue())
    print(f"Data saved to {filename}")

def main(top_n=0):  # Default to all birds
    driver = setup_driver()
    
    if not switch_to_chinese(driver):
        return
    
    bird_data = scrape_bird_list(driver, top_n)
    
    if bird_data:
        save_to_csv(bird_data)
    
    driver.quit()

if __name__ == "__main__":
    main()