from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from xml.etree import ElementTree

try:
    from . import config
    from .utils import logger
except ImportError:
    import config
    from utils import logger


PUBLIC_DIR = Path(__file__).parent.parent / "frontend" / "public"
SITEMAP_FILE = PUBLIC_DIR / "sitemap.xml"
WELL_KNOWN_DIR = PUBLIC_DIR / ".well-known"
SECURITY_TXT_FILE = WELL_KNOWN_DIR / "security.txt"


def generate_security_txt() -> None:
    """
    Generates a .well-known/security.txt file
    """
    try:
        if not SECURITY_TXT_FILE.parent.exists():
            SECURITY_TXT_FILE.parent.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logger.error(f"Failed to create .well-known directory: {e}")

    now = datetime.now(timezone.utc)
    expiration_date = now.replace(
        year=now.year + 1,
        month=1,
        day=1,
        hour=0,
        minute=0,
        second=0
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    content = f"# security.txt for {config.BASE_URL}\n"
    content += f"# Generated on {now.strftime('%Y-%m-%dT%H:%M:%SZ')}\n\n"
    content += f"Contact: {config.CONTACT_INFO}\n"
    content += "Contact: https://github.com/jackgdn/world-news-map\n"
    content += f"Expires: {expiration_date}\n"  # Expires in next year
    content += "Preferred-Languages: zh-CN, en"

    try:
        with SECURITY_TXT_FILE.open("w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        logger.error(f"Failed to write security.txt: {e}")


def generate_sitemap() -> None:
    """
    Generates a sitemap.xml file
    """
    try:
        urls = list()

        # Add public/index.html
        index_file = PUBLIC_DIR / "index.html"
        modtime = datetime.fromtimestamp(
            index_file.stat().st_mtime, tz=timezone.utc)
        urls.append(("/", modtime))

        # Add public/news/*.json
        news_dir = PUBLIC_DIR / "news"
        if news_dir.exists():
            for json_file in news_dir.glob("*.json"):
                modtime = datetime.fromtimestamp(
                    json_file.stat().st_mtime, tz=timezone.utc)
                urls.append((f"/news/{json_file.name}", modtime))

        urlset = ElementTree.Element(
            "urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

        for path, modtime in urls:
            url = ElementTree.SubElement(urlset, "url")
            loc = ElementTree.SubElement(url, "loc")
            loc.text = config.BASE_URL + quote(path)
            lastmod = ElementTree.SubElement(url, "lastmod")
            lastmod.text = modtime.strftime("%Y-%m-%dT%H:%M:%SZ")

        tree = ElementTree.ElementTree(urlset)
        tree.write(SITEMAP_FILE, encoding="utf-8", xml_declaration=True)

        logger.info(
            f"Generated sitemap with {len(urls)} URLs at {SITEMAP_FILE}")

    except Exception as e:
        logger.error(f"Failed to generate sitemap: {e}")


def generate_robots_txt() -> None:
    """
    Generates a robots.txt file
    """
    robots_file = PUBLIC_DIR / "robots.txt"
    content = "User-agent: *\n"
    content += "Allow: /"
    try:
        with robots_file.open("w") as f:
            f.write(content)
        logger.info(f"Generated robots.txt at {robots_file}")
    except Exception as e:
        logger.error(f"Failed to write robots.txt: {e}")


def generate_metadata() -> None:
    """
    Generates both sitemap.xml and .well-known/security.txt
    """
    generate_security_txt()
    generate_sitemap()
    generate_robots_txt()


if __name__ == "__main__":
    generate_metadata()
