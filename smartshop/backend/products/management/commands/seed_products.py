from django.core.management.base import BaseCommand
from products.models import Category, Product, ProductFeature
import random

PRODUCTS_DATA = [
    # ---- SHAMPOO ----
    {
        "category": "Hair Care", "emoji_cat": "💇",
        "brand": "Head & Shoulders", "name": "Head & Shoulders Classic Clean Shampoo",
        "price": 189, "compare_price": 230, "emoji": "🧴",
        "description": "Clinically proven anti-dandruff shampoo that leaves hair clean, fresh and 100% flake free. Gentle enough for everyday use.",
        "rating": 4.4, "reviews": 2341,
        "features": [
            ("Size", "340 ml"), ("Type", "Anti-Dandruff"), ("Hair Type", "All Types"),
            ("Key Ingredient", "Zinc Pyrithione"), ("Usage", "Daily"), ("Fragrance", "Classic Clean"),
        ]
    },
    {
        "category": "Hair Care", "emoji_cat": "💇",
        "brand": "Dove", "name": "Dove Intense Repair Shampoo",
        "price": 145, "compare_price": 175, "emoji": "🧴",
        "description": "Dove Intense Repair Shampoo with Keratin Actives repairs damage and makes hair strong and beautiful.",
        "rating": 4.3, "reviews": 1892,
        "features": [
            ("Size", "340 ml"), ("Type", "Repair"), ("Hair Type", "Damaged Hair"),
            ("Key Ingredient", "Keratin Actives"), ("Usage", "3x per week"), ("Fragrance", "Soft Floral"),
        ]
    },
    {
        "category": "Hair Care", "emoji_cat": "💇",
        "brand": "Clinic Plus", "name": "Clinic Plus Strong & Long Shampoo",
        "price": 65, "compare_price": None, "emoji": "🧴",
        "description": "Clinic Plus shampoo with Milk Protein and Vitamin complex strengthens hair from root to tip, preventing hair fall.",
        "rating": 4.1, "reviews": 3200,
        "features": [
            ("Size", "175 ml"), ("Type", "Strengthening"), ("Hair Type", "Weak Hair"),
            ("Key Ingredient", "Milk Protein + Vitamin E"), ("Usage", "Daily"), ("Fragrance", "Fresh"),
        ]
    },
    {
        "category": "Hair Care", "emoji_cat": "💇",
        "brand": "Pantene", "name": "Pantene Pro-V Silky Smooth Shampoo",
        "price": 199, "compare_price": 250, "emoji": "🧴",
        "description": "Pantene Pro-V with Pro-Vitamin formula tames frizz and gives intense smoothness and shine.",
        "rating": 4.5, "reviews": 1750,
        "features": [
            ("Size", "340 ml"), ("Type", "Smoothing"), ("Hair Type", "Frizzy Hair"),
            ("Key Ingredient", "Pro-Vitamin B5"), ("Usage", "Daily"), ("Fragrance", "Rose"),
        ]
    },

    # ---- TOOTHPASTE ----
    {
        "category": "Oral Care", "emoji_cat": "🦷",
        "brand": "Colgate", "name": "Colgate Strong Teeth Toothpaste",
        "price": 79, "compare_price": 95, "emoji": "🪥",
        "description": "Colgate Strong Teeth with Amino Shakti builds strong teeth with regular use. Protects against cavities and strengthens enamel.",
        "rating": 4.5, "reviews": 5620,
        "features": [
            ("Size", "200g"), ("Type", "Cavity Protection"), ("Fluoride", "Yes"),
            ("Key Ingredient", "Amino Shakti"), ("Flavor", "Spearmint"), ("For", "Whole Family"),
        ]
    },
    {
        "category": "Oral Care", "emoji_cat": "🦷",
        "brand": "Sensodyne", "name": "Sensodyne Rapid Relief Toothpaste",
        "price": 185, "compare_price": 220, "emoji": "🪥",
        "description": "Sensodyne Rapid Relief provides clinically proven rapid sensitivity relief with regular twice-daily brushing.",
        "rating": 4.6, "reviews": 3100,
        "features": [
            ("Size", "75g"), ("Type", "Sensitive"), ("Fluoride", "Yes"),
            ("Key Ingredient", "Strontium Acetate"), ("Flavor", "Mint"), ("For", "Sensitive Teeth"),
        ]
    },
    {
        "category": "Oral Care", "emoji_cat": "🦷",
        "brand": "Pepsodent", "name": "Pepsodent Germicheck Toothpaste",
        "price": 55, "compare_price": 70, "emoji": "🪥",
        "description": "Pepsodent Germicheck toothpaste with iLAC provides 12 hour germ protection for strong teeth and healthy gums.",
        "rating": 4.2, "reviews": 2800,
        "features": [
            ("Size", "150g"), ("Type", "Anti-Bacterial"), ("Fluoride", "Yes"),
            ("Key Ingredient", "iLAC"), ("Flavor", "Mint"), ("Protection", "12 Hours"),
        ]
    },
    {
        "category": "Oral Care", "emoji_cat": "🦷",
        "brand": "Dabur", "name": "Dabur Red Paste Ayurvedic Toothpaste",
        "price": 89, "compare_price": 105, "emoji": "🪥",
        "description": "Dabur Red Paste with 13 Ayurvedic ingredients provides complete oral care with natural herbs and goodness.",
        "rating": 4.3, "reviews": 4100,
        "features": [
            ("Size", "200g"), ("Type", "Ayurvedic"), ("Fluoride", "No"),
            ("Key Ingredient", "Clove Oil + Neem"), ("Flavor", "Herbal"), ("Benefits", "5-in-1"),
        ]
    },

    # ---- TOOTHBRUSH ----
    {
        "category": "Oral Care", "emoji_cat": "🦷",
        "brand": "Colgate", "name": "Colgate ZigZag Toothbrush",
        "price": 35, "compare_price": 45, "emoji": "🪥",
        "description": "Colgate ZigZag toothbrush with criss-cross bristles to reach between teeth for a deeper clean.",
        "rating": 4.3, "reviews": 7800,
        "features": [
            ("Pack", "1 Piece"), ("Bristle Type", "Medium"), ("Handle", "Ergonomic"),
            ("Bristle Pattern", "ZigZag"), ("Tongue Cleaner", "Yes"), ("Suitable For", "Adults"),
        ]
    },
    {
        "category": "Oral Care", "emoji_cat": "🦷",
        "brand": "Oral-B", "name": "Oral-B CrossAction Pro-Health Toothbrush",
        "price": 89, "compare_price": 120, "emoji": "🪥",
        "description": "Oral-B CrossAction Pro-Health toothbrush with angled bristles removes up to 300% more plaque than a regular flat trim toothbrush.",
        "rating": 4.6, "reviews": 3400,
        "features": [
            ("Pack", "1 Piece"), ("Bristle Type", "Soft"), ("Handle", "Comfort Grip"),
            ("Bristle Pattern", "Cross-Action"), ("Plaque Removal", "300% More"), ("Suitable For", "Adults"),
        ]
    },

    # ---- SOAP ----
    {
        "category": "Bath & Body", "emoji_cat": "🛁",
        "brand": "Dove", "name": "Dove Moisturising Cream Beauty Bathing Bar",
        "price": 55, "compare_price": 65, "emoji": "🧼",
        "description": "Dove beauty bar with 1/4 moisturising cream leaves skin soft and smooth, unlike regular soaps that can leave skin feeling dry.",
        "rating": 4.5, "reviews": 9200,
        "features": [
            ("Weight", "100g"), ("Type", "Moisturising"), ("Skin Type", "All Types"),
            ("Key Ingredient", "1/4 Moisturising Cream"), ("Fragrance", "Soft"), ("Pack", "Pack of 3"),
        ]
    },
    {
        "category": "Bath & Body", "emoji_cat": "🛁",
        "brand": "Lifebuoy", "name": "Lifebuoy Total 10 Soap",
        "price": 40, "compare_price": 50, "emoji": "🧼",
        "description": "Lifebuoy Total 10 soap with Active Silver formula protects against 10 types of germs, giving complete hygiene protection.",
        "rating": 4.3, "reviews": 6700,
        "features": [
            ("Weight", "125g"), ("Type", "Antibacterial"), ("Skin Type", "All Types"),
            ("Key Ingredient", "Active Silver"), ("Fragrance", "Fresh"), ("Protection", "10 Germs"),
        ]
    },
    {
        "category": "Bath & Body", "emoji_cat": "🛁",
        "brand": "Lux", "name": "Lux Velvet Glow Soap",
        "price": 45, "compare_price": 55, "emoji": "🧼",
        "description": "Lux Velvet Glow soap with Glycerin and Jojoba oil gives skin a velvet glow and smooth finish with every use.",
        "rating": 4.2, "reviews": 4500,
        "features": [
            ("Weight", "120g"), ("Type", "Moisturising"), ("Skin Type", "Normal to Dry"),
            ("Key Ingredient", "Glycerin + Jojoba Oil"), ("Fragrance", "Floral"), ("Finish", "Velvet Glow"),
        ]
    },
    {
        "category": "Bath & Body", "emoji_cat": "🛁",
        "brand": "Pears", "name": "Pears Pure & Gentle Soap",
        "price": 48, "compare_price": 60, "emoji": "🧼",
        "description": "Pears Pure & Gentle soap is a transparent glycerine soap with natural oils. Dermatologically tested and gentle on skin.",
        "rating": 4.6, "reviews": 8100,
        "features": [
            ("Weight", "125g"), ("Type", "Gentle"), ("Skin Type", "Sensitive"),
            ("Key Ingredient", "Glycerine + Natural Oils"), ("Fragrance", "Original"), ("Dermatology", "Tested"),
        ]
    },

    # ---- FACE WASH ----
    {
        "category": "Skincare", "emoji_cat": "✨",
        "brand": "Cetaphil", "name": "Cetaphil Gentle Skin Cleanser Face Wash",
        "price": 395, "compare_price": 450, "emoji": "💆",
        "description": "Cetaphil Gentle Skin Cleanser is a mild, non-irritating cleanser that removes dirt and makeup without disturbing skin's natural pH.",
        "rating": 4.7, "reviews": 4800,
        "features": [
            ("Size", "250 ml"), ("Type", "Gentle Cleanser"), ("Skin Type", "All/Sensitive"),
            ("Key Ingredient", "Niacinamide"), ("Soap Free", "Yes"), ("Dermatologist", "Recommended"),
        ]
    },
    {
        "category": "Skincare", "emoji_cat": "✨",
        "brand": "Himalaya", "name": "Himalaya Purifying Neem Face Wash",
        "price": 110, "compare_price": 130, "emoji": "💆",
        "description": "Himalaya Neem Face Wash with Neem and Turmeric purifies skin by removing excess oil and preventing pimples.",
        "rating": 4.4, "reviews": 7600,
        "features": [
            ("Size", "150 ml"), ("Type", "Purifying"), ("Skin Type", "Oily/Acne-Prone"),
            ("Key Ingredient", "Neem + Turmeric"), ("Soap Free", "Yes"), ("Benefit", "Anti-Acne"),
        ]
    },
    {
        "category": "Skincare", "emoji_cat": "✨",
        "brand": "Garnier", "name": "Garnier Bright Complete Vitamin C Face Wash",
        "price": 125, "compare_price": 150, "emoji": "💆",
        "description": "Garnier Bright Complete Face Wash with Vitamin C brightens dull skin and gives a refreshing cleanse with every use.",
        "rating": 4.3, "reviews": 5200,
        "features": [
            ("Size", "100 ml"), ("Type", "Brightening"), ("Skin Type", "Dull Skin"),
            ("Key Ingredient", "Vitamin C + Yuzu Lemon"), ("Soap Free", "Yes"), ("Benefit", "Brightening"),
        ]
    },

    # ---- MOISTURISER / LOTION ----
    {
        "category": "Skincare", "emoji_cat": "✨",
        "brand": "Nivea", "name": "Nivea Soft Light Moisturising Cream",
        "price": 148, "compare_price": 175, "emoji": "🧴",
        "description": "Nivea Soft with Jojoba Oil and Vitamin E provides instant deep moisturisation for soft and supple skin all day.",
        "rating": 4.6, "reviews": 9500,
        "features": [
            ("Size", "200 ml"), ("Type", "Moisturiser"), ("Skin Type", "Normal to Dry"),
            ("Key Ingredient", "Jojoba Oil + Vitamin E"), ("Texture", "Light Cream"), ("Usage", "Face & Body"),
        ]
    },
    {
        "category": "Skincare", "emoji_cat": "✨",
        "brand": "Vaseline", "name": "Vaseline Intensive Care Deep Restore Lotion",
        "price": 215, "compare_price": 260, "emoji": "🧴",
        "description": "Vaseline Deep Restore with micro-droplets of Vaseline Jelly heals dry skin from within for visibly healthier skin.",
        "rating": 4.5, "reviews": 6300,
        "features": [
            ("Size", "400 ml"), ("Type", "Body Lotion"), ("Skin Type", "Dry"),
            ("Key Ingredient", "Vaseline Jelly Micro-Droplets"), ("Texture", "Non-Greasy"), ("Usage", "Body"),
        ]
    },

    # ---- DEODORANT ----
    {
        "category": "Personal Care", "emoji_cat": "🌿",
        "brand": "Axe", "name": "Axe Dark Temptation Deodorant Body Spray",
        "price": 195, "compare_price": 230, "emoji": "🌬️",
        "description": "Axe Dark Temptation with irresistible chocolate scent keeps you fresh and confident all day long.",
        "rating": 4.3, "reviews": 4100,
        "features": [
            ("Size", "150 ml"), ("Type", "Body Spray"), ("Fragrance", "Chocolate"),
            ("Protection", "48 Hours"), ("Alcohol", "Yes"), ("Gender", "Men"),
        ]
    },
    {
        "category": "Personal Care", "emoji_cat": "🌿",
        "brand": "Dove", "name": "Dove Original Antiperspirant Deodorant",
        "price": 225, "compare_price": 270, "emoji": "🌬️",
        "description": "Dove Original antiperspirant deodorant with 1/4 moisturising cream protects against sweat for 48 hours and cares for underarm skin.",
        "rating": 4.5, "reviews": 3700,
        "features": [
            ("Size", "150 ml"), ("Type", "Antiperspirant"), ("Fragrance", "Clean Fresh"),
            ("Protection", "48 Hours"), ("Moisturising", "Yes"), ("Gender", "Women"),
        ]
    },
    {
        "category": "Personal Care", "emoji_cat": "🌿",
        "brand": "Fogg", "name": "Fogg Black Collection Body Spray",
        "price": 175, "compare_price": 210, "emoji": "🌬️",
        "description": "Fogg Black Collection body spray with exclusive fragrance provides lasting freshness with no gas - just pure long lasting fragrance.",
        "rating": 4.4, "reviews": 5800,
        "features": [
            ("Size", "150 ml"), ("Type", "Body Spray"), ("Fragrance", "Intense Wood"),
            ("No Gas", "Yes"), ("Duration", "Long Lasting"), ("Gender", "Men"),
        ]
    },

    # ---- HAIR OIL ----
    {
        "category": "Hair Care", "emoji_cat": "💇",
        "brand": "Parachute", "name": "Parachute Advansed Coconut Hair Oil",
        "price": 120, "compare_price": 145, "emoji": "🫙",
        "description": "Parachute Advansed Coconut Hair Oil provides deep nourishment and conditioning for strong, healthy, long hair.",
        "rating": 4.5, "reviews": 11200,
        "features": [
            ("Size", "300 ml"), ("Type", "Coconut Oil"), ("Hair Type", "All Types"),
            ("Key Ingredient", "Pure Coconut Oil"), ("Benefits", "Nourishment + Growth"), ("Usage", "Pre-wash"),
        ]
    },
    {
        "category": "Hair Care", "emoji_cat": "💇",
        "brand": "Bajaj", "name": "Bajaj Almond Drops Hair Oil",
        "price": 89, "compare_price": 110, "emoji": "🫙",
        "description": "Bajaj Almond Drops hair oil with Vitamin E and almond extracts nourishes hair and gives shine and smoothness.",
        "rating": 4.4, "reviews": 8900,
        "features": [
            ("Size", "200 ml"), ("Type", "Almond Oil"), ("Hair Type", "All Types"),
            ("Key Ingredient", "Vitamin E + Almond"), ("Non-Sticky", "Yes"), ("Benefit", "Shine + Nourishment"),
        ]
    },

    # ---- HAND WASH ----
    {
        "category": "Bath & Body", "emoji_cat": "🛁",
        "brand": "Dettol", "name": "Dettol Original Liquid Hand Wash",
        "price": 99, "compare_price": 120, "emoji": "🧴",
        "description": "Dettol Original liquid handwash kills 99.9% germs and provides germ protection for the whole family with every wash.",
        "rating": 4.5, "reviews": 8400,
        "features": [
            ("Size", "250 ml"), ("Type", "Antibacterial"), ("Kills Germs", "99.9%"),
            ("Fragrance", "Pine"), ("Suitable For", "All Family"), ("Refill Available", "Yes"),
        ]
    },
    {
        "category": "Bath & Body", "emoji_cat": "🛁",
        "brand": "Lifebuoy", "name": "Lifebuoy Care Hand Wash",
        "price": 85, "compare_price": 100, "emoji": "🧴",
        "description": "Lifebuoy Care hand wash with Active Silver formula provides 10x better germ protection than ordinary hand wash.",
        "rating": 4.4, "reviews": 5600,
        "features": [
            ("Size", "215 ml"), ("Type", "Antibacterial"), ("Active Silver", "Yes"),
            ("Fragrance", "Fresh"), ("Protection", "10x Better"), ("pH", "Balanced"),
        ]
    },

    # ---- TALCUM POWDER ----
    {
        "category": "Personal Care", "emoji_cat": "🌿",
        "brand": "Ponds", "name": "Ponds Dream Flower Fragrant Talc",
        "price": 75, "compare_price": 90, "emoji": "🌸",
        "description": "Ponds Dream Flower fragrant talc with real flower extracts keeps you feeling fresh and smelling beautiful all day.",
        "rating": 4.4, "reviews": 6100,
        "features": [
            ("Weight", "200g"), ("Type", "Talcum Powder"), ("Fragrance", "Rose"),
            ("Key Ingredient", "Real Flower Extract"), ("Skin Feel", "Smooth"), ("Moisture", "Absorbing"),
        ]
    },
    {
        "category": "Personal Care", "emoji_cat": "🌿",
        "brand": "Nycil", "name": "Nycil Cool Herbal Prickly Heat Powder",
        "price": 65, "compare_price": 80, "emoji": "🌸",
        "description": "Nycil Cool Herbal powder with Pudina Satva and Neem provides cooling relief from prickly heat and keeps skin fresh.",
        "rating": 4.3, "reviews": 4300,
        "features": [
            ("Weight", "150g"), ("Type", "Prickly Heat"), ("Fragrance", "Herbal"),
            ("Key Ingredient", "Pudina + Neem"), ("Cooling", "Yes"), ("Usage", "After Bath"),
        ]
    },

    # ---- CONDITIONER ----
    {
        "category": "Hair Care", "emoji_cat": "💇",
        "brand": "TRESemmé", "name": "TRESemmé Keratin Smooth Conditioner",
        "price": 225, "compare_price": 275, "emoji": "🧴",
        "description": "TRESemmé Keratin Smooth conditioner with BIOTIN and Silk Protein smoothens and detangles hair leaving it sleek and frizz-free.",
        "rating": 4.4, "reviews": 2800,
        "features": [
            ("Size", "340 ml"), ("Type", "Smoothing"), ("Hair Type", "Frizzy Hair"),
            ("Key Ingredient", "Keratin + Silk Protein"), ("Usage", "After Shampoo"), ("Rinse", "2 Minutes"),
        ]
    },

    # ---- SUNSCREEN ----
    {
        "category": "Skincare", "emoji_cat": "✨",
        "brand": "Neutrogena", "name": "Neutrogena Ultra Sheer Dry Touch Sunscreen SPF 50+",
        "price": 399, "compare_price": 480, "emoji": "☀️",
        "description": "Neutrogena Ultra Sheer sunscreen with SPF 50+ provides broad-spectrum UVA+UVB protection with lightweight, non-greasy feel.",
        "rating": 4.5, "reviews": 3900,
        "features": [
            ("Size", "88 ml"), ("SPF", "50+"), ("Type", "Broad Spectrum"),
            ("Finish", "Dry Touch"), ("Water Resistant", "80 Minutes"), ("Skin Type", "All Types"),
        ]
    },

    # ---- FACE CREAM ----
    {
        "category": "Skincare", "emoji_cat": "✨",
        "brand": "Pond's", "name": "Pond's White Beauty Daily Spot-Less Cream",
        "price": 130, "compare_price": 160, "emoji": "🧴",
        "description": "Pond's White Beauty cream with melanin reduction technology visibly reduces spots and gives bright, glowing skin in 4 weeks.",
        "rating": 4.2, "reviews": 5700,
        "features": [
            ("Size", "50g"), ("Type", "Fairness Cream"), ("SPF", "15"),
            ("Key Ingredient", "Niacinamide + Vitamin B3"), ("Result", "4 Weeks"), ("Usage", "Morning"),
        ]
    },
]

CATEGORIES = [
    {"name": "Hair Care", "slug": "hair-care", "emoji": "💇", "description": "Shampoos, conditioners, hair oils and treatments for healthy hair"},
    {"name": "Oral Care", "slug": "oral-care", "emoji": "🦷", "description": "Toothpastes, toothbrushes and mouthwashes for oral hygiene"},
    {"name": "Bath & Body", "slug": "bath-body", "emoji": "🛁", "description": "Soaps, hand washes and body wash for daily hygiene"},
    {"name": "Skincare", "slug": "skincare", "emoji": "✨", "description": "Face wash, moisturisers and sunscreens for healthy skin"},
    {"name": "Personal Care", "slug": "personal-care", "emoji": "🌿", "description": "Deodorants, talc and other personal care essentials"},
]

class Command(BaseCommand):
    help = "Seed the database with 30+ daily-use products across multiple brands and categories"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding database with categories and products...")

        # Create categories
        cat_map = {}
        for cat_data in CATEGORIES:
            cat, created = Category.objects.update_or_create(
                slug=cat_data["slug"],
                defaults={
                    "name": cat_data["name"],
                    "emoji": cat_data["emoji"],
                    "description": cat_data["description"],
                    "is_active": True,
                }
            )
            cat_map[cat_data["name"]] = cat
            action = "Created" if created else "Updated"
            self.stdout.write(f"  {action} category: {cat.name}")

        # Create products
        created_count = 0
        for prod in PRODUCTS_DATA:
            from django.utils.text import slugify
            import uuid
            base_slug = slugify(prod["name"])
            # Ensure slug uniqueness
            slug = base_slug
            if Product.objects.filter(slug=slug).exists():
                slug = base_slug + "-" + str(uuid.uuid4())[:6]

            category = cat_map.get(prod["category"])
            product, created = Product.objects.update_or_create(
                name=prod["name"],
                defaults={
                    "slug": slug,
                    "description": prod["description"],
                    "category": category,
                    "brand": prod["brand"],
                    "price": prod["price"],
                    "compare_price": prod.get("compare_price"),
                    "emoji": prod.get("emoji", "🧴"),
                    "rating": prod["rating"],
                    "review_count": prod["reviews"],
                    "stock_quantity": random.randint(50, 300),
                    "is_active": True,
                    "cprp_brand": prod["brand"].lower().replace(" ", "_"),
                    "cprp_price_range": "budget" if prod["price"] < 100 else "mid" if prod["price"] < 300 else "premium",
                }
            )

            # Recreate features
            product.features.all().delete()
            for i, (key, value) in enumerate(prod["features"]):
                ProductFeature.objects.create(product=product, key=key, value=value, order=i)

            if created:
                created_count += 1
                self.stdout.write(f"  [CREATED] {product.brand} - {product.name}")
            else:
                self.stdout.write(f"  [UPDATED] {product.brand} - {product.name}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! {len(CATEGORIES)} categories and {len(PRODUCTS_DATA)} products seeded."
        ))
