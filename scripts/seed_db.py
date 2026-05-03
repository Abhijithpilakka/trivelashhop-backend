#!/usr/bin/env python3
"""
scripts/seed_db.py
------------------
Seeds the Supabase products table with the 6 default kits.
Run: python scripts/seed_db.py

Requires SUPABASE_URL and SUPABASE_SERVICE_KEY in .env
"""

import os
import sys
from pathlib import Path

# Allow running from root or scripts/
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

PRODUCTS = [
    {
        "name": "Real Madrid Home 24/25", "club": "Real Madrid", "category": "Club",
        "description": "The iconic all-white home shirt for the 24/25 season. Adidas AEROREADY moisture-wicking technology. Official crest with precision embroidery finish.",
        "price": 1299, "offer_price": 999, "logo": "Embroidery", "in_stock": True,
        "sizes": {"S": 8, "M": 3, "L": 0, "XL": 5, "XXL": 2},
        "versions": ["Fan Version", "Player Version", "Master Copy"],
        "photos": [
            "https://images.unsplash.com/photo-1517649763962-0c623066013b?w=600&q=80",
            "https://images.unsplash.com/photo-1605152276897-4f618f831968?w=600&q=80",
        ],
        "tag": "bestseller",
    },
    {
        "name": "FC Barcelona Away 24/25", "club": "FC Barcelona", "category": "Club",
        "description": "Deep navy away kit with gold trim. Nike Dri-FIT technology. Heat-pressed crest for a sleek low-profile look.",
        "price": 1399, "offer_price": 1099, "logo": "Heat Pressed", "in_stock": True,
        "sizes": {"S": 4, "M": 0, "L": 7, "XL": 3, "XXL": 1},
        "versions": ["Fan Version", "Player Version", "Master Copy"],
        "photos": ["https://images.unsplash.com/photo-1552674605-db6ffd4facb5?w=600&q=80"],
        "tag": "new",
    },
    {
        "name": "India National Home", "club": "India", "category": "National",
        "description": "Wear the Blue Tigers with pride. AIFF crest embroidery. Premium polyester blend for match and everyday wear.",
        "price": 899, "offer_price": None, "logo": "Embroidery", "in_stock": True,
        "sizes": {"S": 12, "M": 8, "L": 5, "XL": 9, "XXL": 3},
        "versions": ["Fan Version", "Master Copy"],
        "photos": ["https://images.unsplash.com/photo-1543326727-cf6c39e8f84c?w=600&q=80"],
        "tag": None,
    },
    {
        "name": "Manchester City Third 24/25", "club": "Manchester City", "category": "Club",
        "description": "Man City's limited third kit. Bold geometric print. Heat-pressed Puma badge. Collector's edition.",
        "price": 1199, "offer_price": 949, "logo": "Heat Pressed", "in_stock": False,
        "sizes": {"S": 0, "M": 0, "L": 0, "XL": 0, "XXL": 0},
        "versions": ["Fan Version", "Player Version"],
        "photos": ["https://images.unsplash.com/photo-1589487391730-58f20eb2c308?w=600&q=80"],
        "tag": "soldout",
    },
    {
        "name": "Liverpool Home 24/25", "club": "Liverpool", "category": "Club",
        "description": "Classic red with subtle tonal pinstripes. Nike Dri-FIT ADV. Embroidered crest, match-day ready.",
        "price": 1299, "offer_price": 1049, "logo": "Embroidery", "in_stock": True,
        "sizes": {"S": 2, "M": 6, "L": 4, "XL": 1, "XXL": 5},
        "versions": ["Fan Version", "Player Version", "Master Copy"],
        "photos": ["https://images.unsplash.com/photo-1622279457486-62dcc4a431d6?w=600&q=80"],
        "tag": "bestseller",
    },
    {
        "name": "Brazil Retro 1970", "club": "Brazil", "category": "Retro",
        "description": "Faithful replica of Brazil's 1970 World Cup shirt. Canary yellow with green trim. Cotton-blend, embroidered CBF crest.",
        "price": 1099, "offer_price": 849, "logo": "Embroidery", "in_stock": True,
        "sizes": {"S": 6, "M": 4, "L": 8, "XL": 2, "XXL": 1},
        "versions": ["Fan Version", "Master Copy"],
        "photos": ["https://images.unsplash.com/photo-1574629810360-7efbbe195018?w=600&q=80"],
        "tag": "retro",
    },
]


def main():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not url or not key:
        print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env")
        sys.exit(1)

    sb = create_client(url, key)

    print(f"Seeding {len(PRODUCTS)} products...")
    result = sb.table("products").insert(PRODUCTS).execute()
    inserted = len(result.data or [])
    print(f"✓ Inserted {inserted} products")


if __name__ == "__main__":
    main()
