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
            # Try by ID first
            if id_fallback:
                tag = soup.find(id=id_fallback)
                if tag: return tag.get('title') or tag.get_text(strip=True)
            
            # Try by href
            link = soup.find('a', href=lambda x: x and x.endswith(href_suffix))
            if link:
                count_span = link.find('span', class_='Counter')
                return count_span.get('title') if count_span else link.get_text(strip=True)
            return "N/A"

        data['stargazers_count'] = get_count('/stargazers', 'repo-stars-counter-star')
        data['forks_count'] = get_count('/forks', 'repo-network-counter')
        data['open_issues_count'] = get_count('/issues') # ID issues-tab usually works but let's be safe
        
        # Watchers (Often hidden in the 'Watch' dropdown, hard to scrape directly from main page sometimes, 
        # but usually /watchers page link exists in sidebar or header)
        data['watchers_count'] = get_count('/watchers')

        # --- Contributors ---
        # Sidebar link to /contributors
        contrib_link = soup.find('a', href=lambda x: x and x.endswith('/contributors'))
        if contrib_link:
            count_span = contrib_link.find('span', class_='Counter')
            data['contributors_count'] = count_span.get('title') if count_span else None
        else:
            data['contributors_count'] = None

        # --- License ---
        # Look for "License" header in sidebar or file
        license_header = soup.find('h3', string='License')
        if license_header:
            # The next sibling or link usually contains the license name
            # This is tricky with BS4 structure variations.
            # Alternative: Search for the LICENSE file link in the file list or sidebar
            license_link = soup.find('a', href=lambda x: x and 'LICENSE' in x and 'blob' in x) # File list
            # Or sidebar link
            sidebar_license = soup.find('a', href=lambda x: x and '/blob/' in x and 'LICENSE' in x)
            if sidebar_license:
                 # Often the text is "MIT License" or similar
                 data['license'] = {'name': sidebar_license.get_text(strip=True)}
        
        # If not found, try finding a simplified "License" link in the About section
        if 'license' not in data:
            about_license = soup.find('a', href=lambda x: x and 'LICENSE' in x)
            if about_license:
                 data['license'] = {'name': about_license.get_text(strip=True)}

        # --- Language ---
        lang_item = soup.find('span', class_='color-fg-default text-bold mr-1')
        data['language'] = lang_item.get_text(strip=True) if lang_item else "Unknown"
             
        # --- Metadata ---
        data['private'] = False
        data['clone_url'] = f"{url}.git"
        
        # --- Latest Release ---
        release_header = soup.find('a', href=lambda x: x and '/releases/tag/' in x)
        if release_header:
            data['latest_release'] = release_header.get_text(strip=True)
            # Try to get date
            # relative-time datetime="..."
            time_tag = release_header.find_next('relative-time')
            if time_tag:
                data['latest_release_date'] = time_tag.get('datetime')
        
        # --- OSINT: Dependencies ---
        used_by_tag = soup.find('a', href=lambda x: x and '/network/dependents' in x)
        if used_by_tag:
            count_span = used_by_tag.find('span', class_='Counter')
            data['used_by'] = count_span.get('title') if count_span else used_by_tag.get_text(strip=True)
        
        # --- OSINT: Sponsorship ---
        sponsor_btn = soup.find('a', href=lambda x: x and '/sponsors/' in x)
        data['is_sponsored'] = True if sponsor_btn else False

        # --- OSINT: Topics ---
        topics = []
        topic_tags = soup.find_all('a', class_='topic-tag')
        for t in topic_tags:
            topics.append(t.get_text(strip=True))
        data['topics'] = topics

        # --- OSINT: Social Links ---
        # Scan description and sidebar
        socials = extract_social_links(data['description'])
        data['social_links'] = socials

        # --- OSINT: Preview Image ---
        og_image = soup.find('meta', property='og:image')
        data['social_preview'] = og_image.get('content') if og_image else None
        
        return data
        
    except Exception as e:
        print_warning(f"Scraping failed: {e}")
        return None