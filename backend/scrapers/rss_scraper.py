import feedparser
from newspaper import Article
from datetime import datetime
from typing import List, Dict, Optional
from backend.nlp.language import detect_language
from backend.nlp.translator import translate_to_english
from backend.nlp.summarizer import summarize
from backend.nlp.sentiment import classify_sentiment
from backend.nlp.entities import extract_entities
from backend.nlp.bias import classify_bias
from backend.models.article_model import ArticleDoc, EntitySentiment
from backend.elasticsearch.es_client import get_es
from backend.config import ES_INDEX
import trafilatura
import logging
import re

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None
    logging.warning("BeautifulSoup not available, title extraction may be limited")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

RSS_FEEDS = [
    "https://feeds.feedburner.com/ndtvnews-top-stories",
]

def truncate_text(text: str, max_tokens: int = 800) -> str:
    """Truncate text to avoid sequence length errors."""
    if not text:
        return text
    
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    
    truncated = text[:max_chars]
    last_period = truncated.rfind('.')
    if last_period > max_chars * 0.8:
        return truncated[:last_period + 1]
    
    return truncated

def clean_title(title: str) -> str:
    """Clean and validate a title."""
    if not title:
        return ""
    
    title = ' '.join(title.split())
    title = title.replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
    
    unwanted_patterns = [
        r'\s*-\s*[^-]*$',
        r'^\s*[|\-]\s*',
        r'\s*[|\-]\s*$',
    ]
    
    for pattern in unwanted_patterns:
        title = re.sub(pattern, '', title, flags=re.IGNORECASE)
    
    if len(title) > 200:
        title = title[:200].rsplit(' ', 1)[0] + "..."
    
    return title.strip()

def is_valid_title(title: str) -> bool:
    """Check if a title is valid and meaningful."""
    if not title or len(title.strip()) < 10:
        return False
    
    title_lower = title.lower().strip()
    
    invalid_titles = [
        'untitled', 'no title', 'article', 'news', 'page not found',
        'error', '404', 'access denied', 'forbidden', 'loading'
    ]
    
    for invalid in invalid_titles:
        if invalid in title_lower:
            return False
    
    if not re.search(r'[a-zA-Z]{3,}', title):
        return False
    
    return True

def extract_title_from_url(url: str) -> str:
    """Extract a reasonable title from URL as fallback."""
    try:
        clean_url = url.replace('https://', '').replace('http://', '').replace('www.', '')
        parts = clean_url.split('/')
        
        if len(parts) < 2:
            domain = clean_url.split('?')[0]
            return f"Article from {domain.replace('.com', '').replace('.org', '').replace('.net', '').title()}"
        
        meaningful_parts = []
        for part in parts[1:]:
            if not part or len(part) < 4:
                continue
                
            if any(skip in part.lower() for skip in ['index', 'page', 'www', 'news', 'article', 'default']):
                continue
                
            if part.isdigit() or len(part) < 4:
                continue
            
            cleaned = part.replace('-', ' ').replace('_', ' ')
            cleaned = re.sub(r'\.[a-z]+$', '', cleaned)
            cleaned = re.sub(r'[^\w\s]', ' ', cleaned)
            cleaned = ' '.join(cleaned.split())
            
            if len(cleaned) > 5:
                meaningful_parts.append(cleaned)
        
        if meaningful_parts:
            title_part = max(meaningful_parts, key=len)
            title = ' '.join(word.capitalize() for word in title_part.split())
            return title
        
        domain = clean_url.split('/')[0].split('?')[0]
        domain_name = domain.replace('.com', '').replace('.org', '').replace('.net', '').replace('.in', '')
        return f"Article from {domain_name.title()}"
        
    except Exception as e:
        logger.error(f"Error extracting title from URL {url}: {e}")
        return "News Article"

def fetch_feed_entries(limit_per_feed: int = 20) -> List[Dict]:
    """Fetch entries from RSS feeds."""
    items = []
    for feed_url in RSS_FEEDS:
        try:
            logger.info(f"Fetching feed: {feed_url}")
            feed = feedparser.parse(feed_url)
            
            if feed.bozo:
                logger.warning(f"Feed parsing issues for {feed_url}")
            
            for entry in feed.entries[:limit_per_feed]:
                items.append({
                    "title": entry.get("title", "").strip(),
                    "link": entry.get("link"),
                    "published": entry.get("published", None),
                    "source": feed.feed.get("title") or feed_url,
                    "description": entry.get("description", "")
                })
                
            logger.info(f"Fetched {len(feed.entries[:limit_per_feed])} entries from {feed_url}")
                
        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {str(e)}")
    
    return items

def extract_title_from_html(downloaded_html: str, url: str) -> Optional[str]:
    """Extract title from HTML using BeautifulSoup."""
    if not BeautifulSoup or not downloaded_html:
        return None
    
    try:
        soup = BeautifulSoup(downloaded_html, 'html.parser')
        
        title_selectors = [
            ('meta[property="og:title"]', 'content'),
            ('meta[name="twitter:title"]', 'content'),
            ('meta[property="twitter:title"]', 'content'),
            ('title', 'text'),
            ('h1', 'text'),
            ('.headline', 'text'),
            ('.title', 'text'),
            ('.article-title', 'text'),
            ('.post-title', 'text'),
            ('[class*="headline"]', 'text'),
            ('[class*="title"]', 'text'),
        ]
        
        for selector, attr_type in title_selectors:
            try:
                elements = soup.select(selector)
                
                for element in elements[:3]:
                    if attr_type == 'content':
                        title = element.get('content', '').strip()
                    else:
                        title = element.get_text(strip=True)
                    
                    if title and is_valid_title(title):
                        cleaned_title = clean_title(title)
                        return cleaned_title
                        
            except Exception:
                continue
        
        return None
        
    except Exception as e:
        logger.error(f"HTML title extraction failed for {url}: {e}")
        return None

def extract_title_from_content(text: str) -> Optional[str]:
    """Try to extract a title from the article content itself."""
    if not text or len(text) < 50:
        return None
    
    sentences = re.split(r'[.!?]+', text)
    
    for sentence in sentences[:5]:
        sentence = sentence.strip()
        
        if (15 <= len(sentence) <= 150 and 
            not sentence.lower().startswith(('the article', 'this article', 'according to', 'in a', 'on ', 'at '))):
            
            cleaned = clean_title(sentence)
            if is_valid_title(cleaned):
                return cleaned
    
    return None

def download_article(url: str) -> Optional[Dict]:
    """Download and extract article text using Trafilatura with enhanced title extraction."""
    try:
        downloaded = trafilatura.fetch_url(url)
        
        if downloaded:
            extracted_text = trafilatura.extract(downloaded, include_comments=False, include_tables=False)
            
            if extracted_text and len(extracted_text.strip()) > 100:
                title = None
                
                # Try Trafilatura metadata
                try:
                    metadata = trafilatura.extract_metadata(downloaded)
                    if metadata and hasattr(metadata, 'title') and metadata.title:
                        potential_title = clean_title(metadata.title)
                        if is_valid_title(potential_title):
                            title = potential_title
                except Exception:
                    pass
                
                # Try HTML extraction
                if not title:
                    title = extract_title_from_html(downloaded, url)
                
                # Try content-based extraction
                if not title:
                    title = extract_title_from_content(extracted_text)
                
                return {
                    "title": title,
                    "text": extracted_text,
                    "authors": [],
                    "publish_date": None,
                    "top_image": None,
                    "method": "trafilatura"
                }
                
    except Exception as e:
        logger.warning(f"Trafilatura failed for {url}: {str(e)}")

    # Fallback to Newspaper3k
    try:
        art = Article(url, keep_article_html=False)
        art.download()
        art.parse()
        
        if art.text and len(art.text.strip()) > 100:
            title = None
            if art.title:
                potential_title = clean_title(art.title)
                if is_valid_title(potential_title):
                    title = potential_title
            
            return {
                "title": title,
                "text": art.text,
                "authors": art.authors,
                "publish_date": art.publish_date,
                "top_image": art.top_image,
                "method": "newspaper3k"
            }
            
    except Exception as e:
        logger.warning(f"Newspaper3k also failed for {url}: {str(e)}")

    logger.error(f"All download methods failed for {url}")
    return None

def iso_date(dt) -> Optional[str]:
    """Convert datetime to ISO string."""
    if isinstance(dt, datetime):
        return dt.isoformat()
    return None

def safe_nlp_operation(operation_name: str, operation_func, *args, **kwargs):
    """Safely execute NLP operations with proper error logging."""
    try:
        result = operation_func(*args, **kwargs)
        return result
    except Exception as e:
        logger.error(f"{operation_name} failed: {str(e)}")
        return None

def validate_and_create_entities(entities_data) -> List[EntitySentiment]:
    """Safely create EntitySentiment objects with proper validation."""
    entities = []
    if not entities_data:
        return entities
    
    for e in entities_data:
        try:
            name = e.get("name")
            if name is None or not isinstance(name, str) or not name.strip():
                continue
            
            entity = EntitySentiment(
                name=name.strip(),
                type=e.get("type", "misc"),
                sentiment=e.get("sentiment", "neutral"),
                bias=e.get("bias"),
                score=e.get("score")
            )
            entities.append(entity)
            
        except Exception:
            continue
    
    return entities

def create_article_doc(url: str, feed_title: str, rss_entry: Dict) -> Optional[ArticleDoc]:
    """Create an ArticleDoc with comprehensive title extraction."""
    raw_article = download_article(url)
    if not raw_article or not raw_article.get('text'):
        logger.warning(f"No content extracted for {url}")
        return None

    text = raw_article['text']
    text = truncate_text(text, max_tokens=800)

    # Title extraction with priority order
    final_title = None
    
    # Priority 1: RSS feed title
    rss_title = rss_entry.get('title', '').strip()
    if rss_title and is_valid_title(rss_title):
        final_title = clean_title(rss_title)
    
    # Priority 2: Extracted title from article
    if not final_title:
        extracted_title = raw_article.get('title', '').strip() if raw_article.get('title') else ''
        if extracted_title and is_valid_title(extracted_title):
            final_title = clean_title(extracted_title)
    
    # Priority 3: Content-based title
    if not final_title:
        content_title = extract_title_from_content(text)
        if content_title and is_valid_title(content_title):
            final_title = content_title
    
    # Priority 4: URL-based title
    if not final_title:
        final_title = extract_title_from_url(url)
    
    # Final validation and cleanup
    if not final_title or not is_valid_title(final_title):
        final_title = f"Article from {url.split('//')[1].split('/')[0] if '//' in url else 'Unknown Source'}"

    # NLP operations
    lang = safe_nlp_operation("Language detection", detect_language, text) or "en"
    
    translated_text = None
    if lang != "en":
        translated_result = safe_nlp_operation("Translation", translate_to_english, text)
        if translated_result:
            text = translated_result
            translated_text = translated_result

    summary = safe_nlp_operation("Summarization", summarize, text)
    entities_data = safe_nlp_operation("Entity extraction", extract_entities, text)
    entities = validate_and_create_entities(entities_data)

    # Bias analysis
    bias_result = safe_nlp_operation("Bias classification", classify_bias, text)
    bias_overall, bias_score = ("neutral", 0.0)
    if bias_result and len(bias_result) >= 2:
        bias_overall = bias_result[0] or "neutral"
        bias_score = bias_result[1] or 0.0

    # Sentiment analysis
    sentiment_result = safe_nlp_operation("Sentiment classification", classify_sentiment, text)
    sentiment_overall, sentiment_score = ("neutral", 0.0)
    if sentiment_result and len(sentiment_result) >= 2:
        sentiment_overall = sentiment_result[0] or "neutral"
        sentiment_score = sentiment_result[1] or 0.0

    # Parse published date
    published_date = None
    if raw_article.get('publish_date'):
        published_date = iso_date(raw_article['publish_date'])
    elif rss_entry.get('published'):
        try:
            from dateutil import parser
            parsed_date = parser.parse(rss_entry['published'])
            published_date = iso_date(parsed_date)
        except:
            pass

    article_doc = ArticleDoc(
        title=final_title,
        url=url,
        source_name=feed_title,
        published_date=published_date,
        language=lang,
        original_text=raw_article['text'][:5000],
        translated_text=translated_text,
        summary=summary,
        bias_overall=bias_overall,
        bias_score=bias_score,
        sentiment_overall=sentiment_overall,
        sentiment_score=sentiment_score,
        entities=entities
    )

    return article_doc

def ingest_from_feeds(limit_per_feed: int = 20):
    """Function to ingest articles from RSS feeds and index them in Elasticsearch."""
    es = get_es()
    feed_entries = fetch_feed_entries(limit_per_feed=limit_per_feed)
    
    indexed_count = 0
    errors = []
    
    logger.info(f"Processing {len(feed_entries)} articles...")
    
    for i, entry in enumerate(feed_entries):
        try:
            doc = create_article_doc(entry['link'], entry['source'], entry)
            
            if doc:
                doc_dict = doc.model_dump()
                doc_dict['url'] = str(doc_dict['url'])
                
                result = es.index(index=ES_INDEX, body=doc_dict)
                indexed_count += 1
                logger.info(f"Successfully indexed: '{doc.title}'")
            else:
                logger.warning(f"Failed to create document for {entry.get('link')}")
                
        except Exception as e:
            error_msg = f"Error processing {entry.get('link', 'unknown URL')}: {str(e)}"
            errors.append(error_msg)
            logger.error(error_msg)
    
    logger.info(f"Ingestion complete - Indexed: {indexed_count}/{len(feed_entries)}, Errors: {len(errors)}")
    
    return {
        "indexed": indexed_count,
        "total_fetched": len(feed_entries),
        "errors": errors
    }