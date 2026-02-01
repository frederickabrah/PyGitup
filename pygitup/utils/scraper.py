
import requests
from bs4 import BeautifulSoup
from .ui import print_warning

def scrape_repo_info(url):
    """
    Scrapes public repository information from its GitHub HTML page.
    Returns a dictionary structure similar to the API response.
    """
    print_warning(f"API failed. Attempting to scrape data from {url}...")
    
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        data = {}
        
        # Extract Owner and Name
        path_parts = url.strip("/").split("/")
        if len(path_parts) >= 2:
            data['owner'] = {'login': path_parts[-2]}
            data['name'] = path_parts[-1]
            data['full_name'] = f"{path_parts[-2]}/{path_parts[-1]}"
            
        # Extract Description
        # GitHub usually puts description in 'p.f4' inside the border grid or layout
        desc_tag = soup.find('p', class_='f4 my-3')
        data['description'] = desc_tag.get_text(strip=True) if desc_tag else "No description found (scraped)"
        
        # Extract Stars
        # Looking for the star count in the sidebar or header
        # Current GitHub layout often uses a span with id 'repo-stars-counter-star' 
        # or an 'a' tag with specific href
        star_tag = soup.find(id='repo-stars-counter-star')
        if star_tag:
             data['stargazers_count'] = star_tag.get('title') or star_tag.get_text(strip=True)
        else:
             # Fallback: finding the 'a' tag with 'stargazers' in href
             star_link = soup.find('a', href=lambda x: x and x.endswith('/stargazers'))
             if star_link:
                 # The count is usually in a span inside or just the text
                 count_span = star_link.find('span', class_='Counter')
                 data['stargazers_count'] = count_span.get('title') if count_span else star_link.get_text(strip=True)
             else:
                 data['stargazers_count'] = "N/A"

        # Extract Forks
        fork_tag = soup.find(id='repo-network-counter')
        if fork_tag:
            data['forks_count'] = fork_tag.get('title') or fork_tag.get_text(strip=True)
        else:
             fork_link = soup.find('a', href=lambda x: x and x.endswith('/forks'))
             if fork_link:
                 count_span = fork_link.find('span', class_='Counter')
                 data['forks_count'] = count_span.get('title') if count_span else fork_link.get_text(strip=True)
             else:
                 data['forks_count'] = "N/A"
                 
        # Extract Issues
        issues_tab = soup.find(id='issues-tab')
        if issues_tab:
            count_span = issues_tab.find('span', class_='Counter')
            data['open_issues_count'] = count_span.get('title') if count_span else "N/A"
        else:
            data['open_issues_count'] = "N/A"
            
        # Extract Language
        # Found in the 'Languages' section of the sidebar
        lang_header = soup.find('h2', string='Languages')
        if lang_header:
            # The list is usually in a ul following the header, but specific class structures vary.
            # A common reliable pattern is finding the list of languages progress bar or the stats list.
            # Trying to find the first language span in the sidebar stats.
            lang_item = soup.find('span', class_='color-fg-default text-bold mr-1')
            data['language'] = lang_item.get_text(strip=True) if lang_item else "Unknown"
        else:
             data['language'] = "Unknown"
             
        # Metadata
        data['private'] = False # If we can scrape it publicly, it's public
        data['clone_url'] = f"{url}.git"
        data['created_at'] = "Unknown (Scraped)" # Hard to scrape reliably without parsing timestamps
        
        # OSINT: Used By (Dependents)
        used_by_tag = soup.find('a', href=lambda x: x and '/network/dependents' in x)
        if used_by_tag:
            count_span = used_by_tag.find('span', class_='Counter')
            data['used_by'] = count_span.get('title') if count_span else used_by_tag.get_text(strip=True)
        
        # OSINT: Sponsorship Status
        sponsor_btn = soup.find('a', href=lambda x: x and '/sponsors/' in x)
        data['is_sponsored'] = True if sponsor_btn else False

        # OSINT: Topics/Tags
        topics = []
        topic_tags = soup.find_all('a', class_='topic-tag')
        for t in topic_tags:
            topics.append(t.get_text(strip=True))
        data['topics'] = topics

        # OSINT: Social Preview Image
        og_image = soup.find('meta', property='og:image')
        data['social_preview'] = og_image.get('content') if og_image else None
        
        return data
        
    except Exception as e:
        print_warning(f"Scraping failed: {e}")
        return None
