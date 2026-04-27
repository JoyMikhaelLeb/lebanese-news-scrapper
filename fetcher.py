"""
Media Monitoring Tool - Link Fetcher
Reads links from Google Sheet, extracts content, saves to text file
"""

import requests
from newspaper import Article
from urllib.parse import urlparse
import re
import time

# Disable SSL warnings for some sites
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def expand_short_url(url):
    """Expand shortened URLs like bit.ly"""
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        return response.url
    except:
        return url


def detect_link_type(url):
    """Detect what type of link this is"""
    domain = urlparse(url).netloc.lower()
    
    if 'x.com' in domain or 'twitter.com' in domain:
        return 'twitter'
    elif 'instagram.com' in domain:
        return 'instagram'
    elif 'facebook.com' in domain:
        return 'facebook'
    elif 'bit.ly' in domain or 'tinyurl.com' in domain or 't.co' in domain:
        return 'shortened'
    else:
        return 'news'


def fetch_news_article(url):
    """Fetch and extract text from news article using newspaper3k"""
    try:
        article = Article(url, language='ar')
        article.download()
        article.parse()
        
        title = article.title or ""
        text = article.text or ""
        
        if len(text.strip()) < 50:
            # Fallback: try with requests + basic extraction
            return fetch_with_requests(url)
        
        return {
            'status': 'done',
            'title': title,
            'text': text
        }
    except Exception as e:
        # Try fallback method
        return fetch_with_requests(url)


def fetch_with_requests(url):
    """Fallback method using requests + BeautifulSoup"""
    try:
        from bs4 import BeautifulSoup
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script, style, nav, footer, aside elements
        for tag in soup(['script', 'style', 'nav', 'footer', 'aside', 'header', 'advertisement']):
            tag.decompose()
        
        # Try to find article content
        article = soup.find('article') or soup.find('div', class_=re.compile(r'article|content|post|entry'))
        
        if article:
            text = article.get_text(separator='\n', strip=True)
        else:
            # Get body text as last resort
            body = soup.find('body')
            text = body.get_text(separator='\n', strip=True) if body else ""
        
        # Get title
        title = ""
        title_tag = soup.find('h1') or soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
        
        # Clean up text - remove excessive whitespace
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        text = '\n'.join(lines)
        
        if len(text) < 50:
            return {
                'status': 'error',
                'title': title,
                'text': 'Could not extract content'
            }
        
        return {
            'status': 'done',
            'title': title,
            'text': text
        }
        
    except Exception as e:
        return {
            'status': 'error',
            'title': '',
            'text': f'Error: {str(e)}'
        }


def fetch_twitter(url):
    """
    Twitter/X requires JavaScript - mark for nodriver processing
    For now, return needs_browser status
    """
    return {
        'status': "didn't open",
        'title': '',
        'text': 'Twitter/X requires browser - will process separately'
    }


def fetch_instagram(url):
    """Instagram usually requires login for full content"""
    return {
        'status': "didn't open",
        'title': '',
        'text': 'Instagram requires login'
    }


def fetch_facebook(url):
    """Facebook usually requires login"""
    return {
        'status': "didn't open",
        'title': '',
        'text': 'Facebook requires login'
    }


def process_link(url):
    """Main function to process a single link"""
    url = url.strip()
    
    if not url:
        return None
    
    # Detect type
    link_type = detect_link_type(url)
    
    # Expand if shortened
    if link_type == 'shortened':
        url = expand_short_url(url)
        link_type = detect_link_type(url)
    
    # Fetch based on type
    if link_type == 'twitter':
        result = fetch_twitter(url)
    elif link_type == 'instagram':
        result = fetch_instagram(url)
    elif link_type == 'facebook':
        result = fetch_facebook(url)
    else:
        result = fetch_news_article(url)
    
    result['url'] = url
    result['type'] = link_type
    
    return result


def read_links_from_csv(filepath):
    """Read links from a CSV file (exported from Google Sheet)"""
    links = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            link = line.strip()
            if link and link.startswith('http'):
                links.append(link)
    return links


def save_results(results, output_file='output.txt'):
    """Save all results to a text file"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("=" * 60 + "\n")
        f.write("MEDIA MONITORING REPORT\n")
        f.write(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write("=" * 60 + "\n\n")
        
        for i, result in enumerate(results, 1):
            f.write("=" * 60 + "\n")
            f.write(f"SOURCE {i}: {result['url']}\n")
            f.write(f"TYPE: {result['type']}\n")
            f.write(f"STATUS: {result['status']}\n")
            f.write("-" * 60 + "\n")
            
            if result['title']:
                f.write(f"TITLE: {result['title']}\n\n")
            
            f.write(result['text'] + "\n\n")
    
    print(f"Results saved to {output_file}")


def generate_status_csv(results, links, output_file='status.csv'):
    """Generate a CSV with link and status for updating Google Sheet"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write("Link,Status\n")
        for link, result in zip(links, results):
            status = result['status'] if result else 'error'
            f.write(f'"{link}","{status}"\n')
    
    print(f"Status CSV saved to {output_file}")


def main(input_file='links.csv', output_file='output.txt'):
    """Main entry point"""
    print("Reading links...")
    links = read_links_from_csv(input_file)
    print(f"Found {len(links)} links")
    
    results = []
    for i, link in enumerate(links, 1):
        print(f"Processing {i}/{len(links)}: {link[:50]}...")
        result = process_link(link)
        if result:
            results.append(result)
        time.sleep(1)  # Be nice to servers
    
    print("\nSaving results...")
    save_results(results, output_file)
    generate_status_csv(results, links)
    
    # Print summary
    done = sum(1 for r in results if r['status'] == 'done')
    didnt_open = sum(1 for r in results if r['status'] == "didn't open")
    errors = sum(1 for r in results if r['status'] == 'error')
    
    print(f"\n--- SUMMARY ---")
    print(f"Done: {done}")
    print(f"Didn't open: {didnt_open}")
    print(f"Errors: {errors}")


if __name__ == "__main__":
    main()
