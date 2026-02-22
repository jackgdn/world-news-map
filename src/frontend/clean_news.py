import datetime
from pathlib import Path


def iter_news_files(news_dir: Path):
    if not news_dir.is_dir():
        return []
    return list(news_dir.glob("*.json"))


def parse_date(stem: str):
    try:
        return datetime.datetime.strptime(stem, "%Y-%m-%d").date()
    except ValueError:
        return None


def clean_news(news_dir: Path, days: int = 15) -> int:
    cutoff = datetime.date.today() - datetime.timedelta(days=days)
    removed = 0
    for path in iter_news_files(news_dir):
        dt = parse_date(path.stem)
        if dt is None:
            continue
        if dt <= cutoff:
            path.unlink(missing_ok=True)
            removed += 1
    return removed


def main():
    base = Path(__file__).parent.parent.parent
    news_dir = base / "public" / "news"
    removed_count = clean_news(news_dir, days=15)
    print(f"Removed {removed_count} files from {news_dir}")


if __name__ == "__main__":
    main()
