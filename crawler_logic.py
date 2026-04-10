import csv
import re
import time
from pathlib import Path
from typing import Any

import requests


GRAPHQL_URL = "https://online.mmvietnam.com/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/123.0.0.0 Safari/537.36"
    ),
}
REQUEST_TIMEOUT = 30
PAGE_SIZE = 40
SLEEP_SECONDS = 1.2


def build_search_payload(keyword: str, page: int) -> dict[str, Any]:
    return {
        "operationName": "GetProductsBySearch",
        "query": """
            query GetProductsBySearch($search: String!, $pageSize: Int!, $currentPage: Int!, $sort: ProductAttributeSortInput) {
                products(search: $search, pageSize: $pageSize, currentPage: $currentPage, sort: $sort) {
                    items {
                        id
                        uid
                        name
                        sku
                        ecom_name
                        mm_barcode
                        price_range {
                            maximum_price {
                                final_price { currency value }
                                regular_price { currency value }
                            }
                        }
                        small_image { url }
                    }
                    page_info {
                        total_pages
                    }
                    total_count
                }
            }
        """,
        "variables": {
            "search": keyword,
            "pageSize": PAGE_SIZE,
            "currentPage": page,
            "sort": {"position": "DESC"},
        },
    }


def sanitize_filename(keyword: str) -> str:
    normalized = re.sub(r"\s+", "_", keyword.strip())
    safe_name = re.sub(r"[^0-9A-Za-z_\-À-ỹ]", "", normalized)
    return safe_name or "ket_qua"


def flatten_products(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in items:
        price_info = item.get("price_range", {}).get("maximum_price", {})
        rows.append(
            {
                "ID": item.get("id"),
                "SKU": item.get("sku"),
                "Barcode": item.get("mm_barcode"),
                "Name": item.get("name"),
                "Ecom Name": item.get("ecom_name"),
                "Final Price": price_info.get("final_price", {}).get("value"),
                "Regular Price": price_info.get("regular_price", {}).get("value"),
                "Currency": price_info.get("final_price", {}).get("currency"),
                "Image URL": item.get("small_image", {}).get("url"),
            }
        )
    return rows


def save_to_csv(rows: list[dict[str, Any]], keyword: str, output_dir: Path) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"search_{sanitize_filename(keyword)}.csv"

    with file_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return file_path


def crawl_products(keyword: str, output_dir: str | Path | None = None) -> dict[str, Any]:
    target_dir = Path(output_dir) if output_dir else Path(__file__).resolve().parent
    current_page = 1
    total_pages = 1
    all_products: list[dict[str, Any]] = []

    try:
        while current_page <= total_pages:
            payload = build_search_payload(keyword, current_page)
            response = requests.post(
                GRAPHQL_URL,
                headers=HEADERS,
                json=payload,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()

            data = response.json()
            products_data = data.get("data", {}).get("products", {})
            items = products_data.get("items", [])

            if not products_data or not items and current_page == 1:
                return {"success": False, "message": "No products found."}

            all_products.extend(flatten_products(items))
            total_pages = products_data.get("page_info", {}).get("total_pages", 1)
            current_page += 1

            if current_page <= total_pages:
                time.sleep(SLEEP_SECONDS)

        if not all_products:
            return {"success": False, "message": "No products found."}

        file_path = save_to_csv(all_products, keyword, target_dir)
        file_bytes = file_path.read_bytes()

        return {
            "success": True,
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_bytes": file_bytes,
            "total_products": len(all_products),
        }
    except (requests.RequestException, ValueError, OSError):
        return {"success": False, "message": "Crawler failed."}
