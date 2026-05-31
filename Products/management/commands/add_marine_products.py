from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.core.files.base import ContentFile
from Products.models import Category, Product, ProductImage, ProductVideo
import requests
from io import BytesIO


class Command(BaseCommand):
    help = 'Add marine products to the database'

    def handle(self, *args, **options):
        # Create or get Marine category
        marine_category, created = Category.objects.get_or_create(
            name='Marine Products',
            defaults={
                'slug': 'marine-products',
                'description': 'Fresh marine and ocean products including fish, shrimp, and seafood',
            }
        )

        if created:
            self.stdout.write(
                self.style.SUCCESS(f'Created category: {marine_category.name}')
            )

        # Create subcategories
        subcategories_data = [
            {
                'name': 'Fresh Fish',
                'description': 'Premium quality fresh fish caught daily from the Arabian Gulf'
            },
            {
                'name': 'Shrimp & Prawns',
                'description': 'Fresh and frozen shrimp available in various sizes'
            },
            {
                'name': 'Crustaceans',
                'description': 'Crabs, lobsters, and other shellfish delicacies'
            },
            {
                'name': 'Frozen Seafood',
                'description': 'Frozen marine products for long-term storage'
            },
        ]

        subcategories = {}
        for subcat_data in subcategories_data:
            subcat_slug = slugify(subcat_data['name'])
            subcat, created = Category.objects.get_or_create(
                slug=subcat_slug,
                defaults={
                    'name': subcat_data['name'],
                    'parent': marine_category,
                    'description': subcat_data['description'],
                }
            )
            if subcat.parent is None:
                subcat.parent = marine_category
                subcat.save(update_fields=['parent'])
            subcategories[subcat_data['name']] = subcat
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created subcategory: {subcat.name}')
                )

        # Marine products data
        products_data = [
            # Fresh Fish
            {
                'category': 'Fresh Fish',
                'name': 'Arabian Gulf Hammour',
                'description': 'Premium fresh Hammour fish from the Arabian Gulf. Nutritious white fish rich in protein and omega-3 fatty acids. Perfect for grilling or baking.',
                'price': 89.99,
                'discount_price': 79.99,
                'stock': 45,
                'sku': 'FH-HAMMOUR-001',
                'expected_delivery_time': '30-60 mins'
            },
            {
                'category': 'Fresh Fish',
                'name': 'Fresh Sea Bass',
                'description': 'Delicate and flaky sea bass fillet. High in vitamin D and selenium. Ideal for Pan-searing or steaming with fresh herbs.',
                'price': 74.99,
                'discount_price': 64.99,
                'stock': 38,
                'sku': 'FH-BASS-001',
                'expected_delivery_time': '30-60 mins'
            },
            {
                'category': 'Fresh Fish',
                'name': 'Fresh Red Snapper',
                'description': 'Whole fresh red snapper with vibrant red color. Perfect for traditional Middle Eastern fish preparations. Very flavorful and firm meat.',
                'price': 69.99,
                'discount_price': None,
                'stock': 52,
                'sku': 'FH-SNAPPER-001',
                'expected_delivery_time': '30-60 mins'
            },
            {
                'category': 'Fresh Fish',
                'name': 'Fresh Grouper Fillet',
                'description': 'Boneless grouper fillet. Mild, delicate flavor. Excellent source of protein. Suitable for all cooking methods.',
                'price': 94.99,
                'discount_price': 84.99,
                'stock': 28,
                'sku': 'FH-GROUPER-001',
                'expected_delivery_time': '45-75 mins'
            },
            # Shrimp & Prawns
            {
                'category': 'Shrimp & Prawns',
                'name': 'Fresh Gulf Shrimp (Large)',
                'description': 'Large premium shrimp from the Arabian Gulf. Succulent and tender. Perfect for grilling, frying, or in curries. 500g per pack.',
                'price': 99.99,
                'discount_price': 89.99,
                'stock': 67,
                'sku': 'SP-SHRIMP-LG-001',
                'expected_delivery_time': '30-45 mins'
            },
            {
                'category': 'Shrimp & Prawns',
                'name': 'Fresh Gulf Shrimp (Medium)',
                'description': 'Medium-sized fresh shrimp. Great for prawns dishes and Asian cuisine. 600g per pack.',
                'price': 69.99,
                'discount_price': 59.99,
                'stock': 85,
                'sku': 'SP-SHRIMP-MD-001',
                'expected_delivery_time': '30-45 mins'
            },
            {
                'category': 'Shrimp & Prawns',
                'name': 'Fresh King Prawns',
                'description': 'Jumbo king prawns with excellent flavor. Perfect for special occasions and premium dishes. 400g per pack.',
                'price': 149.99,
                'discount_price': 129.99,
                'stock': 35,
                'sku': 'SP-PRAWNS-KING-001',
                'expected_delivery_time': 'Next Day'
            },
            {
                'category': 'Shrimp & Prawns',
                'name': 'Frozen Shrimp Mix',
                'description': 'Assorted frozen shrimp in various sizes. Easy to cook from frozen. 1kg per pack.',
                'price': 59.99,
                'discount_price': 49.99,
                'stock': 120,
                'sku': 'SP-SHRIMP-MIX-001',
                'expected_delivery_time': '30-60 mins'
            },
            # Crustaceans
            {
                'category': 'Crustaceans',
                'name': 'Fresh Live Crab',
                'description': 'Live fresh crab caught from the Arabian waters. Sweet, tender meat. Perfect for crab curry or traditional preparations. 600g avg.',
                'price': 119.99,
                'discount_price': 99.99,
                'stock': 22,
                'sku': 'CR-CRAB-LIVE-001',
                'expected_delivery_time': 'Next Day'
            },
            {
                'category': 'Crustaceans',
                'name': 'Fresh Lobster Tail',
                'description': 'Premium lobster tail with succulent meat. Perfect for special dinners. Grilling recommended. 150g per piece.',
                'price': 199.99,
                'discount_price': 179.99,
                'stock': 18,
                'sku': 'CR-LOBSTER-TAIL-001',
                'expected_delivery_time': 'Next Day'
            },
            {
                'category': 'Crustaceans',
                'name': 'Fresh Squid (Kalamari)',
                'description': 'Fresh squid tubes and tentacles. Young and tender. Perfect for Mediterranean dishes. 500g per pack.',
                'price': 54.99,
                'discount_price': 44.99,
                'stock': 40,
                'sku': 'CR-SQUID-001',
                'expected_delivery_time': '45-75 mins'
            },
            {
                'category': 'Crustaceans',
                'name': 'Fresh Octopus',
                'description': 'Fresh wild-caught octopus. Tender and flavorful when cooked properly. Great for grilling. 600g avg.',
                'price': 129.99,
                'discount_price': None,
                'stock': 15,
                'sku': 'CR-OCTOPUS-001',
                'expected_delivery_time': '2-3 Business Days'
            },
            # Frozen Seafood
            {
                'category': 'Frozen Seafood',
                'name': 'Frozen Fish Fillets Mix',
                'description': 'Assorted frozen fish fillets including hamour, grouper, and snapper. Easy to cook. 1kg per pack.',
                'price': 79.99,
                'discount_price': 69.99,
                'stock': 95,
                'sku': 'FS-FILLET-MIX-001',
                'expected_delivery_time': '30-60 mins'
            },
            {
                'category': 'Frozen Seafood',
                'name': 'Frozen Whole Fish (Various)',
                'description': 'Frozen whole fish in assorted varieties. Maintains quality for months when properly stored. 800g avg.',
                'price': 49.99,
                'discount_price': None,
                'stock': 110,
                'sku': 'FS-WHOLE-FISH-001',
                'expected_delivery_time': '30-60 mins'
            },
            {
                'category': 'Frozen Seafood',
                'name': 'Frozen Seafood Cocktail',
                'description': 'Mix of frozen shrimp, fish, and squid. Perfect for paella and seafood dishes. 500g per pack.',
                'price': 89.99,
                'discount_price': 79.99,
                'stock': 65,
                'sku': 'FS-COCKTAIL-001',
                'expected_delivery_time': '30-60 mins'
            },
            {
                'category': 'Frozen Seafood',
                'name': 'Frozen Fish Cutlets',
                'description': 'Pre-cut frozen fish cutlets. Ready for frying or baking. 600g per pack (8-10 pieces).',
                'price': 59.99,
                'discount_price': 49.99,
                'stock': 75,
                'sku': 'FS-CUTLETS-001',
                'expected_delivery_time': '30-60 mins'
            },
        ]

        # Image and Video URLs
        image_url = "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSVhsoE3HLZUu5LI2Cvm9FbY7GVpKh-IV3wgg&s"
        video_url = "https://in.pinterest.com/pin/898397825668040705/"

        # Create products
        created_count = 0
        for product_data in products_data:
            category_obj = subcategories[product_data.pop('category')]
            
            product, created = Product.objects.get_or_create(
                sku=product_data['sku'],
                defaults={
                    'category': category_obj,
                    'slug': slugify(product_data['name']),
                    'is_available': True,
                    **product_data
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created product: {product.name} ({product.sku})')
                )
                
                # Add product image
                try:
                    response = requests.get(image_url, timeout=10)
                    if response.status_code == 200:
                        img_content = ContentFile(response.content, name=f'{product.sku}_image.jpg')
                        ProductImage.objects.get_or_create(
                            product=product,
                            defaults={
                                'image': img_content,
                                'is_feature': True
                            }
                        )
                        self.stdout.write(
                            self.style.SUCCESS(f'  ├─ Added image for {product.name}')
                        )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  ├─ Could not download image for {product.name}: {str(e)}')
                    )
                
                # Add product video
                try:
                    ProductVideo.objects.get_or_create(
                        product=product,
                        defaults={
                            'video_url': video_url,
                            'title': f'{product.name} - Product Video'
                        }
                    )
                    self.stdout.write(
                        self.style.SUCCESS(f'  └─ Added video for {product.name}')
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.WARNING(f'  └─ Could not add video for {product.name}: {str(e)}')
                    )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Product already exists: {product.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\n✓ Completed! Created {created_count} new marine products with images and videos.')
        )
