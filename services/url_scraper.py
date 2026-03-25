import requests
from bs4 import BeautifulSoup
from typing import Optional, List, Callable
from urllib.parse import urljoin, urlparse
import re
import concurrent.futures


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# Paths that are unlikely to contain useful business content
SKIP_PATTERNS = re.compile(
    r"(login|signup|sign-up|register|cart|checkout|account|password|reset|"
    r"terms|privacy|cookie|legal|careers|jobs|blog/\d|/tag/|/category/|"
    r"\.pdf$|\.png$|\.jpg$|\.svg$|\.css$|\.js$|#)",
    re.IGNORECASE,
)

# Paths likely to contain valuable business info
PRIORITY_PATTERNS = re.compile(
    r"(about|company|product|solution|service|platform|feature|"
    r"pricing|enterprise|technology|security|compliance|case-stud|"
    r"integration|partner|customer|resource|overview|how-it-work|"
    r"why-|our-|what-we)",
    re.IGNORECASE,
)

MAX_PAGES = 10
MAX_CONTENT_PER_PAGE = 6000
MAX_TOTAL_CONTENT = 25000


def _extract_page_content(soup: BeautifulSoup, url: str) -> dict:
    """Extract structured content from a parsed page."""
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "iframe"]):
        tag.decompose()

    title = soup.title.get_text(strip=True) if soup.title else ""
    meta_desc = ""
    meta_tag = soup.find("meta", attrs={"name": "description"})
    if meta_tag:
        meta_desc = meta_tag.get("content", "")
    og_tag = soup.find("meta", attrs={"property": "og:description"})
    if og_tag and not meta_desc:
        meta_desc = og_tag.get("content", "")

    main_content = ""
    for selector in ["main", "article", '[role="main"]', ".content", "#content", ".main"]:
        element = soup.select_one(selector)
        if element:
            main_content = element.get_text(separator=" ", strip=True)
            break
    if not main_content:
        body = soup.find("body")
        if body:
            main_content = body.get_text(separator=" ", strip=True)

    headings = []
    for h in soup.find_all(["h1", "h2", "h3"]):
        text = h.get_text(strip=True)
        if text and len(text) > 3:
            headings.append(text)

    main_content = re.sub(r"\s+", " ", main_content).strip()

    return {
        "url": url,
        "title": title,
        "meta_desc": meta_desc,
        "headings": headings[:15],
        "content": main_content[:MAX_CONTENT_PER_PAGE],
    }


def _discover_internal_links(soup: BeautifulSoup, base_url: str) -> List[str]:
    """Find same-domain links from the page, prioritizing valuable ones."""
    parsed_base = urlparse(base_url)
    base_domain = parsed_base.netloc.lower().replace("www.", "")
    seen = set()
    priority = []
    normal = []

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue

        full_url = urljoin(base_url, href)
        parsed = urlparse(full_url)
        link_domain = parsed.netloc.lower().replace("www.", "")

        if link_domain != base_domain:
            continue

        clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
        if clean_url in seen:
            continue
        seen.add(clean_url)

        if SKIP_PATTERNS.search(parsed.path):
            continue

        if PRIORITY_PATTERNS.search(parsed.path):
            priority.append(clean_url)
        else:
            normal.append(clean_url)

    return priority + normal


def _fetch_page(url: str) -> Optional[BeautifulSoup]:
    """Fetch and parse a single page. Returns None on failure."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=10, allow_redirects=True)
        resp.raise_for_status()
        if "text/html" not in resp.headers.get("content-type", ""):
            return None
        return BeautifulSoup(resp.text, "lxml")
    except Exception:
        return None


def crawl_website(
    url: str,
    max_pages: int = MAX_PAGES,
    on_page_callback: Optional[Callable[[str, int, int], None]] = None,
) -> str:
    """
    Crawl a website starting from `url`, following internal links up to `max_pages`.
    Calls on_page_callback(page_url, current_count, total_discovered) for progress.
    Returns combined content string for LLM analysis.
    """
    # Scrape the seed page first
    soup = _fetch_page(url)
    if soup is None:
        raise ValueError(f"Failed to fetch URL: {url}")

    seed_content = _extract_page_content(soup, url)
    internal_links = _discover_internal_links(soup, url)

    if on_page_callback:
        on_page_callback(url, 1, min(len(internal_links) + 1, max_pages))

    pages = [seed_content]
    crawled_urls = {url.rstrip("/")}
    total_chars = len(seed_content["content"])

    # Crawl additional pages concurrently
    links_to_crawl = [
        link for link in internal_links
        if link.rstrip("/") not in crawled_urls
    ][: max_pages - 1]

    def _crawl_one(link: str):
        page_soup = _fetch_page(link)
        if page_soup is None:
            return None
        return _extract_page_content(page_soup, link)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        future_map = {executor.submit(_crawl_one, link): link for link in links_to_crawl}
        for future in concurrent.futures.as_completed(future_map):
            link = future_map[future]
            try:
                result = future.result()
            except Exception:
                result = None

            if result and result["content"] and len(result["content"]) > 100:
                if total_chars + len(result["content"]) > MAX_TOTAL_CONTENT:
                    continue
                pages.append(result)
                total_chars += len(result["content"])
                crawled_urls.add(link.rstrip("/"))

                if on_page_callback:
                    on_page_callback(link, len(pages), min(len(links_to_crawl) + 1, max_pages))

    # Combine all pages into a structured document for the LLM
    sections = []
    for i, page in enumerate(pages):
        path = urlparse(page["url"]).path or "/"
        section = f"--- PAGE {i + 1}: {page['title'] or path} ({page['url']}) ---"
        if page["meta_desc"]:
            section += f"\nMETA: {page['meta_desc']}"
        if page["headings"]:
            section += f"\nHEADINGS: {' | '.join(page['headings'][:10])}"
        section += f"\nCONTENT:\n{page['content']}"
        sections.append(section)

    combined = "\n\n".join(sections)
    return combined


def scrape_url(url: str) -> str:
    """Scrape text content from a single URL (legacy, used as fallback)."""
    soup = _fetch_page(url)
    if soup is None:
        raise ValueError(f"Failed to fetch URL: {url}")
    page = _extract_page_content(soup, url)

    nav_texts = []
    soup2 = _fetch_page(url)
    if soup2:
        for a in soup2.find_all("a", href=True):
            text = a.get_text(strip=True)
            if text and 3 < len(text) < 50:
                nav_texts.append(text)

    combined = f"""
TITLE: {page['title']}

META DESCRIPTION: {page['meta_desc']}

PAGE HEADINGS:
{chr(10).join(page['headings'][:20])}

NAVIGATION/MENU ITEMS:
{', '.join(list(set(nav_texts))[:30])}

MAIN CONTENT:
{page['content'][:8000]}
""".strip()

    return combined


def is_valid_url(url: str) -> bool:
    """Basic URL validation."""
    pattern = re.compile(
        r"^https?://"
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
        r"localhost|"
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
        r"(?::\d+)?"
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )
    return bool(pattern.match(url))
