from html.parser import HTMLParser
import xml.etree.ElementTree as ET
from html import unescape
import re

from email.utils import parsedate_to_datetime
from datetime import timezone, datetime


class DiscordHTMLToMarkdown(HTMLParser):
    def __init__(self):
        super().__init__()
        self.out = []
        self.stack = []
        self.in_li = False
        self.href = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ("b", "strong"):
            self.out.append("**"); self.stack.append("**")
        elif tag in ("i", "em"):
            self.out.append("*"); self.stack.append("*")
        elif tag == "code":
            self.out.append("`"); self.stack.append("`")
        elif tag in ("p", "div"):
            if self.out and not self.out[-1].endswith("\n\n"):
                self.out.append("\n\n")
            self.stack.append(None)
        elif tag in ("br",):
            self.out.append("\n")
        elif tag in ("ul", "ol"):
            self.stack.append(tag)
        elif tag == "li":
            self.in_li = True
            self.out.append("- ")
            self.stack.append("li")
        elif tag == "a":
            self.href = attrs.get("href")
            self.stack.append("a")
        else:
            self.stack.append(None)

    def handle_endtag(self, tag):
        if tag in ("b", "strong", "i", "em", "code"):
            while self.stack:
                m = self.stack.pop()
                if m in ("**", "*", "`"):
                    self.out.append(m)
                    break
        elif tag == "a":
            if self.href:
                if self.out and re.match(r"(?:^|\n)-\s*$", "".join(self.out[-1:])):
                    self.out.append(self.href)
            self.href = None
            self._pop_to("a")
        elif tag == "li":
            if not self.out or not self.out[-1].endswith("\n"):
                self.out.append("\n")
            self.in_li = False
            self._pop_to("li")
        elif tag in ("ul", "ol"):
            if not self.out or not self.out[-1].endswith("\n\n"):
                self.out.append("\n")
            self._pop_to(tag)
        elif tag in ("p", "div"):
            if not self.out or not self.out[-1].endswith("\n\n"):
                self.out.append("\n\n")
            self._pop_to(None)

    def handle_data(self, data):
        text = unescape(data)
        if self.href:
            text = text.strip()
            if text:
                self.out.append(f"[{text}]({self.href})")
            else:
                self.out.append(self.href)
        else:
            if self.in_li:
                self.out.append(re.sub(r"\s+", " ", text).strip())
            else:
                self.out.append(re.sub(r"[ \t]+", " ", text))

    def _pop_to(self, marker):
        while self.stack:
            m = self.stack.pop()
            if m == marker:
                break

    def get_markdown(self):
        s = "".join(self.out)

        s = re.sub(r"[ \t]+\n", "\n", s)
        s = re.sub(r"\n{3,}", "\n\n", s)
        s = s.strip()
        return s

def html_to_discord_markdown(html: str, title: str | None = None, date_str: str | None = None) -> str:
    parser = DiscordHTMLToMarkdown()
    parser.feed(html)
    body = parser.get_markdown()

    header = ""
    if title and date_str:
        header = f"**[RSS Feed] {title}** ({date_str})\n"
    elif title:
        header = f"**[RSS Feed] {title}** \n"

    return header + body


def parse_rss_items(text: str):
    root = ET.fromstring(text)  # raises if XML is invalid
    items = []
    for it in root.findall(".//item"):
        items.append({
            "title": it.findtext("title", default=""),
            "link": it.findtext("link", default=""),
            "guid": it.findtext("guid", default=""),
            "pubDate": it.findtext("pubDate", default=""),
            "description": it.findtext("description", default=""),
        })
    return items[::-1]


def release_to_unix(s: str) -> datetime:
    """
    Parse strings like:
    'Release date: Sat, 06 Sep 2025 23:00:00 +0100'
    Returns a timezone-aware datetime.
    """
    prefix = "Release date:"
    if s.startswith(prefix):
        s = s[len(prefix):].strip()
    # RFC-822 style with offset like +0100 (no colon)
    return round(datetime.strptime(s, "%a, %d %b %Y %H:%M:%S %z").timestamp())
