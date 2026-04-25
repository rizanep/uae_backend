# Products API Reference

**Base URL:** `https://simakfresh.ae/api/products/`

---

## Table of Contents

- [Authentication & Permissions](#authentication--permissions)
- [Categories](#categories)
- [Products](#products)
- [Product Images (Gallery)](#product-images-gallery)
- [Product Videos](#product-videos)
- [Discount Tiers (Quantity-Based Pricing)](#discount-tiers)
- [Delivery Tiers (Quantity-Based Delivery Estimates)](#delivery-tiers)
- [Admin Dashboard Endpoint](#admin-dashboard)
- [Filtering, Searching & Ordering](#filtering-searching--ordering)

---

## Authentication & Permissions

| Role | Read (GET) | Write (POST/PUT/PATCH/DELETE) |
|------|-----------|-------------------------------|
| **Public / Any User** | ✅ Products, Categories, Images, Videos | ❌ |
| **Admin (is_staff)** | ✅ All | ✅ All |
| **Discount Tiers & Delivery Tiers** | Admin only | Admin only |

**Auth Header:** `Authorization: Bearer <access_token>`

---

## Categories

### List Categories
```
GET /api/products/categories/
```

**Query Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `search` | string | Search by `name` or `description` |
| `name` | string | Exact match |
| `slug` | string | Exact match |
| `parent` | int/null | Filter by parent category ID. Use `null` for top-level |

**Response:**
```json
{
  "count": 5,
  "results": [
    {
      "id": 1,
      "name": "Marine Products",
      "slug": "marine-products",
      "description": "Fresh seafood and marine products",
      "image": "/media/categories/marine.jpg",
      "parent": null
    }
  ]
}
```

### Create Category (Admin)
```
POST /api/products/categories/
Content-Type: multipart/form-data
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | ✅ | Max 100 chars |
| `description` | string | ❌ | |
| `image` | file | ❌ | Image file upload |
| `parent` | int | ❌ | Parent category ID for subcategories |

> `slug` is auto-generated from `name`.

### Update Category (Admin)
```
PUT /api/products/categories/{id}/
PATCH /api/products/categories/{id}/
Content-Type: multipart/form-data
```
Same fields as create. Use `PATCH` for partial updates.

### Delete Category (Admin — Soft Delete)
```
DELETE /api/products/categories/{id}/
```
Sets `deleted_at` timestamp. Category is hidden from public lists but preserved in the database.

---

## Products

### List Products
```
GET /api/products/products/
```

**Query Parameters:**
| Param | Type | Description | Example |
|-------|------|-------------|---------|
| `search` | string | Search in `name`, `description`, `sku` | `?search=hammour` |
| `category` | int | Filter by category ID | `?category=3` |
| `category_slug` | string | Filter by category slug | `?category_slug=fresh-fish` |
| `min_price` | decimal | Minimum price | `?min_price=50` |
| `max_price` | decimal | Maximum price | `?max_price=200` |
| `is_available` | bool | Availability filter | `?is_available=true` |
| `available_emirates` | string | Comma-separated emirate slugs (matches products available in ANY listed emirate) | `?available_emirates=dubai,sharjah` |
| `ordering` | string | Sort by field (prefix `-` for descending) | `?ordering=-price` |
| `limit` | int | Page size (default: 10) | `?limit=20` |
| `offset` | int | Pagination offset | `?offset=20` |

**Ordering fields:** `price`, `created_at`, `stock`

**Response:**
```json
{
  "count": 30,
  "next": "https://simakfresh.ae/api/products/products/?limit=10&offset=10",
  "results": [
    {
      "id": 15,
      "category": 3,
      "category_name": "Fresh Fish",
      "name": "Hammour Fillet",
      "slug": "hammour-fillet",
      "description": "Fresh local hammour fillet, boneless",
      "price": "120.00",
      "discount_price": "99.00",
      "final_price": "99.00",
      "stock": 50,
      "is_available": true,
      "image": "/media/products/hammour.jpg",
      "sku": "FH-HAMMOUR-001",
      "unit": "kg",
      "available_emirates": ["abu_dhabi", "dubai", "sharjah", "ajman", "umm_al_quwain", "ras_al_khaimah", "fujairah"],
      "expected_delivery_time": "Next Day",
      "images": [
        {
          "id": 1,
          "image": "/media/products/gallery/hammour-side.jpg",
          "is_feature": true,
          "created_at": "2026-03-15T10:30:00Z"
        }
      ],
      "videos": [
        {
          "id": 1,
          "video_file": null,
          "video_url": "https://youtube.com/watch?v=example",
          "title": "Hammour Preparation Guide",
          "created_at": "2026-03-15T10:30:00Z"
        }
      ],
      "delivery_tiers": [
        { "id": 1, "product": 15, "min_quantity": 1, "delivery_days": 1 },
        { "id": 2, "product": 15, "min_quantity": 10, "delivery_days": 3 }
      ],
      "discount_tiers": [
        { "id": 1, "product": 15, "min_quantity": 5, "discount_percentage": "5.00" },
        { "id": 2, "product": 15, "min_quantity": 20, "discount_percentage": "10.00" }
      ],
      "average_rating": 4.5,
      "total_reviews": 12,
      "created_at": "2026-03-15T10:30:00Z",
      "updated_at": "2026-04-01T08:00:00Z"
    }
  ]
}
```

### Get Single Product
```
GET /api/products/products/{id}/
```

### Create Product (Admin)
```
POST /api/products/products/
Content-Type: multipart/form-data
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `category` | int | ✅ | Category ID |
| `name` | string | ✅ | Max 255 chars |
| `description` | string | ✅ | |
| `price` | decimal | ✅ | Original price |
| `discount_price` | decimal | ❌ | Sale price. If set, `final_price` = `discount_price` |
| `stock` | int | ❌ | Default: 0 |
| `is_available` | bool | ❌ | Default: true |
| `image` | file | ❌ | Main product image (uploaded to `media/products/`) |
| `unit` | string | ❌ | `piece` (default), `kg`, or `g` |
| `available_emirates` | JSON array | ❌ | Default: all 7 emirates. Example: `["dubai", "sharjah"]` |
| `expected_delivery_time` | string | ❌ | e.g. `"Next Day"`, `"2-3 Days"` |

> `slug` and `sku` are auto-generated from `name`. SKU format: slugified name, truncated to 40 chars, with `-N` suffix if duplicates exist.

### Update Product (Admin)
```
PUT /api/products/products/{id}/
PATCH /api/products/products/{id}/
Content-Type: multipart/form-data
```

**Example — Update price and stock:**
```json
PATCH /api/products/products/15/
{
  "price": "130.00",
  "discount_price": "110.00",
  "stock": 75
}
```

**Example — Update main image:**
```
PATCH /api/products/products/15/
Content-Type: multipart/form-data

image: <file>
```

**Example — Change available emirates:**
```json
PATCH /api/products/products/15/
{
  "available_emirates": ["dubai", "abu_dhabi"]
}
```

### Delete Product (Admin — Soft Delete)
```
DELETE /api/products/products/{id}/
```

---

## Product Images (Gallery)

Each product can have multiple gallery images in addition to its main `image` field. Gallery images are returned nested inside the product response under `"images"`.

### List All Images
```
GET /api/products/product-images/
```

**Filter Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `product` | int | Filter by product ID |
| `is_feature` | bool | Filter featured images |

**Example — Get all images for product 15:**
```
GET /api/products/product-images/?product=15
```

### Get Single Image
```
GET /api/products/product-images/{id}/
```

### Add Image to Product (Admin)
```
POST /api/products/product-images/
Content-Type: multipart/form-data
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `product` | int | ✅ | Product ID |
| `image` | file | ✅ | Image file (uploaded to `media/products/gallery/`) |
| `is_feature` | bool | ❌ | Default: false. Mark as featured/hero image |

**cURL Example:**
```bash
curl -X POST https://simakfresh.ae/api/products/product-images/ \
  -H "Authorization: Bearer <token>" \
  -F "product=15" \
  -F "image=@/path/to/photo.jpg" \
  -F "is_feature=true"
```

### Update Image (Admin)
```
PATCH /api/products/product-images/{id}/
Content-Type: multipart/form-data
```

**Replace the image file:**
```bash
curl -X PATCH https://simakfresh.ae/api/products/product-images/5/ \
  -H "Authorization: Bearer <token>" \
  -F "image=@/path/to/new-photo.jpg"
```

**Toggle featured status:**
```json
PATCH /api/products/product-images/5/
{
  "is_feature": true
}
```

### Delete Image (Admin)
```
DELETE /api/products/product-images/{id}/
```
> This is a **hard delete** — the image record and file are permanently removed.

---

## Product Videos

Each product can have multiple videos — either uploaded files or external URLs (YouTube, Vimeo, etc.). Videos are returned nested inside the product response under `"videos"`.

### List All Videos
```
GET /api/products/product-videos/
```

**Filter Parameters:**
| Param | Type | Description |
|-------|------|-------------|
| `product` | int | Filter by product ID |
| `title` | string | Exact title match |
| `video_url` | string | Exact URL match |

**Example — Get all videos for product 15:**
```
GET /api/products/product-videos/?product=15
```

### Add Video to Product (Admin)

**Option A — Upload a video file:**
```
POST /api/products/product-videos/
Content-Type: multipart/form-data
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `product` | int | ✅ | Product ID |
| `video_file` | file | ❌ | Video file (uploaded to `media/products/videos/`) |
| `video_url` | URL | ❌ | External video link (YouTube, Vimeo, etc.) |
| `title` | string | ❌ | Video title, max 100 chars |

> Provide either `video_file` OR `video_url` (or both).

**cURL — Upload file:**
```bash
curl -X POST https://simakfresh.ae/api/products/product-videos/ \
  -H "Authorization: Bearer <token>" \
  -F "product=15" \
  -F "video_file=@/path/to/video.mp4" \
  -F "title=Product Demo"
```

**Option B — Add external URL:**
```json
POST /api/products/product-videos/
{
  "product": 15,
  "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "title": "How to prepare Hammour"
}
```

### Update Video (Admin)
```
PATCH /api/products/product-videos/{id}/
```

**Replace video file:**
```bash
curl -X PATCH https://simakfresh.ae/api/products/product-videos/3/ \
  -H "Authorization: Bearer <token>" \
  -F "video_file=@/path/to/new-video.mp4"
```

**Change URL or title:**
```json
PATCH /api/products/product-videos/3/
{
  "video_url": "https://youtube.com/watch?v=new-video",
  "title": "Updated Title"
}
```

### Delete Video (Admin)
```
DELETE /api/products/product-videos/{id}/
```
> **Hard delete** — permanently removes the video record and file.

---

## Discount Tiers

Quantity-based percentage discounts. When a customer buys ≥ `min_quantity` items, the per-unit price is reduced by `discount_percentage`%.

**Admin only** — not publicly readable.

### How pricing works:
1. Start with `product.final_price` (= `discount_price` if set, else `price`)
2. Find the highest `ProductDiscountTier` where `min_quantity ≤ ordered_quantity`
3. Apply: `unit_price = final_price - (final_price × discount_percentage / 100)`

**Example:** Product price = 100 AED
| Tier | min_quantity | discount_percentage | Customer buys 25 → |
|------|-------------|--------------------|----|
| 1 | 5 | 5% | |
| 2 | 20 | 10% | ✅ This tier applies → 90 AED/unit |
| 3 | 50 | 15% | |

### List Discount Tiers (Admin)
```
GET /api/products/discount-tiers/
GET /api/products/discount-tiers/?product=15
```

### Create Discount Tier (Admin)
```json
POST /api/products/discount-tiers/
{
  "product": 15,
  "min_quantity": 10,
  "discount_percentage": "5.00"
}
```

### Update Discount Tier (Admin)
```json
PATCH /api/products/discount-tiers/{id}/
{
  "discount_percentage": "7.50"
}
```

### Delete Discount Tier (Admin)
```
DELETE /api/products/discount-tiers/{id}/
```

---

## Delivery Tiers

Quantity-based delivery time estimates. Higher quantities may require longer delivery times.

**Admin only** — not publicly readable. Delivery tier data is included in product responses for reference.

### List Delivery Tiers (Admin)
```
GET /api/products/delivery-tiers/
GET /api/products/delivery-tiers/?product=15
```

### Create Delivery Tier (Admin)
```json
POST /api/products/delivery-tiers/
{
  "product": 15,
  "min_quantity": 1,
  "delivery_days": 1
}
```

### Update Delivery Tier (Admin)
```json
PATCH /api/products/delivery-tiers/{id}/
{
  "delivery_days": 3
}
```

### Delete Delivery Tier (Admin)
```
DELETE /api/products/delivery-tiers/{id}/
```

---

## Admin Dashboard

### Product Counts (Admin)
```
GET /api/products/products/products_count/
Authorization: Bearer <admin_token>
```

**Response:**
```json
{
  "total_products": 30,
  "active": 28,
  "out_of_stock": 2,
  "low_stock": 5
}
```

---

## Filtering, Searching & Ordering

### Quick Reference

| Endpoint | Search Fields | Filter Fields | Ordering Fields |
|----------|--------------|---------------|-----------------|
| `/categories/` | `name`, `description` | `id`, `name`, `slug`, `parent`, `created_at`, `updated_at`, `deleted_at` | — |
| `/products/` | `name`, `description`, `sku` | `category`, `category_slug`, `is_available`, `min_price`, `max_price`, `available_emirates` | `price`, `created_at`, `stock` |
| `/product-images/` | — | `id`, `product`, `is_feature`, `created_at` | — |
| `/product-videos/` | — | `id`, `product`, `video_url`, `title`, `created_at` | — |

### Combined Filtering Example
```
GET /api/products/products/?category_slug=fresh-fish&min_price=50&max_price=200&ordering=-price&search=fillet&available_emirates=dubai&limit=20
```

---

## Emirate Slugs Reference

Use these values for `available_emirates`:

| Slug | Emirate |
|------|---------|
| `abu_dhabi` | Abu Dhabi |
| `dubai` | Dubai |
| `sharjah` | Sharjah |
| `ajman` | Ajman |
| `umm_al_quwain` | Umm Al Quwain |
| `ras_al_khaimah` | Ras Al Khaimah |
| `fujairah` | Fujairah |

---

## File Storage

| Content | Upload Path | Access URL |
|---------|------------|------------|
| Main product image | `media/products/` | `/media/products/filename.jpg` |
| Gallery images | `media/products/gallery/` | `/media/products/gallery/filename.jpg` |
| Video files | `media/products/videos/` | `/media/products/videos/filename.mp4` |
| Category images | `media/categories/` | `/media/categories/filename.jpg` |

---

## Common Workflows

### Add a new product with images and video
```
1. POST /api/products/products/          → Create product (with main image)
2. POST /api/products/product-images/    → Add gallery image 1 (is_feature=true)
3. POST /api/products/product-images/    → Add gallery image 2
4. POST /api/products/product-videos/    → Add YouTube link
5. POST /api/products/discount-tiers/    → Add quantity discount (optional)
6. POST /api/products/delivery-tiers/    → Add delivery estimate (optional)
```

### Replace a product's main image
```
PATCH /api/products/products/{id}/
Content-Type: multipart/form-data
image: <new_file>
```

### Replace a gallery image
```
PATCH /api/products/product-images/{image_id}/
Content-Type: multipart/form-data
image: <new_file>
```

### Remove a gallery image
```
DELETE /api/products/product-images/{image_id}/
```

### Add a YouTube video to a product
```json
POST /api/products/product-videos/
{
  "product": 15,
  "video_url": "https://www.youtube.com/watch?v=VIDEO_ID",
  "title": "Product showcase"
}
```

### Upload a video file
```bash
curl -X POST https://simakfresh.ae/api/products/product-videos/ \
  -H "Authorization: Bearer <token>" \
  -F "product=15" \
  -F "video_file=@video.mp4" \
  -F "title=Demo video"
```

### Set up quantity-based pricing
```json
POST /api/products/discount-tiers/
{"product": 15, "min_quantity": 5, "discount_percentage": "5.00"}

POST /api/products/discount-tiers/
{"product": 15, "min_quantity": 20, "discount_percentage": "10.00"}

POST /api/products/discount-tiers/
{"product": 15, "min_quantity": 50, "discount_percentage": "15.00"}
```
