"""RSS feed reader adapter for Sentiment Engine (Phase 1b).

Fetches public financial RSS feeds using stdlib urllib and xml.etree.ElementTree.
No new dependencies introduced. Bounded with timeout and max items.
Strict sanitization (§26): no PII, credentials, or positions handled or logged.
"""
from datetime import datetime, timezone
import urllib.request
import xml.etree.ElementTree as ET
from typing import Optional


class RSSNewsAdapter:
    """Standard RSS feed reader for financial headlines."""

    def __init__(self, feed_url: Optional[str] = None, timeout: float = 5.0):
        self.feed_url = feed_url or "https://www.cnbc.com/id/100003114/device/rss/rss.html"
        self.timeout = timeout

    def fetch_headlines(self, max_items: int = 50) -> list[dict]:
        """Fetch and parse RSS feed into standardized headline dicts."""
        if not self.feed_url:
            return []

        try:
            req = urllib.request.Request(
                self.feed_url,
                headers={"User-Agent": "PIMS-SentimentAgent/1.0"},
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                xml_data = response.read()

            root = ET.fromstring(xml_data)
            headlines = []

            # Handle RSS 2.0 (<channel><item>...) and Atom (<feed><entry>...)
            items = root.findall(".//item") or root.findall(".//{http://www.w3.org/2005/Atom}entry")
            
            for item in items[:max_items]:
                title_elem = item.find("title") or item.find("{http://www.w3.org/2005/Atom}title")
                date_elem = item.find("pubDate") or item.find("{http://www.w3.org/2005/Atom}published") or item.find("{http://www.w3.org/2005/Atom}updated")
                
                title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                pub_date = date_elem.text.strip() if date_elem is not None and date_elem.text else datetime.now(timezone.utc).isoformat()

                if title:
                    headlines.append({
                        "title": title,
                        "pub_date": pub_date,
                        "source": "RSS_FEED",
                    })

            return headlines
        except Exception:
            # Network or parse failure -> return empty list (HONEST UNAVAILABLE policy)
            return []
