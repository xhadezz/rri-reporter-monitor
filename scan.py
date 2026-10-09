import json
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

sys.path.insert(0, os.path.dirname(__file__))
from scanner_core import discover, fetch_article, ARTICLE_WORKERS

BASE_DIR = os.path.dirname(__file__)
DATA_PATH = os.path.join(BASE_DIR, "data.json")


def read_previous_data():
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        if isinstance(data, dict) and isinstance(data.get("articles"), list):
            return data
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Data sebelumnya tidak bisa dibaca: {exc}", file=sys.stderr)
    return {"meta": {}, "articles": []}


def write_json_atomic(data):
    # Tulis ke file sementara dahulu agar data.json tidak rusak jika proses terputus.
    fd, temp_path = tempfile.mkstemp(prefix="data-", suffix=".json", dir=BASE_DIR)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
        os.replace(temp_path, DATA_PATH)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def is_match(result):
    sifa = bool(result.get("body_sifa"))
    edwi = bool(result.get("body_edwi") and result.get("author_match"))
    return sifa, edwi


def article_record(result, sifa, edwi):
    return {
        "url": result["url"],
        "title": result.get("title", "-"),
        # Dashboard/Excel cukup menampilkan kategori, tanpa ID setelah slash.
        "category": str(result.get("category", "-") or "-").split("/")[0].strip(),
        "author": result.get("author", "-"),
        "published": result.get("published", ""),
        "published_date": result.get("published_date", ""),
        "sifa": sifa,
        "edwi": edwi,
    }


def main():
    previous = read_previous_data()
    old_articles = previous.get("articles", [])

    try:
        items, discovery_errors = discover(50)
    except Exception as exc:
        print(f"DISCOVERY GAGAL TOTAL: {type(exc).__name__}: {exc}", file=sys.stderr)
        print("Data lama dipertahankan; data.json tidak diubah.", file=sys.stderr)
        return 1

    print(f"Discovery selesai: {len(items)} URL; error halaman: {discovery_errors}")
    if not items:
        print("Tidak ada URL yang ditemukan. Untuk mencegah dashboard menjadi 0 akibat gangguan sumber, data lama dipertahankan.", file=sys.stderr)
        return 1

    fetched = []
    errors = discovery_errors
    with ThreadPoolExecutor(max_workers=ARTICLE_WORKERS, thread_name_prefix="article") as executor:
        futures = {executor.submit(fetch_article, item): item for item in items}
        for future in as_completed(futures):
            item = futures[future]
            try:
                result = future.result()
            except Exception as exc:
                errors += 1
                print(f"Artikel gagal {item.get('url', '-')}: {type(exc).__name__}: {exc}", file=sys.stderr)
                continue
            fetched.append(result)
            if result.get("error"):
                errors += 1
                print(f"Artikel gagal {result.get('url', '-')}: {result['error']}", file=sys.stderr)

    successful = [r for r in fetched if not r.get("error")]
    if not successful:
        print(f"Semua fetch artikel gagal ({errors} error). Data lama dipertahankan; data.json tidak diubah.", file=sys.stderr)
        return 1

    fresh_by_url = {}
    for result in successful:
        sifa, edwi = is_match(result)
        if sifa or edwi:
            fresh_by_url[result["url"]] = article_record(result, sifa, edwi)

    # Bila discovery/fetch parsial, pertahankan hasil lama untuk URL yang belum berhasil
    # diproses. URL yang berhasil dibaca akan diperbarui atau dihapus jika tak lagi cocok.
    partial_scan = errors > 0 or len(successful) < len(items)
    if partial_scan:
        merged = {a.get("url"): a for a in old_articles if a.get("url")}
        successfully_checked_urls = {r.get("url") for r in successful}
        for url in successfully_checked_urls:
            merged.pop(url, None)
        merged.update(fresh_by_url)
        articles = list(merged.values())
        print("Scan parsial: hasil lama untuk artikel yang belum berhasil dicek dipertahankan.")
    else:
        articles = list(fresh_by_url.values())

    articles.sort(key=lambda a: (a.get("published_date", ""), a.get("title", "")), reverse=True)
    tz = ZoneInfo("Asia/Jakarta") if ZoneInfo else timezone.utc
    now = datetime.now(timezone.utc).astimezone(tz).strftime("%Y-%m-%d %H:%M:%S WIB")
    data = {
        "meta": {
            "last_scan": now,
            "discovered": len(items),
            "fetched": len(successful),
            "matched": len(articles),
            "errors": errors,
            "workers": ARTICLE_WORKERS,
            "status": "partial" if partial_scan else "success",
        },
        "articles": articles,
    }
    write_json_atomic(data)
    print("HASIL SCAN:")
    print(json.dumps(data["meta"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
