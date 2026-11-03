from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from cart.models import Cart, CartItem
from products.models import Category, Product

CATEGORIES = ["Men", "Women", "Kids"]

ADULT_SIZES = ["S", "M", "L", "XL"]
KIDS_SIZES = ["4Y", "6Y", "8Y", "10Y", "12Y"]

# (category, title, description, price, sizes, stock)
PRODUCTS = [
    ("Men", "Classic White Oxford Shirt", "Cotton oxford shirt with button-down collar.", "34.99", ADULT_SIZES, 40),
    ("Men", "Slim Fit Dark Wash Jeans", "Stretch denim jeans in a dark indigo wash.", "49.90", ["30", "32", "34", "36"], 25),
    ("Men", "Merino Wool Crew Sweater", "Lightweight merino sweater for layering.", "79.00", ADULT_SIZES, 12),
    ("Men", "Basic Crew Neck T-Shirt", "Everyday 100% cotton tee.", "12.50", ["S", "M", "L", "XL", "XXL"], 120),
    ("Men", "Water-Resistant Bomber Jacket", "Padded bomber jacket with ribbed cuffs.", "119.99", ["M", "L", "XL"], 2),
    ("Men", "Chino Shorts", "Relaxed-fit cotton chino shorts.", "27.00", ["30", "32", "34"], 0),
    ("Men", "Leather Derby Shoes", "Full-grain leather derby shoes.", "89.95", ["41", "42", "43", "44", "45"], 18),
    ("Women", "Floral Midi Dress", "Flowy midi dress with a floral print.", "59.99", ["XS", "S", "M", "L"], 22),
    ("Women", "High-Rise Mom Jeans", "Relaxed high-rise jeans with tapered leg.", "54.00", ["24", "26", "28", "30"], 30),
    ("Women", "Cashmere Blend Cardigan", "Soft cashmere-blend cardigan with buttons.", "99.00", ["S", "M", "L"], 1),
    ("Women", "Satin Slip Skirt", "Bias-cut satin midi skirt.", "39.90", ["XS", "S", "M", "L"], 15),
    ("Women", "Oversized Linen Blazer", "Breathable linen blazer, relaxed fit.", "129.00", ["S", "M", "L"], 0),
    ("Women", "Ribbed Tank Top", "Stretch ribbed cotton tank top.", "9.99", ["XS", "S", "M", "L", "XL"], 80),
    ("Women", "Trench Coat", "Classic double-breasted trench coat.", "149.50", ["S", "M", "L"], 9),
    ("Kids", "Dinosaur Print Hoodie", "Fleece hoodie with dinosaur print.", "24.99", KIDS_SIZES, 35),
    ("Kids", "Pull-On Denim Shorts", "Elastic-waist denim shorts.", "14.99", KIDS_SIZES, 40),
    ("Kids", "Striped Long Sleeve Tee", "Organic cotton striped tee.", "11.00", KIDS_SIZES, 60),
    ("Kids", "Puffer Winter Jacket", "Warm hooded puffer jacket.", "64.90", KIDS_SIZES, 5),
    ("Kids", "Light-Up Sneakers", "Velcro sneakers with LED soles.", "34.50", ["28", "29", "30", "31", "32"], 20),
    ("Kids", "Cotton Pajama Set", "Two-piece cotton pajama set.", "19.99", KIDS_SIZES, 28),
]

LOW_STOCK_THRESHOLD = 2


class Command(BaseCommand):
    help = "Seed the database with demo categories and clothing products."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing cart items, carts, products and categories before seeding.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["reset"]:
            # Order matters: Product and Category are PROTECTed by their children.
            deleted = {
                "cart items": CartItem.objects.all().delete()[0],
                "carts": Cart.objects.all().delete()[0],
                "products": Product.objects.all().delete()[0],
                "categories": Category.objects.all().delete()[0],
            }
            summary = ", ".join(f"{count} {name}" for name, count in deleted.items())
            self.stdout.write(self.style.WARNING(f"Reset: deleted {summary}."))
        elif Product.objects.exists():
            self.stdout.write(self.style.NOTICE(
                f"Skipped: {Product.objects.count()} products already exist. "
                "Use --reset to wipe and re-seed."
            ))
            return

        categories = {}
        for name in CATEGORIES:
            categories[name], _ = Category.objects.get_or_create(
                slug=slugify(name), defaults={"name": name}
            )

        # Created one by one so each product gets its own created_at timestamp.
        products = [
            Product.objects.create(
                category=categories[category],
                title=title,
                description=description,
                price=Decimal(price),
                sizes=sizes,
                stock_quantity=stock,
            )
            for category, title, description, price, sizes, stock in PRODUCTS
        ]

        self._print_summary(categories, products)

    def _print_summary(self, categories, products):
        out_of_stock = [p for p in products if p.stock_quantity == 0]
        low_stock = [p for p in products if 0 < p.stock_quantity <= LOW_STOCK_THRESHOLD]
        prices = [p.price for p in products]

        self.stdout.write(self.style.SUCCESS("Seeding complete."))
        self.stdout.write(f"  Categories: {len(categories)}")
        for name, category in categories.items():
            count = sum(1 for p in products if p.category_id == category.id)
            self.stdout.write(f"    - {name}: {count} products")
        self.stdout.write(f"  Products:   {len(products)}")
        self.stdout.write(f"  Price range: {min(prices)} - {max(prices)}")
        self.stdout.write(f"  Out of stock ({len(out_of_stock)}):")
        for p in out_of_stock:
            self.stdout.write(f"    - {p.title}")
        self.stdout.write(f"  Low stock <= {LOW_STOCK_THRESHOLD} ({len(low_stock)}):")
        for p in low_stock:
            self.stdout.write(f"    - {p.title} (stock: {p.stock_quantity})")
