import requests
import json
import re
import os
import threading
# from tqdm import tqdm
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

if not os.path.exists("html_files2"):
    os.makedirs("html_files2")
directory = "html_files2"
pattern1 = r'([.]html$|[/]$|^[/])'
pattern2 = r'[/]'
quotes_and_author = []
authors = []
lock = threading.Lock()

def create_file_name(url):
    stripped_url = re.sub(pattern1, '', url)
    replaced_text = re.sub(pattern2, '_', stripped_url)
    # print(replaced_text)
    file_name = f'{replaced_text}.html'
    return file_name

@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=4, max=10),
       retry=retry_if_exception_type(requests.exceptions.RequestException))
def get_soup(url):
    try:
        response = requests.get("https://www.azquotes.com/" + url, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        file_name = create_file_name(url)
        file_path = os.path.join(directory, file_name)
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(response.text)
        return soup
    except requests.exceptions.RequestException as e:
        print(e)
        return None

def getting_initial_links():
    soup = get_soup("quotes/topics/focus.html")
    authors_ul = soup.find('ul', class_='authors')
    li_tags = authors_ul.find_all('li')
    href_links = [li.find('a')['href'] for li in li_tags]
    href_links.pop(0)
    return href_links

def getting_all_authors_belonging_to_an_alphabet(url):
    soup = get_soup(url)
    if soup is None:
        return None
    # Extracting links from the table
    table = soup.find('table', class_='table')
    if table:
        for a_tag in table.find_all('a'):
            with lock:
                authors.append(a_tag.get('href'))
            # print(a_tag.get('href'))
    
    # Checking for 'next' link
    next_li = soup.find('li', class_='next')
    if next_li and next_li.find('a'):
        next_url = next_li.find('a').get('href')
        if next_url:
            getting_all_authors_belonging_to_an_alphabet("quotes" + next_url)
    for author in authors:
        t = threading.Thread(target=getting_quotes, args = [author])
        t.start()
    
def getting_quotes(url):
    
    soup = get_soup(url)
    if soup is None:
        return None
    title_tags = soup.find_all('a', class_='title')
    quotes = [tag.get_text() for tag in title_tags]
    author_div = soup.find('div', class_='author')
    author = author_div.find('a').get_text(strip=True) if author_div and author_div.find('a') else None
    # next_link = None
    for quote in quotes:
        with lock:
            dictionary = {
                "quote" : quote,
                "author" : author
            }
            quotes_and_author.append(dictionary) 
    with lock:
        save_file = open("savedata2.json", "w")  
        json.dump(quotes_and_author, save_file, indent = 6)  
        save_file.close() 
    next_li = soup.find('li', class_='next')
    if next_li:
        next_a = next_li.find('a')
        # print(quotes)
        # print(author)
        if next_a and 'href' in next_a.attrs:
            next_link = next_a['href']
        else: 
            return None
    else: 
        return None

    getting_quotes(next_link)
    
def main():
    href_links = getting_initial_links()
    # # print(href_links)
    for link in href_links:
        # getting_all_authors_belonging_to_an_alphabet(link)
        t = threading.Thread(target=getting_all_authors_belonging_to_an_alphabet, args = [link])
        t.start()
    
if __name__ == '__main__':
    main()