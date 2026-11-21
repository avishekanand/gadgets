import pytest

from dashboard.news import fetch_news, merge, parse_feed

RSS = b"""<?xml version="1.0"?><rss version="2.0"><channel>
<item><title>Older  story</title><link>https://a.example/1</link><pubDate>Sat, 21 Nov 2026 10:00:00 +0000</pubDate></item>
<item><title>Newer story</title><link>https://a.example/2</link><pubDate>Sat, 21 Nov 2026 12:00:00 +0000</pubDate></item>
<item><title></title><link>https://a.example/3</link></item>
</channel></rss>"""

ATOM = b"""<?xml version="1.0"?><feed xmlns="http://www.w3.org/2005/Atom">
<entry><title>Atom <b>one</b></title><link rel="alternate" href="https://b.example/1"/><published>2026-11-21T11:00:00Z</published></entry>
<entry><title>Newer story</title><link href="javascript:alert(1)"/><updated>2026-11-21T09:00:00-05:00</updated></entry>
</feed>"""


def test_parse_rss_and_atom():
    rss = parse_feed(RSS, "A")
    assert [i["title"] for i in rss] == ["Older story", "Newer story"]  # empty title dropped
    atom = parse_feed(ATOM, "B")
    assert atom[0]["title"] == "Atom one" and atom[0]["url"] == "https://b.example/1"


def test_merge_sorts_dedupes_limits_and_drops_unsafe_links():
    out = merge({"Tech": parse_feed(RSS, "A") + parse_feed(ATOM, "B")}, per_section=3)
    items = out["sections"][0]["items"]
    # 14:00Z (B, 09:00-05:00) is newest, then 12:00Z, 11:00Z; duplicate "Newer story" from A dropped
    assert [i["title"] for i in items] == ["Newer story", "Atom one", "Older story"]
    assert items[0]["source"] == "B" and items[0]["url"] == ""  # javascript: link removed


def test_fetch_news_skips_broken_feed_but_fails_if_all_broken():
    feeds = [{"section": "Tech", "name": "A", "url": "a"}, {"section": "AI", "name": "bad", "url": "bad"}]

    def fetch(url):
        if url == "bad":
            raise OSError("down")
        return RSS

    out = fetch_news(feeds, 5, fetch=fetch)
    assert [s["name"] for s in out["sections"]] == ["Tech"]
    with pytest.raises(RuntimeError):
        fetch_news([feeds[1]], 5, fetch=fetch)


def test_parse_rss1_rdf():
    rdf = b"""<?xml version="1.0"?><rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
      xmlns="http://purl.org/rss/1.0/" xmlns:dc="http://purl.org/dc/elements/1.1/">
      <item><title>Quantum thing</title><link>https://n.example/1</link><dc:date>2026-11-20</dc:date></item>
    </rdf:RDF>"""
    out = parse_feed(rdf, "Nature")
    assert out[0]["title"] == "Quantum thing" and out[0]["when"].year == 2026


def test_summaries_strip_html_and_truncate():
    from dashboard.news import SUMMARY_CHARS, summarize
    assert summarize("&lt;p&gt;Hello &amp;amp; <b>world</b>&lt;/p&gt;") == "Hello & world"
    assert summarize("arXiv:2611.01234v1 Announce Type: new Abstract: We study ranking.") == "We study ranking."
    assert summarize("Great story. The post Great story appeared first on Site.") == "Great story."
    long = summarize("word " * 200)
    assert long.endswith("…") and len(long) <= SUMMARY_CHARS + 1


def test_feed_items_carry_summary():
    rss = b"""<rss><channel><item><title>T</title><link>https://x/1</link>
      <description>&lt;p&gt;Short &lt;i&gt;summary&lt;/i&gt;&lt;/p&gt;</description></item></channel></rss>"""
    assert parse_feed(rss, "S")[0]["summary"] == "Short summary"
    atom = b"""<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>A</title>
      <summary>An  abstract
      over lines.</summary></entry></feed>"""
    assert parse_feed(atom, "S")[0]["summary"] == "An abstract over lines."


def test_per_section_counts():
    many = [{"title": f"t{i}", "url": "", "source": "A", "when": None, "summary": ""} for i in range(10)]
    out = merge({"US": many, "Tech": list(many)}, per_section=6, counts={"US": 4})
    assert [len(s["items"]) for s in out["sections"]] == [4, 6]


def test_fetch_headlines_fetches_only_that_section_and_returns_top_n():
    from dashboard.news import fetch_headlines

    feeds = [
        {"section": "US", "name": "A", "url": "a"},
        {"section": "US", "name": "B", "url": "b"},
        {"section": "Tech", "name": "C", "url": "c"},  # must NOT be fetched
    ]
    fetched: list[str] = []

    def fetch(url):
        fetched.append(url)
        return RSS

    items = fetch_headlines(feeds, section="US", count=2, fetch=fetch)
    assert sorted(fetched) == ["a", "b"]  # only US feeds hit
    assert len(items) == 2
    assert items[0]["title"] == "Newer story"  # newest first
    assert all("source" in i and "title" in i for i in items)


def test_fetch_headlines_disabled_when_count_zero():
    from dashboard.news import fetch_headlines

    called = []
    fetch_headlines([{"section": "US", "name": "A", "url": "a"}], "US", 0,
                    fetch=lambda u: called.append(u) or RSS)
    assert called == []  # no network when count is 0


def test_default_config_feeds_cover_the_chosen_section():
    from dashboard.config import Config

    c = Config(lat=52.0, lon=4.3)
    assert any(f["section"] == c.news_section for f in c.news)
    assert c.news_count >= 1
