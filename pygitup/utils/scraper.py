import requests
import re
from bs4 import BeautifulSoup
from .ui import print_warning

def extract_social_links(text):
    """Extracts social media links from text using regex."""
    if not text:
        return []
    
    patterns = {
        "Twitter/X": r'https?://(www\.)?(twitter\.com|x\.com)/[a-zA-Z0-9_]+',
        "LinkedIn": r'https?://(www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+',
        "Discord": r'https?://(discord\.gg|discord\.com/invite)/[a-zA-Z0-9]+',
        "Medium": r'https?://(www\.)?medium\.com/@[a-zA-Z0-9_]+',
        "YouTube": r'https?://(www\.)?youtube\.com/(channel/|c/|user/)?[a-zA-Z0-9_-]+',
        "Patreon": r'https?://(www\.)?patreon\.com/[a-zA-Z0-9_-]+'
    }
    
    found = []
    for platform, pattern in patterns.items():
        matches = re.findall(pattern, text)
        for match in matches:
            # re.findall returns tuples if groups are present, or strings
            # We need to reconstruct or just grab the full match if possible.
            # Simplified approach: finditer for full match
            pass
    
    # Better approach with finditer to get full URLs
    results = {}
    for platform, pattern in patterns.items():
        for match in re.finditer(pattern, text):
            results[platform] = match.group(0)
    
    return results

def scrape_repo_info(url):
    """
    Scrapes public repository information from its GitHub HTML page.
    Returns a dictionary structure similar to the API response.
    """
    print_warning(f"API failed or enhancing data. Scraping deep intel from {url}...")
    
    try:
        response = requests.get(url)
        if response.status_code != 200:
            return None
            
        soup = BeautifulSoup(response.text, 'html.parser')
        data = {}
        
        # --- Basic Identity ---
        path_parts = url.strip("/").split("/")
        if len(path_parts) >= 2:
            data['owner'] = {'login': path_parts[-2]}
            data['name'] = path_parts[-1]
            data['full_name'] = f"{path_parts[-2]}/{path_parts[-1]}"
            
        # --- Description & Website ---
        desc_tag = soup.find('p', class_='f4 my-3')
        data['description'] = desc_tag.get_text(strip=True) if desc_tag else "No description found"
        
        website_tag = soup.find('a', role='link', rel=lambda x: x and 'nofollow' in x and 'me' not in x) # Heuristic
        # Better heuristic: Sidebar link often has class 'text-bold' inside the about section? 
        # Actually, let's look for the link in the sidebar grid
        sidebar = soup.find('div', class_='BorderGrid-cell')
        if sidebar:
             link = sidebar.find('a', href=True, class_='text-bold') # Usually the website
             if link and 'github.com' not in link['href']: # avoid internal links
                 data['homepage'] = link['href']

        # --- Statistics (Stars, Forks, Watchers, Issues) ---
        def get_count(href_suffix, id_fallback=None):
            val = "0"
            # Try by ID first
            if id_fallback:
                tag = soup.find(id=id_fallback)
                if tag: val = tag.get('title') or tag.get_text(strip=True)
            
            # Try by href if ID failed or returned label
            if val == "0" or not any(char.isdigit() for char in val):
                link = soup.find('a', href=lambda x: x and x.endswith(href_suffix))
                if link:
                    count_span = link.find('span', class_='Counter')
                    val = count_span.get('title') if count_span else link.get_text(strip=True)
            
            # Clean: Extract only digits/commas
            digits = re.sub(r'[^0-9,.]', '', val)
            return digits if digits else "0"

        data['stargazers_count'] = get_count('/stargazers', 'repo-stars-counter-star')
        data['forks_count'] = get_count('/forks', 'repo-network-counter')
        data['open_issues_count'] = get_count('/issues')
        data['watchers_count'] = get_count('/watchers')

        # --- Deep Footprint Scan (Description + README) ---
        all_text = data['description']
        
        # Try to find README link to scrape more text
        readme_link = soup.find('div', id='readme')
        if readme_link:
            all_text += "\n" + readme_link.get_text(strip=True)
            
        data['social_links'] = extract_social_links(all_text)

        # --- OSINT: Community & Sustainability ---
        # 1. Used By (Dependents)
        used_by_link = soup.find('a', href=lambda x: x and '/network/dependents' in x)
        if used_by_link:
            count_span = used_by_link.find('span', class_='Counter')
            data['used_by'] = count_span.get('title') if count_span else used_by_link.get_text(strip=True)
        
        # 2. Sponsorship Status
        sponsor_btn = soup.find('a', href=lambda x: x and '/sponsors/' in x)
        data['is_sponsored'] = True if sponsor_btn else False

        # --- OSINT: Preview Image ---
        og_image = soup.find('meta', property='og:image')
        data['social_preview'] = og_image.get('content') if og_image else None
        
        return data
        
    except Exception as e:
        print_warning(f"Scraping failed: {e}")
        return None