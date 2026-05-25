# Product Preparation Specification - Quick Reference

## Quick Start

### Admin: Add Preparation Options to Product

1. Go to Django Admin → Products → Products
2. Select a product to edit
3. Scroll to bottom → "Product Preparation Specifications" section
4. Click "Add another Product Preparation Specification"
5. Fill in:
   - **Name**: e.g., "Live (Packed in Air bag)"
   - **Description**: e.g., "Fresh live seafood in protective packaging"
   - **Image**: Upload or select image
   - **Extra Price**: e.g., 0 or 5 (in AED)
   - **Is Active**: Check this
   - **Sort Order**: 1, 2, 3, etc. (lower = displayed first)
6. Repeat for other preparation options
7. Click "Save" at bottom

### Frontend: Display Preparation Options to User

```javascript
// Get preparation specs from product
const product = await fetch(`/api/products/${productId}/`).then(r => r.json());
const preps = product.preparation_specifications;

// Display each option
preps.forEach(prep => {
    console.log(`${prep.name}`);
    console.log(`Extra cost: +${prep.extra_price} AED`);
    console.log(`Description: ${prep.description}`);
    if (prep.image) {
        console.log(`Image: ${prep.image}`);
    }
});
```

### Frontend: User Orders Product with Preparation

```javascript
// User selects:
// - Product: Whole Fish (50 AED)
// - Quantity: 2
// - Preparation: "Whole cleaned headon" (+5 AED)
// - Instructions: "Keep extra ice inside"

const orderData = {
    product_id: 1,
    quantity: 2,
    preparation_specification_id: 2,  // ID of selected prep
    preparation_instructions: "Keep extra ice inside"
};

// Send to backend
const response = await fetch('/api/orders/add-item/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(orderData)
});
```

### Backend: Create Order Item with Preparation

#### Method 1: Using Helper Function

```python
from Products.preparation_utils import OrderItemPreparationHelper

order_item = OrderItemPreparationHelper.create_order_item_with_preparation(
    order=order,
    product=product,
    quantity=2,
    price=Decimal("50.00"),
    prep_spec_id=2,  # ID of preparation specification
    instructions="Keep extra ice inside"
)

# Result:
# - item.price = 50.00 (per unit)
# - item.quantity = 2
# - item.subtotal = 100.00 (50 * 2)
# - item.preparation_extra_price = 5.00
# - item.total_with_preparation = 110.00 (100 + 5*2)
```

#### Method 2: Direct Model Usage

```python
from Products.models import ProductPreparationSpecification

# Get preparation spec
prep_spec = ProductPreparationSpecification.objects.get(id=2)

# Create order item
order_item = OrderItem.objects.create(
    order=order,
    product=product,
    product_name=product.name,
    quantity=2,
    price=Decimal("50.00"),
    preparation_specification=prep_spec,
    preparation_instructions="Keep extra ice inside"
)

# Snapshots are automatically created by save() method:
# - preparation_specification_name = "Whole cleaned headon"
# - preparation_extra_price = 5.00
```

## Price Calculation

**Formula**: `(unit_price × quantity) + (preparation_extra_price × quantity)`

**Example**:
- Product: 50 AED
- Quantity: 2
- Preparation Extra: 5 AED
- Total: (50 × 2) + (5 × 2) = 100 + 10 = **110 AED**

**Helper function**:
```python
from Products.preparation_utils import OrderItemPreparationHelper

total = OrderItemPreparationHelper.calculate_total_with_preparation(
    quantity=2,
    unit_price=Decimal("50.00"),
    prep_extra_price=Decimal("5.00")
)
# Returns: Decimal("110.00")
```

## Viewing Orders with Preparation Info

### In Django Admin

1. Go to Orders
2. Click on an order
3. Scroll to "Order Items" inline section
4. View columns:
   - **Preparation Specification Name**: e.g., "Whole cleaned headon"
   - **Preparation Extra Price**: e.g., 5.00
   - **Total with Preparation**: e.g., 110.00
   - **Preparation Instructions**: e.g., "Keep extra ice inside"

### In API Response

```json
{
  "id": 123,
  "items": [
    {
      "id": 456,
      "product_name": "Whole Fish",
      "quantity": 2,
      "price": "50.00",
      "subtotal": "100.00",
      "preparation_specification": 2,
      "preparation_specification_name": "Whole cleaned headon",
      "preparation_extra_price": "5.00",
      "preparation_instructions": "Keep extra ice inside",
      "total_with_preparation": "110.00"
    }
  ]
}
```

## Common Tasks

### Check if Product Has Preparation Options

```python
from Products.preparation_utils import PreparationSpecificationQueryHelper

has_options = PreparationSpecificationQueryHelper.product_has_preparation_options(product)
if has_options:
    specs = PreparationSpecificationQueryHelper.get_active_specs_for_product(product)
    for spec in specs:
        print(f"{spec.name} - +{spec.extra_price} AED")
```

### Get All Active Preparation Options for Product

```python
from Products.models import ProductPreparationSpecification

specs = ProductPreparationSpecification.objects.filter(
    product=product,
    is_active=True
).order_by('sort_order', 'name')

for spec in specs:
    print(f"{spec.name}: {spec.description}")
    print(f"Extra: {spec.extra_price} AED")
    print(f"Image: {spec.image.url if spec.image else 'None'}")
```

### Update Preparation for Pending Order

```python
from Products.preparation_utils import OrderItemPreparationHelper

order_item = OrderItemPreparationHelper.update_order_item_preparation(
    order_item=order_item,
    prep_spec_id=3,  # New prep spec
    instructions="Changed instructions"
)
```

### Get Preparation Summary

```python
from Products.preparation_utils import OrderItemPreparationHelper

summary = OrderItemPreparationHelper.get_preparation_summary(order_item)
# Returns: {
#     'id': 2,
#     'name': 'Whole cleaned headon',
#     'extra_price': 5.0,
#     'instructions': 'Keep extra ice inside',
#     'subtotal_base': 100.0,
#     'subtotal_preparation': 10.0,
#     'total': 110.0
# }
```

### Get Orders with Custom Preparation Instructions

```python
from Products.preparation_utils import PreparationSpecificationQueryHelper
from datetime import datetime, timedelta

# Get orders from last 7 days with custom instructions
seven_days_ago = datetime.now() - timedelta(days=7)

items = PreparationSpecificationQueryHelper.get_orders_with_preparation_instructions(
    start_date=seven_days_ago,
    has_instructions_only=True
)

for item in items:
    print(f"Order {item.order.id}: {item.product.name}")
    print(f"Preparation: {item.preparation_specification_name}")
    print(f"Instructions: {item.preparation_instructions}")
```

## Data Integrity & Snapshots

When an order item is created with a preparation specification, **snapshots** are automatically created:

- **preparation_specification_name**: Name of spec at order time (allows spec to be renamed without affecting order history)
- **preparation_extra_price**: Price at order time (allows price to change without affecting past orders)

**Why?** If admin later updates a prep spec name or price, orders show what was ordered at that time.

## Validation Rules

1. **Preparation is REQUIRED** if product has active preparation specifications
2. **Preparation must belong to the product** being ordered
3. **Preparation must be active** (can't select disabled options)
4. **Instructions are optional** but max 500 characters (if set)
5. **Can't modify orders** in non-PENDING status

## Troubleshooting

### "Preparation specification is required"

**Cause**: Product has active prep options but none was selected

**Fix**: Select a preparation option in the order form

### "Preparation specification does not match product"

**Cause**: Selected prep spec ID doesn't belong to this product

**Fix**: Verify correct product and prep spec ID are being used

### "This preparation option is no longer available"

**Cause**: Admin disabled the preparation option

**Fix**: Select a different active preparation option or ask admin to re-enable

### Price not calculating correctly

**Check**:
```python
# Get the order item
item = OrderItem.objects.get(id=123)

# Check the values
print(f"Unit price: {item.price}")
print(f"Quantity: {item.quantity}")
print(f"Prep extra: {item.preparation_extra_price}")
print(f"Subtotal: {item.subtotal}")
print(f"Total: {item.total_with_preparation}")

# Verify calculation
expected = (item.price * item.quantity) + (item.preparation_extra_price * item.quantity)
print(f"Expected total: {expected}")
```

## Migration & Deployment

Migration file created: `Orders/migrations/0010_orderitem_preparation_extra_price_and_more.py`

**What changed**:
- Added 4 new optional fields to OrderItem
- Existing orders unaffected (fields are NULL)
- No data loss

**Deploy steps**:
```bash
# 1. Create migration
python manage.py makemigrations

# 2. Run migration
python manage.py migrate

# 3. No manual data migration needed - safe to deploy!
```

## API Endpoints

### Get Product with Preparation Specs
```
GET /api/products/{id}/
```

### Create Order with Preparation
```
POST /api/orders/
{
    "items": [
        {
            "product_id": 1,
            "quantity": 2,
            "preparation_specification_id": 2,
            "preparation_instructions": "..."
        }
    ]
}
```

### Get Order Details
```
GET /api/orders/{id}/
```

### List Orders with Preparation
```
GET /api/orders/?has_preparation=true
```

## Next Steps

1. ✅ Add preparation specs to existing products in admin
2. ✅ Update frontend to display prep options
3. ✅ Update order creation API/views to accept prep spec
4. ✅ Test order flow with different prep combinations
5. ✅ Train kitchen staff on viewing preparation instructions
6. ✅ Update order confirmation email/SMS with prep details
