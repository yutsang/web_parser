import pandas as pd
from tqdm import tqdm
import itertools
from multiprocessing import Pool
import requests
from bs4 import BeautifulSoup
from nltk.tokenize import word_tokenize
import re
from tqdm import tqdm

# Define the search keywords
antibiotics_keywords = ["antibiotic resistance", "antimicrobial resistance", "AMR"]
ai_keywords = ["deep learning", "neural network", "embedding", "interpretable", "autoencoders", "CNN", "convolutional", "LSTM", "long short-term memory", "NLP", "Natural Language Processing", "transformer", "BERT"]

# Tokenize the keywords for easier matching
antibiotics_tokens = set(word_tokenize(" ".join(antibiotics_keywords)))
ai_tokens = set(word_tokenize(" ".join(ai_keywords)))


# Function to search Google Scholar with pagination
def search_google_scholar(query, num_pages=10):
    articles = []
    for page in tqdm(range(num_pages), desc="Parsing Google Scholar"):
        url = f"https://scholar.google.com/scholar?q={query}&start={page*10}&as_ylo=2023&as_yhi=2024"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        for item in soup.select('[data-lid]'):
            title = item.select_one('.gs_rt').text
            authors = item.select_one('.gs_a').text
            snippet = item.select_one('.gs_rs').text
            link = item.select_one('.gs_rt a')['href']
            articles.append({'Title': title, 'Authors': authors, 'Snippet': snippet, 'Link': link, 'Source': 'Google Scholar'})
    return articles

# Function to search PubMed with pagination
def search_pubmed(query, num_pages=10):
    articles = []
    for page in tqdm(range(num_pages), desc="Parsing PubMed"):
        url = f"https://pubmed.ncbi.nlm.nih.gov/?term={query}&filter=years.2023-2024&page={page+1}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        for item in soup.select('.docsum-content'):
            title = item.select_one('.docsum-title').text.strip()
            authors = item.select_one('.docsum-authors').text.strip()
            snippet = item.select_one('.full-view-snippet').text.strip() if item.select_one('.full-view-snippet') else ''
            link = "https://pubmed.ncbi.nlm.nih.gov" + item.select_one('.docsum-title')['href']
            articles.append({'Title': title, 'Authors': authors, 'Snippet': snippet, 'Link': link, 'Source': 'PubMed'})
    return articles


# Function to search IEEE Xplore with pagination
def search_ieee(keyword_pair, num_pages=5):
    articles = []
    for page in range(num_pages):
        query = "%20".join(keyword_pair).replace(' ', '%20')  # Join the keywords with %20 to form the query
        url = f"https://ieeexplore.ieee.org/search/searchresult.jsp?queryText={query}&highlight=true&returnType=SEARCH&matchPubs=true&ranges=2023_2024_Year&returnFacets=ALL&refinements=ContentType:Journals&pageNumber={page+1}"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        for item in soup.select('.List-results-items'):
            title = item.select_one('.title').text.strip()
            authors = item.select_one('.author').text.strip()
            snippet = item.select_one('.description').text.strip() if item.select_one('.description') else ''
            link = "https://ieeexplore.ieee.org" + item.select_one('.title a')['href']
            articles.append({'Title': title, 'Authors': authors, 'Snippet': snippet, 'Link': link, 'Source': 'IEEE Xplore'})
    return articles

# Function to extract and parse references from articles
def extract_references(article_url, depth=2):
    connected_articles = []
    try:
        response = requests.get(article_url)
        soup = BeautifulSoup(response.text, 'html.parser')
        references = []
        for ref in soup.find_all('a', href=True):
            if 'doi' in ref['href']:
                references.append(ref['href'])
        for ref in references:
            response = requests.get(ref)
            soup = BeautifulSoup(response.text, 'html.parser')
            title = soup.select_one('.title').text.strip()
            authors = soup.select_one('.author').text.strip()
            snippet = soup.select_one('.description').text.strip() if soup.select_one('.description') else ''
            article = {'Title': title, 'Authors': authors, 'Snippet': snippet, 'Link': ref}
            connected_articles.append(article)
            if depth > 1:
                article['References'] = extract_references(ref, depth-1)
    except:
        pass
    return connected_articles

# Define a function that takes a URL and returns its references
def get_references(url):
    return url, extract_references(url)

# Apply the is_relevant function to the connected articles
def apply_is_relevant_to_connected_articles(articles):
    relevant_articles = []
    for article in articles:
        if is_relevant(article):
            relevant_articles.append(article)
        if 'References' in article:
            relevant_articles.extend(apply_is_relevant_to_connected_articles(article['References']))
    return relevant_articles
    

# Function to check if an article is relevant
def is_relevant(article):
    title_tokens = set(word_tokenize(article['Title'].lower()))
    snippet_tokens = set(word_tokenize(article['Snippet'].lower()))
    return (antibiotics_tokens & title_tokens or antibiotics_tokens & snippet_tokens) and (ai_tokens & title_tokens or ai_tokens & snippet_tokens)


# Check if all links are connectable
def check_link(link):
    try:
        response = requests.get(link)
        return response.status_code == 200
    except:
        return False