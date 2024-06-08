import itertools
import pandas as pd
from tqdm import tqdm
import re, random, time
from datetime import datetime
from selenium import webdriver
from nltk.tokenize import word_tokenize
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support import expected_conditions as EC

#IEEE Xplore

def search_word_tokenizer(antibiotics_keywords: list, ai_keywords: list):
    antibiotics_tokens = set(word_tokenize(" ".join(antibiotics_keywords)))
    ai_tokens = set(word_tokenize(" ".join(ai_keywords)))
    return [f"{antibiotic} {ai}" for antibiotic in antibiotics_tokens for ai in ai_tokens]

def generate_ieee_urls(keyword_pair, num_pages=5):
    urls = []
    for page in range(num_pages):
        query = "%20".join(keyword_pair).replace(' ', '%20')  # Join the keywords with %20 to form the query
        url = f"https://ieeexplore.ieee.org/search/searchresult.jsp?queryText={query}&highlight=true&returnType=SEARCH&matchPubs=true&ranges=2010_2024_Year&returnFacets=ALL&refinements=ContentType:Journals&pageNumber={page+1}"
        urls.append(url)
    return urls

################

def parse_links_selenium(url):
    # Setup the webdriver
    webdriver_service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-popups")
    options.add_argument("--headless")  # Run in headless mode
    
    # List of user-agent strings
    user_agents = [
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.48',
    ]

    # Use the current time as the seed
    random.seed(time.time())

    # Randomly select a user-agent string
    user_agent = random.choice(user_agents)

    # Add the user-agent string to the options
    options.add_argument(user_agent)


    driver = webdriver.Chrome(service=webdriver_service, options=options)

    # Get the page
    driver.get(url)

    # Find all the <a> tags
    a_tags = driver.find_elements(By.TAG_NAME, 'a')

    # Extract the href attribute from each <a> tag
    links = [a.get_attribute('href') for a in a_tags if a.get_attribute('href') is not None]

    # Filter the links
    links = [re.match(r'(https://ieeexplore.ieee.org/document/\d+)/.*', link).group(1) 
             for link in links 
             if re.match(r'https://ieeexplore.ieee.org/document/\d+', link)]

    # Close the driver
    driver.quit()
    return links



#################

def parse_info_selenium(url):
    # Check that the URL is valid
    if url is None or not isinstance(url, str) or not url.startswith('http'):
        return pd.Series([None]*6)

    # Setup the webdriver
    webdriver_service = Service(ChromeDriverManager().install())
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-popups")
    options.add_argument("--headless")  # Run in headless mode

    # List of user-agent strings
    user_agents = [
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
        'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.48',
        'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
        'user-agent=Mozilla/5.0 (Linux; Android 10; SM-A205U) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36',
        'user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Mobile/15E148 Safari/604.1'
    ]

    # Use the current time as the seed
    random.seed(time.time())

    # Randomly select a user-agent string
    user_agent = random.choice(user_agents)

    # Add the user-agent string to the options
    options.add_argument(user_agent) 

    driver = webdriver.Chrome(service=webdriver_service, options=options)

    # Get the page
    driver.get(url)

    # Create a WebDriverWait object
    wait = WebDriverWait(driver, 20)  # Wait for up to 20 seconds

    # Extract the required information
    try:
        journal = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a.stats-document-abstract-publishedIn'))).text
    except Exception as e:
        journal = None
        print(f"Error fetching journal for URL {url}: {e}")

    try:
        doi = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[href^="https://doi.org/"]'))).text
    except Exception as e:
        doi = None
        print(f"Error fetching DOI for URL {url}: {e}")
        
    try:
        publication_div = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.u-pb-1.doc-abstract-pubdate')))
        date_string = publication_div.text.split("Date of Publication:")[1].strip()
        date_object = datetime.strptime(date_string, "%d %B %Y")
        date_of_publication = date_object.strftime("%Y-%m-%d")
    except Exception as e:
        date_of_publication = None
        print(f"Error fetching date of publication for URL {url}: {e}")

    try:
        first_author = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'a[triggers="hover"] span'))).text
    except Exception as e:
        first_author = None
        print(f"Error fetching first author for URL {url}: {e}")

    try:
        title = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.document-title'))).text
    except Exception as e:
        title = None
        print(f"Error fetching title for URL {url}: {e}")

    try:
        abstract = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div.abstract-text'))).text
    except Exception as e:
        abstract = None
        print(f"Error fetching abstract for URL {url}: {e}")

    # Close the driver
    driver.quit()
    return pd.Series([journal, doi, date_of_publication, first_author, title, abstract])


####
def ieee_parser(antibiotics_keywords: list, ai_keywords: list) -> pd.DataFrame: 
    
    # Generate all pairs of keywords
    keyword_pairs = list(itertools.product(search_word_tokenizer(antibiotics_keywords, ai_keywords)))
    
    # Generate URLs for each pair of keywords
    ieee_urls = [generate_ieee_urls(pair, 1) for pair in keyword_pairs]
    
    # Flatten the list of lists
    ieee_urls = [url for sublist in ieee_urls for url in sublist]

    # Convert the list of URLs to a DataFrame
    ieee_urls = pd.DataFrame(ieee_urls, columns=['URL'])

    # Create a list to store the results
    urls = []
    
    #  Apply the parse_links_selenium function to each URL in the dataframe
    for url in tqdm(ieee_urls['URL']):
        links = parse_links_selenium(url)
        for link in links:
            urls.append({'URL': link})

    # Create a DataFrame from the results and remove duplicates
    urls = pd.DataFrame(urls).drop_duplicates()

    # Assuming ieee_results is a DataFrame with a column 'Link' containing the URLs
    # Initialize an empty list to hold the results
    results = []

    # Use tqdm to show progress
    for url in tqdm(urls['URL']):
        results.append(parse_info_selenium(url))

    # Convert the list of results to a DataFrame
    results_df = pd.DataFrame(results, columns=['Journal', 'DOI', 'Date of Publication', 'First Author', 'Title', 'Abstract'])

    print(type(urls), type(results_df))
    # Concatenate the original dataframe with the new information
    ieee_results = pd.concat([urls, results_df], axis=1)

    # Output the final DataFrame
    return ieee_results




