import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
from tqdm import tqdm
import time
from fake_useragent import UserAgent

# Function to search Google Scholar with pagination and error handling
def search_google_scholar(query, num_pages=10):
    articles = []
    
    # Initialize the UserAgent object
    ua = UserAgent()

    for page in range(num_pages):
        url = f"https://scholar.google.com/scholar?q={query}&start={page*10}&as_ylo=2023&as_yhi=2024"
        for attempt in range(3):  # Retry mechanism
            try:
                # In your request, set the 'User-Agent' header to a random User-Agent string
                response = requests.get(url, headers={'User-Agent': ua.random})
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                for item in soup.select('[data-lid]'):
                    title = item.select_one('.gs_rt').text
                    authors = item.select_one('.gs_a').text
                    snippet = item.select_one('.gs_rs').text
                    link = item.select_one('.gs_rt a')['href']
                    articles.append({'Title': title, 'Authors': authors, 'Snippet': snippet, 'Link': link, 'Source': 'Google Scholar'})
                break  # Exit retry loop if successful
            except Exception as e:
                print(f"Error fetching Google Scholar page {page+1}: {e}")
                time.sleep(2)  # Wait before retrying
    
    # Perform searches with pagination sequentially and remove duplicates
    articles_df = pd.DataFrame(articles).drop_duplicates(subset=['Title'])

    # Extract references for each article
    articles_df['References'] = articles_df['Link'].apply(extract_references)

    # Extract first author and other authors
    articles_df['First Author'] = articles_df['Authors'].apply(lambda x: x.split(',')[0])
    articles_df['Other Authors'] = articles_df['Authors'].apply(lambda x: ', '.join(x.split(',')[1:]))

    # Extract year of publication
    articles_df['Year'] = articles_df['Authors'].apply(lambda x: re.search(r'\d{4}', x).group() if re.search(r'\d{4}', x) else 'Unknown')

    # Extract journal and DOI
    articles_df['Journal'] = articles_df['Link'].apply(lambda x: x.split('/')[2] if 'doi' in x else 'Unknown')
    articles_df['DOI'] = articles_df['Link'].apply(lambda x: x.split('/')[-1] if 'doi' in x else 'Unknown')

    articles_df['Link Connectable'] = articles_df['Link'].apply(check_link)
    
    return articles_df

# Function to extract references from articles
def extract_references(article_url):
    try:
        response = requests.get(article_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        references = []
        for ref in soup.find_all('a', href=True):
            if 'doi' in ref['href']:
                references.append(ref['href'])
        return references
    except Exception as e:
        print(f"Error extracting references from {article_url}: {e}")
        return []

# Check if all links are connectable
def check_link(link):
    try:
        response = requests.get(link)
        return response.status_code == 200
    except Exception as e:
        print(f"Error checking link {link}: {e}")
        return False