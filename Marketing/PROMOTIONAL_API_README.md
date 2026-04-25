# Marketing API - Promotional Content

## Overview
The Promotional Content API provides dynamic promotional text for delivery offers and time slots based on current settings and time.

## Endpoints

### Get Delivery Offers
```
GET /api/marketing/promotional/delivery_offers/
```

Returns promotional text for delivery offers including:
- Free delivery threshold amount
- Next available delivery time slot based on current time
- Text available in English, Arabic, and Chinese

**Response Status:** `200 OK`

**Response Example:**
```json
{
  "promotional_texts": {
    "en": {
      "free_delivery": "Purchase for 20.00 AED or above for free delivery",
      "delivery_time": "Purchase before 7:30 AM to get delivery between 8:00 AM - 9:00 AM"
    },
    "ar": {
      "free_delivery": "اشتري بقيمة 20 درهم أو أكثر للحصول على توصيل مجاني",
      "delivery_time": "اشترِ قبل 7:30 AM للحصول على توصيل بين 8:00 AM - 9:00 AM"
    },
    "zh": {
      "free_delivery": "购买满 20 AED 或以上可享免运费",
      "delivery_time": "请在 7:30 AM 前下单，配送时间为 8:00 AM - 9:00 AM"
    }
  },
  "timestamp": "2026-04-19T10:15:30+04:00",
  "timezone": "Asia/Dubai"
}
```

## Features

### Dynamic Free Delivery Text
- Uses the current `DeliveryChargeConfig.min_free_shipping_amount`
- Shows "Purchase for X AED or above for free delivery"
- If delivery charges are disabled, shows "Free delivery on all orders"

### Dynamic Delivery Time Text
- Checks current time in UAE timezone (Asia/Dubai)
- Finds the next available delivery slot based on cutoff times
- Only returns one delivery time text
- If no slots available today, shows tomorrow's first slot
- Format: "Purchase before [cutoff] to get delivery between [start] - [end]"

### Time Zone Handling
- All times are calculated in UAE timezone (GMT+4)
- Uses pytz for accurate timezone conversion
- Respects delivery slot overrides and cutoff times

## Permissions
- **Public endpoint** - No authentication required
- Uses `AllowAny` permission class

## Dependencies
- `DeliveryChargeConfig` from Orders app
- `DeliveryTimeSlot` and `DeliverySlotOverride` from Orders app
- UAE timezone configuration

## Use Cases
- Display promotional banners on website/mobile app
- Show delivery offers in checkout flow
- Dynamic content for marketing campaigns
- Real-time delivery availability messaging