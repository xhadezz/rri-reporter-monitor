import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

sys.path.insert(0, os.path.dirname(__file__))
from scanner_core import discover, fetch_article, ARTICLE_WORKERS


def main():
    # Discovery dibuat tahan exception agar satu future yang bermasalah
    # tidak menghentikan seluruh scheduled scan.
    try:
        items, discovery_errors = discover(50)
    except Exception as exc:
        print(f"Discovery gagal total: {type(exc).__name__}: {exc}", file=sys.stderr)
        items, discovery_errors = [], 1

    fetched = []
    errors = discovery_errors

    with ThreadPoolExecutor(
        max_workers=ARTICLE_WORKERS,
        thread_name_prefix="article",
    ) as executor:
        futures = [executor.submit(fetch_article, item) for item in items]

        for future in as_completed(futures):
            try:
                result = future.result()
            except Exception as exc:
                # Jangan biarkan satu artikel menghentikan seluruh scan.
                errors += 1
                print(
                    f"Artikel gagal diproses: {type(exc).__name__}: {exc}",
                    file=sys.stderr,
                )
                continue

            fetched.append(result)
            if result.get("error"):
                errors += 1

    articles = []
    for result in fetched:
        if result.get("error"):
            continue

        sifa = bool(result.get("body_sifa"))
        edwi = bool(result.get("body_edwi") and result.get("author_match"))

        if sifa or edwi:
            articles.append(
                {
                    "url": result["url"],
                    "title": result.get("title", "-"),
                    "category": result.get("category", "-"),
                    "author": result.get("author", "-"),
                    "published": result.get("published", ""),
                    "published_date": result.get("published_date", ""),
                    "sifa": sifa,
                    "edwi": edwi,
                }
            )

    # Data JSON tetap disimpan walaupun ada sebagian artikel yang error.
    # Urutan internal tetap terbaru -> terlama untuk kebutuhan dashboard.
    articles.sort(
        key=lambda item: (
            item.get("published_date", ""),
            item.get("title", ""),
        ),
        reverse=True,
    )

    tz = ZoneInfo("Asia/Jakarta") if ZoneInfo else timezone.utc
    now = datetime.now(timezone.utc).astimezone(tz).strftime(
        "%Y-%m-%d %H:%M:%S WIB"
    )

    data = {
        "meta": {
            "last_scan": now,
            "discovered": len(items),
            "fetched": len(fetched),
            "matched": len(articles),
            "errors": errors,
            "workers": ARTICLE_WORKERS,
        },
        "articles": articles,
    }

    output = os.path.join(os.path.dirname(__file__), "data.json")
    with open(output, "w", encoding="utf-8") as handle:
        json.dump(data, handle, ensure_ascii=False, indent=2)

    print("HASIL SCAN:")
    print(json.dumps(data["meta"], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
