"""
Email Populator Service

Fetches email, LinkedIn, and portfolio from GitHub profiles and portfolio websites.
Used after Add Experts (CSV / comma-separated usernames / GitHub repo) to fill
contact info for experts that don't have email yet.
"""
import re
import time
from typing import Optional, Dict, List

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

try:
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.support.ui import WebDriverWait
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_SUPPORT = True
except ImportError:
    SELENIUM_SUPPORT = False


def _urljoin(base: str, path: str) -> str:
    from urllib.parse import urlparse, urljoin
    return urljoin(base, path)


class EmailPopulator:
    """Fetches email, LinkedIn, portfolio from GitHub and portfolio sites."""

    def __init__(self, github_token: Optional[str] = None, use_selenium: bool = False):
        self.github_token = github_token
        self.session = requests.Session() if REQUESTS_AVAILABLE else None
        self.use_selenium = use_selenium and SELENIUM_SUPPORT
        self.driver = None

        if self.session:
            if github_token:
                self.session.headers.update({
                    'Authorization': f'token {github_token}',
                    'Accept': 'application/vnd.github.v3+json'
                })
            else:
                self.session.headers.update({'Accept': 'application/vnd.github.v3+json'})

        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        self.linkedin_pattern = re.compile(
            r'(?:https?://)?(?:www\.)?linkedin\.com/in/([a-zA-Z0-9_-]+)/?',
            re.IGNORECASE
        )
        self.url_pattern = re.compile(
            r'https?://(?:www\.)?([a-zA-Z0-9-]+\.(?:com|io|dev|me|net|org|co|in|tech|app|xyz))(?:/[^\s]*)?',
            re.IGNORECASE
        )
        self.exclude_patterns = [
            r'\.png@', r'\.jpg@', r'noreply\.github', r'example\.com', r'your-email@'
        ]

        if self.use_selenium:
            self._init_selenium()

    def _init_selenium(self):
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
        except Exception:
            self.use_selenium = False
            self.driver = None

    def __del__(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass

    def is_valid_email(self, email: str) -> bool:
        if not email or len(email) > 100 or len(email) < 5:
            return False
        for pat in self.exclude_patterns:
            if re.search(pat, email.lower()):
                return False
        return True

    def extract_emails_from_text(self, text: str) -> List[str]:
        if not text:
            return []
        emails = self.email_pattern.findall(text)
        return list(set(e for e in emails if self.is_valid_email(e)))

    def extract_linkedin_url(self, text: str) -> Optional[str]:
        if not text:
            return None
        m = self.linkedin_pattern.search(text)
        return f"https://linkedin.com/in/{m.group(1)}" if m else None

    def extract_portfolio_urls(self, text: str) -> List[str]:
        if not text:
            return []
        urls = []
        for m in self.url_pattern.finditer(text):
            u = m.group(0)
            if 'github.com' not in u.lower() and 'linkedin.com' not in u.lower():
                urls.append(u)
        for word in text.split():
            word = word.strip('()[]<>,;"\'')
            if (word.startswith(('http://', 'https://')) or ('.' in word and any(x in word.lower() for x in ['.com', '.io', '.dev']))):
                if not word.startswith(('http://', 'https://')):
                    word = 'https://' + word
                if 'github.com' not in word.lower() and 'linkedin.com' not in word.lower():
                    urls.append(word)
        return list(set(urls))

    def get_github_profile_data(self, username: str) -> Optional[Dict]:
        if not username or not self.session:
            return None
        result = {'email': None, 'linkedin': None, 'portfolio': None, 'bio': None}
        try:
            r = self.session.get(f'https://api.github.com/users/{username}', timeout=10)
            if r.status_code != 200:
                return None
            data = r.json()
            bio = data.get('bio', '') or ''
            result['bio'] = bio

            if data.get('email') and self.is_valid_email(data['email']):
                result['email'] = data['email']

            if bio:
                if not result['linkedin']:
                    result['linkedin'] = self.extract_linkedin_url(bio)
                if not result['email']:
                    emails = self.extract_emails_from_text(bio)
                    if emails:
                        result['email'] = emails[0]
                if not result['portfolio']:
                    urls = self.extract_portfolio_urls(bio)
                    if urls:
                        result['portfolio'] = urls[0]

            if data.get('blog'):
                blog = data['blog'].strip()
                if blog:
                    if not blog.startswith(('http://', 'https://')):
                        blog = 'https://' + blog
                    if 'linkedin.com/in/' in blog.lower():
                        if not result['linkedin']:
                            result['linkedin'] = blog
                    elif not result['portfolio']:
                        result['portfolio'] = blog

            return result
        except Exception:
            return None

    def get_github_events_email(self, username: str) -> Optional[str]:
        if not username or not self.session:
            return None
        try:
            r = self.session.get(f'https://api.github.com/users/{username}/events/public', timeout=10)
            if r.status_code != 200:
                return None
            for event in r.json()[:10]:
                if event.get('type') == 'PushEvent':
                    for c in event.get('payload', {}).get('commits', [])[:3]:
                        email = (c.get('author') or {}).get('email')
                        if email and 'noreply.github.com' not in email and self.is_valid_email(email):
                            return email
        except Exception:
            pass
        return None

    def get_github_search_commits_email(self, username: str) -> Optional[str]:
        """Fallback: get author email from GitHub Search API (commits by author)."""
        if not username or not self.session:
            return None
        try:
            url = f'https://api.github.com/search/commits?q=author:{username}&sort=author-date&order=desc&per_page=30'
            headers = {'Accept': 'application/vnd.github.cloak-preview+json'}
            r = self.session.get(url, timeout=15, headers=headers)
            if r.status_code != 200:
                return None
            items = r.json().get('items', [])
            for item in items:
                commit = item.get('commit', {})
                author = commit.get('author', {})
                email = (author or {}).get('email')
                if email and 'noreply.github.com' not in email.lower() and self.is_valid_email(email):
                    return email
        except Exception:
            pass
        return None

    def extract_mailto_links(self, html: str) -> List[str]:
        patterns = [
            r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})',
            r'mailto:([a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,})\?',
        ]
        out = []
        for p in patterns:
            for m in re.finditer(p, html, re.IGNORECASE):
                e = m.group(1).replace('%40', '@').strip()
                if self.is_valid_email(e):
                    out.append(e)
        return list(set(out))

    def get_portfolio_email(self, url: str) -> Optional[str]:
        if not url or not self.session:
            return None
        url = url.strip()
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        try:
            from urllib.parse import urlparse
            r = self.session.get(url, timeout=15, headers={'User-Agent': 'Mozilla/5.0'})
            if r.status_code != 200:
                return None
            html = r.text
            parsed = urlparse(url)
            domain = parsed.netloc.replace('www.', '')
            for e in self.extract_mailto_links(html):
                if domain in e.lower():
                    return e
            for e in self.extract_emails_from_text(html):
                if domain in e.lower():
                    return e
            emails = self.extract_emails_from_text(html)
            if emails:
                return emails[0]
        except Exception:
            pass
        return None

    def find_user_data(
        self,
        username: str,
        existing_email: str = '',
        existing_website: str = '',
        existing_linkedin: str = '',
    ) -> Dict:
        """Returns dict with keys: email, linkedin, portfolio (all optional)."""
        result = {
            'email': existing_email.strip() or None,
            'linkedin': existing_linkedin.strip() or None,
            'portfolio': existing_website.strip() or None,
        }
        github_data = self.get_github_profile_data(username)
        if github_data:
            if not result['email'] and github_data.get('email'):
                result['email'] = github_data['email']
            if not result['linkedin'] and github_data.get('linkedin'):
                result['linkedin'] = github_data['linkedin']
            if not result['portfolio'] and github_data.get('portfolio'):
                result['portfolio'] = github_data['portfolio']

        if not result['email']:
            ev_email = self.get_github_events_email(username)
            if ev_email:
                result['email'] = ev_email

        if not result['email']:
            search_email = self.get_github_search_commits_email(username)
            if search_email:
                result['email'] = search_email

        if not result['email'] and result['portfolio']:
            port_email = self.get_portfolio_email(result['portfolio'])
            if port_email:
                result['email'] = port_email

        return result


def populate_contacts_for_usernames(
    usernames: List[str],
    github_token: Optional[str] = None,
    use_selenium: bool = False,
    only_if_missing_email: bool = False,
) -> Dict:
    """
    For each GitHub username, run EmailPopulator to find email/LinkedIn/portfolio and update MongoDB.
    When only_if_missing_email=True, experts who already have email are skipped.
    When only_if_missing_email=False (default), every profile is processed and found links are stored.

    Returns: { "updated": int, "skipped": int, "errors": int, "details": [...] }
    """
    from services.mongodb_service import get_expert, update_expert_contact

    if not REQUESTS_AVAILABLE:
        return {"updated": 0, "skipped": 0, "errors": len(usernames), "details": ["requests not installed"]}

    populator = EmailPopulator(github_token=github_token, use_selenium=use_selenium)
    updated = 0
    skipped = 0
    errors = 0
    details = []

    for username in usernames:
        if not username or not username.strip():
            continue
        username = username.strip()
        try:
            expert = get_expert(username)
            if not expert:
                details.append(f"{username}: not in MongoDB, skip")
                skipped += 1
                continue

            existing_email = (expert.get('email') or '').strip()
            existing_linkedin = (expert.get('linkedin_url') or '').strip()
            existing_portfolio = (expert.get('portfolio_url') or '').strip()

            if only_if_missing_email and existing_email:
                details.append(f"{username}: already has email, skip")
                skipped += 1
                continue

            user_data = populator.find_user_data(
                username,
                existing_email=existing_email,
                existing_website=existing_portfolio,
                existing_linkedin=existing_linkedin,
            )

            new_email = (user_data.get('email') or '').strip() or None
            new_linkedin = (user_data.get('linkedin') or '').strip() or None
            new_portfolio = (user_data.get('portfolio') or '').strip() or None

            if new_email or new_linkedin or new_portfolio:
                update_expert_contact(
                    username,
                    email=new_email,
                    linkedin_url=new_linkedin,
                    portfolio_url=new_portfolio,
                )
                updated += 1
                details.append(f"{username}: updated email={bool(new_email)} linkedin={bool(new_linkedin)} portfolio={bool(new_portfolio)}")
            else:
                details.append(f"{username}: nothing found")
                skipped += 1

            time.sleep(0.5)
        except Exception as e:
            errors += 1
            details.append(f"{username}: error {e}")

    return {"updated": updated, "skipped": skipped, "errors": errors, "details": details}
