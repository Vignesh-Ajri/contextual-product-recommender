import os
import json
import uuid
import sys
import django
from decimal import Decimal

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from products.models import Product, Category

def get_price_from_range(price_range):
    """Estimate a base price from the CPRP price_range."""
    price_map = {
        "0-50": 35.0, "50-100": 75.0, "100-250": 175.0,
        "250-500": 375.0, "500-1000": 750.0, "1000-2000": 1500.0,
        "2000+": 2500.0, "0-500": 250.0, "500-1k": 750.0, "1k-5k": 2500.0
    }
    return Decimal(str(price_map.get(price_range, 100.0)))

def run():
    print("Clearing existing products...")
    Product.objects.all().delete()
    Category.objects.all().delete()
    
    # Read the existing PRODUCTS dict from cprp data generator script to maintain consistency
    sys.path.append(os.path.join(os.path.dirname(__file__), '../../../data'))
    try:
        from generate_fmcg_data import PRODUCTS
    except ImportError:
        print("Failed to import PRODUCTS from generate_fmcg_data.py")
        return
        
    print(f"Loaded {len(PRODUCTS)} categories from CPRP synthetic data.")
    
    # Create categories
    category_map = {}
    for cat_name, cat_data in PRODUCTS.items():
        clean_name = cat_name.replace('_', ' ').title()
        category = Category.objects.create(
            name=clean_name,
            cprp_category=cat_name
        )
        category_map[cat_name] = category
        print(f"Created category: {clean_name}")
        
        # Create products for each brand and price range in this category
        for brand in cat_data['brands']:
            for price_range in cat_data['price_ranges']:
                prod_name = f"{brand.title()} {clean_name}"
                base_price = get_price_from_range(price_range)
                
                Product.objects.create(
                    name=prod_name,
                    category=category,
                    brand=brand.title(),
                    price=base_price,
                    compare_price=base_price * Decimal('1.2'),
                    cprp_brand=brand,
                    cprp_price_range=price_range
                )
    
    print(f"\nSeed complete! Created {Product.objects.count()} products.")

if __name__ == '__main__':
    run()
