import re
from html.parser import HTMLParser
from urllib.request import Request, urlopen


DATA_EXTENSIONS = (
    ".csv",
    ".json",
    ".xlsx",
    ".xls",
    ".xml",
    ".zip",
    ".txt",
    ".parquet",
    ".tsv",
    ".geojson",
)


def coerce_numeric(value):
    """Convert a French-formatted number like '1 234,5' into a float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None

    lower = text.lower()
    if lower in {"na", "n/a", "null", "none", "nan"}:
        return None

    cleaned = re.sub(r"[^0-9,\.\-+]", "", text)
    if not cleaned or cleaned in {"-", "+", ".", ","}:
        return None

    if "," in cleaned and "." in cleaned:
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")
        else:
            cleaned = cleaned.replace(",", "")
    elif "," in cleaned:
        if cleaned.count(",") > 1:
            cleaned = cleaned.replace(",", "")
        else:
            cleaned = cleaned.replace(",", ".")

    return float(cleaned)


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        for attr_name, attr_value in attrs:
            if attr_name.lower() == "href" and attr_value:
                self.links.append(attr_value.strip())


def extract_data_links(html):
    """Extract likely data file links from a page while preserving ordering."""
    if not html:
        return []

    parser = _LinkParser()
    parser.feed(html)

    candidates = []
    for href in parser.links:
        candidate = href.strip()
        if not candidate or candidate.startswith("#"):
            continue
        if candidate.lower().startswith(("javascript:", "mailto:")):
            continue

        normalized = candidate.lower()
        if not any(
            normalized.endswith(ext) or ext in normalized
            for ext in DATA_EXTENSIONS
        ) and "download" not in normalized and "csv" not in normalized and "json" not in normalized:
            continue

        candidates.append(candidate)

    return candidates


def fetch_html(url):
    """Simple HTTP fetch helper for dashboard-style use cases."""
    request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=20) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")
