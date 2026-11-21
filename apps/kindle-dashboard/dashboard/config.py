"""Load the dashboard's TOML config into a typed Config object."""
from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path

import tomli


@dataclass
class Config:
    lat: float
    lon: float
    units: str = "C"
    tz: str = "Europe/Amsterdam"
    refresh_min: int = 20
    server_host: str = "0.0.0.0"
    server_port: int = 8713
    out_dir: str = "./out"
    agenda_rows: int = 8
    orientation: str = "portrait"  # "portrait" or "landscape"
    flip: bool = False  # rotate the landscape image 180° (if it comes out upside down)
    calendars: list[str] = field(default_factory=list)  # iCal URLs (fallback source)
    atlas_url: str | None = None  # if set, use the Atlas API instead of iCal URLs
    atlas_mine: bool = True  # Atlas: only the user's own events

    # News headlines (same feeds as the bedside console). The fridge shows one
    # section as a compact HEADLINES block; news_section picks which, news_count
    # how many stories. Set news_count = 0 (or news = []) to hide the block.
    news_section: str = "US"
    news_count: int = 3
    news: list[dict] = field(default_factory=lambda: [
        {"section": "US", "name": "NPR", "url": "https://feeds.npr.org/1001/rss.xml"},
        {"section": "US", "name": "NYT", "url": "https://rss.nytimes.com/services/xml/rss/nyt/US.xml"},
        {"section": "India", "name": "The Hindu", "url": "https://www.thehindu.com/news/national/feeder/default.rss"},
        {"section": "India", "name": "NDTV", "url": "https://feeds.feedburner.com/ndtvnews-top-stories"},
        {"section": "Science", "name": "Quanta", "url": "https://www.quantamagazine.org/feed/"},
        {"section": "Science", "name": "Nature", "url": "https://www.nature.com/nature.rss"},
        {"section": "Science", "name": "Phys.org", "url": "https://phys.org/rss-feed/breaking/"},
        {"section": "arXiv · IR", "name": "arXiv cs.IR",
         "url": "https://export.arxiv.org/api/query?search_query=cat:cs.IR&sortBy=submittedDate&sortOrder=descending&max_results=15"},
        {"section": "AI", "name": "MIT Tech Review", "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed"},
        {"section": "AI", "name": "TechCrunch", "url": "https://techcrunch.com/category/artificial-intelligence/feed/"},
        {"section": "Tech", "name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index"},
        {"section": "Tech", "name": "The Verge", "url": "https://www.theverge.com/rss/index.xml"},
    ])


def load_config(path: str | None = None) -> Config:
    """Read a TOML config file into a Config. Unknown keys are ignored."""
    if path is None:
        path = str(Path(__file__).resolve().parents[1] / "config.toml")
    data = tomli.loads(Path(path).read_text(encoding="utf-8"))
    known = {f.name for f in fields(Config)}
    return Config(**{k: v for k, v in data.items() if k in known})
