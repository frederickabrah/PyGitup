import requests
import re
from bs4 import BeautifulSoup
from .ui import print_warning, print_info, print_success
from datetime import datetime

def extract_social_links(text):
    if not text:
        return {}

    patterns = {
        "Twitter/X": r'https?://(www\.)?(twitter\.com|x\.com)/[a-zA-Z0-9_]+',
        "LinkedIn": r'https?://(www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+',
        "Discord": r'https?://(discord\.gg|discord\.com/invite)/[a-zA-Z0-9]+',
        "Medium": r'https?://(www\.)?medium\.com/@[a-zA-Z0-9_]+',
        "YouTube": r'https?://(www\.)?youtube\.com/(channel/|c/|user/)?[a-zA-Z0-9_-]+',
        "Patreon": r'https?://(www\.)?patreon\.com/[a-zA-Z0-9_-]+',
        "Mastodon": r'https?://(www\.)?mastodon\.social/@[a-zA-Z0-9_]+',
        "Dev.to": r'https?://(www\.)?dev\.to/[a-zA-Z0-9_]+',
        "Hashnode": r'https?://(www\.)?[a-zA-Z0-9_]+\.hashnode\.dev',
        "Personal Blog": r'https?://(www\.)?[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?!.*(?:github|linkedin|twitter|facebook))'
    }

    results = {}
    for platform, pattern in patterns.items():
        for match in re.finditer(pattern, text):
            results[platform] = match.group(0)

    return results

def scrape_repo_info(url):
    print_info(f"Scraping repository data from {url}...")

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            print_warning(f"Scrape failed: HTTP {response.status_code}")
            return None

        soup = BeautifulSoup(response.text, 'html.parser')
        data = {}
        data['scrape_timestamp'] = datetime.utcnow().isoformat()
        data['source_url'] = url

        path_parts = url.strip("/").split("/")
        if len(path_parts) >= 2:
            data['owner'] = {'login': path_parts[-2]}
            data['name'] = path_parts[-1]
            data['full_name'] = f"{path_parts[-2]}/{path_parts[-1]}"
            data['github_url'] = url

        desc_tag = soup.find('p', class_='f4 my-3')
        data['description'] = desc_tag.get_text(strip=True) if desc_tag else "No description"
        
        sidebar = soup.find('div', class_='BorderGrid-cell')
        if sidebar:
            website_link = sidebar.find('a', href=True, class_='text-bold')
            if website_link and 'github.com' not in website_link['href']:
                data['homepage'] = website_link['href']

        def get_count(href_suffix, id_fallback=None):
            val = "0"
            if id_fallback:
                tag = soup.find(id=id_fallback)
                if tag: val = tag.get('title') or tag.get_text(strip=True)
            if val == "0" or not any(char.isdigit() for char in val):
                link = soup.find('a', href=lambda x: x and x.endswith(href_suffix))
                if link:
                    count_span = link.find('span', class_='Counter')
                    val = count_span.get('title') if count_span else link.get_text(strip=True)
            digits = re.sub(r'[^0-9,.]', '', val)
            return digits if digits else "0"

        data['stargazers_count'] = get_count('/stargazers', 'repo-stars-counter-star')
        data['forks_count'] = get_count('/forks', 'repo-network-counter')
        data['open_issues_count'] = get_count('/issues')
        data['watchers_count'] = get_count('/watchers')
        data['pull_requests_count'] = get_count('/pulls')

        commit_link = soup.find('a', href=lambda x: x and '/commits/' in x)
        if commit_link:
            count_tag = commit_link.find(['span', 'strong'], class_=lambda x: x and ('Counter' in x or 'num' in x))
            if not count_tag:
                count_tag = commit_link.find('span', class_='d-none d-sm-inline')
            val = count_tag.get_text(strip=True) if count_tag else commit_link.get_text(strip=True)
            data['commits_count'] = re.sub(r'[^0-9,]', '', val)
        else:
            data['commits_count'] = "N/A"

        branch_link = soup.find('a', href=lambda x: x and '/branches' in x)
        data['branches_count'] = branch_link.find('span', class_='Counter').get_text(strip=True) if branch_link and branch_link.find('span', class_='Counter') else "N/A"

        release_link = soup.find('a', href=lambda x: x and '/releases' in x)
        data['releases_count'] = release_link.find('span', class_='Counter').get_text(strip=True) if release_link and release_link.find('span', class_='Counter') else "0"

        tags_link = soup.find('a', href=lambda x: x and '/tags' in x)
        data['tags_count'] = tags_link.find('span', class_='Counter').get_text(strip=True) if tags_link and tags_link.find('span', class_='Counter') else "0"

        data['has_wiki'] = bool(soup.find('a', id='wiki-tab'))
        data['has_discussions'] = bool(soup.find('a', id='discussions-tab'))
        data['has_projects'] = bool(soup.find('a', id='projects-tab'))
        data['has_packages'] = bool(soup.find('a', href=lambda x: x and '/packages' in x))
        data['has_actions'] = bool(soup.find('a', href=lambda x: x and '/actions' in x))
        data['has_security_policy'] = bool(soup.find('a', href=lambda x: x and '/security/policy' in x))
        data['has_sponsors'] = bool(soup.find('a', href=lambda x: x and '/sponsors' in x))
        data['has_dependents'] = bool(soup.find('a', href=lambda x: x and '/network/dependents' in x))

        license_link = soup.find('a', href=lambda x: x and '/blob/' in x and ('LICENSE' in x or 'LICENSE' in x.upper()))
        if license_link:
            license_text = license_link.get_text(strip=True)
            data['license'] = {'name': license_text, 'spdx_id': license_text}
        else:
            badges = soup.find_all('img', alt=lambda x: x and 'license' in x.lower())
            if badges:
                data['license'] = {'name': 'Unknown', 'spdx_id': 'UNKNOWN'}

        data['has_security_policy'] = bool(soup.find('a', href=lambda x: x and '/security/policy' in x))
        data['has_code_of_conduct'] = bool(soup.find('a', href=lambda x: x and 'CODE_OF_CONDUCT' in x.upper()))
        data['has_contributing'] = bool(soup.find('a', href=lambda x: x and 'CONTRIBUTING' in x.upper()))

        badges = []
        for img in soup.find_all('img'):
            alt = img.get('alt', '')
            src = img.get('src', '')
            if 'Build' in alt or 'CI' in alt or 'Action' in alt or 'workflow' in src.lower():
                status = "Passing" if 'passing' in src or 'success' in src else "Failing" if 'failing' in src else "Unknown"
                badges.append(f"CI: {status}")
        data['ci_status'] = badges[0] if badges else "N/A"

        languages = []
        lang_section = soup.find('h2', string=re.compile(r'Languages', re.I))
        if lang_section:
            lang_container = lang_section.find_parent('div')
            if lang_container:
                for item in lang_container.find_all('li', class_='d-inline'):
                    text = item.get_text(separator=' ', strip=True)
                    languages.append(text)
        data['languages_full'] = languages if languages else ["N/A"]

        topics = []
        topic_tags = soup.find_all('a', class_='topic-tag-link')
        for topic in topic_tags:
            topics.append(topic.get_text(strip=True))
        data['topics'] = topics if topics else []

        used_by_link = soup.find('a', href=lambda x: x and '/network/dependents' in x)
        if used_by_link:
            used_by_text = used_by_link.get_text(strip=True)
            match = re.search(r'[\d,]+', used_by_text)
            data['used_by'] = int(match.group().replace(',', '')) if match else 0
        else:
            data['used_by'] = 0

        data['is_sponsored'] = bool(soup.find('button', string=re.compile(r'Sponsor', re.I)))

        social_preview = soup.find('meta', property='og:image')
        if social_preview:
            data['social_preview'] = social_preview.get('content')

        twitter_card = soup.find('meta', attrs={'name': 'twitter:card'})
        if twitter_card:
            data['twitter_card'] = twitter_card.get('content')

        readme_section = soup.find('article', class_='Box-body')
        if readme_section:
            try:
                readme_text = readme_section.get_text()
                data['social_links'] = extract_social_links(readme_text)
            except:
                data['social_links'] = {}
        else:
            data['social_links'] = {}

        contributors_link = soup.find('a', href=lambda x: x and '/graphs/contributors' in x)
        if contributors_link:
            contributors_text = contributors_link.get_text(strip=True)
            match = re.search(r'[\d,]+', contributors_text)
            data['contributors_count'] = int(match.group().replace(',', '')) if match else 0
        else:
            data['contributors_count'] = "N/A"

        release_section = soup.find('a', class_='Link--primary', href=lambda x: x and '/releases/tag' in x)
        if release_section:
            release_name = release_section.get_text(strip=True)
            data['latest_release'] = release_name

        readme = soup.find('article', class_='Box-body')
        if readme:
            readme_text = readme.get_text(strip=True)[:1000]
            data['readme_preview'] = readme_text
            tech_keywords = ['python', 'javascript', 'react', 'node', 'api', 'docker', 'kubernetes', 'aws', 'azure', 'machine learning', 'ai', 'blockchain']
            detected_tech = [tech for tech in tech_keywords if tech in readme_text.lower()]
            data['detected_technologies'] = detected_tech

        files = []
        file_items = soup.find_all('td', class_='content', itemprop='name')
        for item in file_items[:20]:
            files.append(item.get_text(strip=True))
        data['top_level_files'] = files

        relative_time = soup.find('relative-time')
        if relative_time:
            data['last_activity'] = relative_time.get('datetime', 'Unknown')

        branch_select = soup.find('select', class_='branch-select-menu')
        if branch_select:
            branches = [opt.get_text(strip=True) for opt in branch_select.find_all('option')]
            data['available_branches'] = branches[:10]

        env_indicators = {}
        for file in files:
            file_lower = file.lower()
            if 'docker' in file_lower:
                env_indicators['docker'] = True
            if 'requirements.txt' in file_lower:
                env_indicators['python'] = True
            if 'package.json' in file_lower:
                env_indicators['nodejs'] = True
            if 'Cargo.toml' in file_lower:
                env_indicators['rust'] = True
            if 'go.mod' in file_lower:
                env_indicators['golang'] = True
            if 'pom.xml' in file_lower or 'build.gradle' in file_lower:
                env_indicators['java'] = True
            if 'Gemfile' in file_lower:
                env_indicators['ruby'] = True
            if 'composer.json' in file_lower:
                env_indicators['php'] = True
        data['detected_environments'] = env_indicators

        watch_link = soup.find('a', href=lambda x: x and '/watchers' in x)
        if watch_link:
            watch_count = watch_link.find('span', class_='Counter')
            data['watch_count'] = watch_count.get_text(strip=True) if watch_count else "0"

        releases_section = soup.find('div', class_='Box-body', id='release-list')
        if releases_section:
            assets = releases_section.find_all('a', href=lambda x: x and '/releases/download/' in x)
            data['release_assets_count'] = len(assets)

        favicon = soup.find('link', rel='icon')
        if favicon:
            data['has_custom_favicon'] = True

        manifest = soup.find('link', rel='manifest')
        data['has_pwa'] = bool(manifest)

        meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
        if meta_keywords:
            data['github_keywords'] = meta_keywords.get('content', '')

        canonical = soup.find('link', rel='canonical')
        if canonical:
            data['canonical_url'] = canonical.get('href')

        robots = soup.find('meta', attrs={'name': 'robots'})
        if robots:
            data['robots_directive'] = robots.get('content')

        data['html_lang'] = soup.find('html').get('lang', 'en') if soup.find('html') else 'en'
        data['body_class'] = soup.find('body').get('class', []) if soup.find('body') else []

        page_context = soup.find('div', class_='application-main')
        data['has_modern_ui'] = bool(page_context)

        repo_flags = soup.find_all('span', class_='Label')
        flags = [flag.get_text(strip=True) for flag in repo_flags]
        if flags:
            data['repository_flags'] = flags

        graph_links = soup.find_all('a', href=lambda x: x and '/graphs/' in x)
        data['has_analytics_graphs'] = len(graph_links) > 0

        if readme_section:
            workflow_badges = readme_section.find_all('img', src=lambda x: x and 'github.com/workflows' in str(x))
            data['workflow_badges_count'] = len(workflow_badges)

        issue_template = soup.find('a', href=lambda x: x and '/issues/new' in x)
        data['has_issue_templates'] = bool(issue_template)

        code_tab = soup.find('a', id='code-tab')
        data['code_tab_enabled'] = bool(code_tab)

        insights_tab = soup.find('a', href=lambda x: x and '/pulse' in x)
        data['insights_enabled'] = bool(insights_tab)

        settings_link = soup.find('a', href=lambda x: x and '/settings' in x)
        data['user_has_access'] = bool(settings_link)

        archive_banner = soup.find('div', class_='archived-banner')
        data['is_archived'] = bool(archive_banner)

        template_btn = soup.find('button', string=re.compile(r'Use this template', re.I))
        data['is_template_repo'] = bool(template_btn)

        gen_btn = soup.find('a', href=lambda x: x and '/releases/new' in x)
        data['can_create_releases'] = bool(gen_btn)

        print_success(f"OSINT scan complete! Extracted {len(data)} data points")
        return data

    except Exception as e:
        print_warning(f"OSINT scan failed: {e}")
        return None