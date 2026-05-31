# Product Preparation Specification Feature

## Overview

The Product Preparation Specification feature allows seafood ecommerce admins to define multiple preparation/packaging options for products. Users must select one preparation option when ordering and can provide custom instructions.

**Features:**
- Admin defines preparation specifications per product (e.g., "Live (Packed in Air bag)", "Whole cleaned headon")
- Each preparation option has name, description, image, and optional extra price
- Users must select a preparation specification when ordering
- Users can add custom preparation instructions
- Order details track the selected preparation option and any custom instructions
- Verification happens at order time

## Database Models

### ProductPreparationSpecification
```python
ProductPreparationSpecification(
    product,                    # ForeignKey to Product
    name,                       # str: "Live (Packed in Air bag)"
    description,                # str: Details about preparation
    image,                      # ImageField: Visual representation
    extra_price,                # Decimal: Additional cost (default 0 AED)
    is_active,                  # bool: Enable/disable this option
    sort_order,                 # int: Display order
    created_at,
    updated_at
)
```

### OrderItem (Updated)
Added fields:
```python
preparation_specification        # ForeignKey to ProductPreparationSpecification (nullable, blank for old orders)
preparation_specification_name   # str: Snapshot of spec name at order time
preparation_extra_price          # Decimal: Extra price at order time
preparation_instructions         # TextField: Custom user instructions
```

## Admin Interface

### Adding Preparation Specifications

1. **Navigate to Product Edit Page**
   - Go to Django Admin > Products
   - Edit a product
   - Scroll to "Product Preparation Specifications" inline section

2. **Add New Specification**
   - Click "Add another Product Preparation Specification"
   - Fill in:
     - **Name**: "Live (Packed in Air bag)"
     - **Description**: "Fresh live seafood packed in protective air bag"
     - **Image**: Upload visual representation
     - **Extra Price**: 0 (or additional cost e.g., 5 AED)
     - **Is Active**: Check to enable
     - **Sort Order**: Lower numbers display first

3. **Save**
   - Click Save Product

### Standalone Preparation Spec Admin
- Navigate to Django Admin > Products > Product Preparation Specifications
- View, add, edit, or delete specifications
- Bulk edit extra_price and is_active
- Search by product name or specification name

### Viewing Preparation Specs in Order Admin
- Navigate to Order details
- Expand "Order Items" inline section
- View:
  - Preparation Specification Name
  - Preparation Extra Price
  - Total with Preparation (qty × price + qty × extra_price)
  - Preparation Instructions

## API Usage

### Get Product with Preparation Specifications

```bash
GET /api/products/{id}/
```

**Response:**
```json
{
  "id": 1,
  "name": "Whole Fish",
  "price": "50.00",
  "preparation_specifications": [
    {
      "id": 1,
      "product": 1,
      "name": "Live (Packed in Air bag)",
      "description": "Fresh live seafood",
      "image": "https://...",
      "extra_price": "0.00",
      "is_active": true,
      "sort_order": 1
    },
    {
      "id": 2,
      "product": 1,
      "name": "Whole cleaned headon",
      "description": "Cleaned but head remains",
      "image": "https://...",
      "extra_price": "5.00",
      "is_active": true,
      "sort_order": 2
    }
  ]
}
```

### Create Order with Preparation Specification

When adding items to cart/creating order, include:

```python
# Example: Order creation with preparation
OrderItem.objects.create(
    order=order,
    product=product,
    product_name=product.name,
    quantity=2,
    price=product.final_price,
    preparation_specification=prep_spec,  # ProductPreparationSpecification instance
    preparation_specification_name=prep_spec.name,  # Snapshot of name
    preparation_extra_price=prep_spec.extra_price,  # Snapshot of price
    preparation_instructions="Please keep them very fresh, packed with extra ice"
)
```

### Get Order Details with Preparation Info

```bash
GET /api/orders/{id}/
```

**Response:**
```json
{
  "id": 123,
  "items": [
    {
      "id": 456,
      "product": 1,
      "product_name": "Whole Fish",
      "quantity": 2,
      "price": "50.00",
      "subtotal": "100.00",
      "preparation_specification": 2,
      "preparation_specification_name": "Whole cleaned headon",
      "preparation_extra_price": "5.00",
      "preparation_instructions": "Please keep them very fresh",
      "total_with_preparation": "110.00"  # 100 + (5 * 2)
    }
  ]
}
```

## Frontend Integration

### Display Preparation Options

When user adds product to cart:

```javascript
// Get active preparation specs
const prepSpecs = product.preparation_specifications.filter(s => s.is_active);

// Display as dropdown/radio buttons
prepSpecs.forEach(spec => {
    console.log(`${spec.name} - +${spec.extra_price} AED`);
    console.log(`Image: ${spec.image}`);
    console.log(`Description: ${spec.description}`);
});
```

### Create Order Item with Preparation

```javascript
// User selects preparation option
const selectedPrepSpec = {
    id: 2,
    name: "Whole cleaned headon",
    extra_price: "5.00"
};

// User enters custom instructions
const customInstructions = "Please keep them very fresh, packed with extra ice";

// Send to backend
POST /api/cart/add/
{
    "product_id": 1,
    "quantity": 2,
    "preparation_specification_id": 2,
    "preparation_instructions": "Please keep them very fresh..."
}
```

### Calculate Total Price

```javascript
// Base price + (extra_price * quantity)
const item = {
    price: 50.00,
    quantity: 2,
    preparation_extra_price: 5.00
};

const subtotal = item.price * item.quantity;  // 100.00
const extra = item.preparation_extra_price * item.quantity;  // 10.00
const total = subtotal + extra;  // 110.00
```

## Validation & Business Logic

### Create OrderItem Validation

Add to your OrderItem model or serializer:

```python
def clean(self):
    """Validate preparation specification is selected."""
    if not self.preparation_specification:
        raise ValidationError({
            'preparation_specification': 'Preparation specification is required.'
        })
    
    # Verify spec belongs to this product
    if self.preparation_specification.product != self.product:
        raise ValidationError({
            'preparation_specification': 'Preparation spec does not match product.'
        })
    
    # Verify spec is active
    if not self.preparation_specification.is_active:
        raise ValidationError({
            'preparation_specification': 'This preparation option is no longer available.'
        })
```

### Save OrderItem with Preparation Snapshot

```python
def save(self, *args, **kwargs):
    """Save snapshots of preparation data at order time."""
    if self.preparation_specification:
        # Store snapshots (for data integrity if spec is later modified)
        self.preparation_specification_name = self.preparation_specification.name
        self.preparation_extra_price = self.preparation_specification.extra_price
    
    super().save(*args, **kwargs)
```

## Order Processing Flow

1. **Product Browse**: Customer sees product with available preparation specs
2. **Cart Add**: Customer selects:
   - Product
   - Quantity
   - **Preparation specification** (REQUIRED)
   - Optional: Custom preparation instructions
3. **Cart Review**: Display:
   - Item price
   - Preparation option selected
   - Extra price
   - Total (item total + extra)
4. **Order Confirmation**: Display all preparation details
5. **Kitchen Processing**: 
   - Staff can see preparation spec and instructions
   - Verify and prepare accordingly

## Examples

### Example 1: Simple Whole Fish Product

**Product Name**: Whole Fish (1 KG)
**Base Price**: 50 AED

**Preparation Specs:**
1. Live (Packed in Air bag) - Extra: 0 AED
2. Whole uncleaned, fresh caught (Packed with ice) - Extra: 0 AED
3. Whole cleaned headon (Packed with ice) - Extra: 5 AED
4. Whole cleaned headless (Packed with ice) - Extra: 3 AED

**Order Example:**
- User orders 2 units
- Selects "Whole cleaned headon" (+5 AED)
- Instructions: "Please remove all scales, keep ice inside"
- Total: (50 × 2) + (5 × 2) = 110 AED

### Example 2: Mixed Preparation Order

Order with 3 different items, each with different prep:

```json
{
  "items": [
    {
      "product": "Whole Fish",
      "quantity": 1,
      "price": 50,
      "prep": "Live (Air bag)",
      "extra": 0,
      "total": 50
    },
    {
      "product": "Fish Fillets",
      "quantity": 2,
      "price": 40,
      "prep": "Deboned fillets",
      "extra": 10,
      "total": 100
    },
    {
      "product": "Shrimp",
      "quantity": 0.5,
      "price": 100,
      "prep": "Cleaned headless",
      "extra": 5,
      "total": 52.50
    }
  ],
  "order_total": 202.50
}
```

## Migration Notes

The migration adds:
- New `ProductPreparationSpecification` table with indexes on (product, is_active)
- Four new optional fields to `OrderItem` table:
  - `preparation_specification` (FK, nullable)
  - `preparation_specification_name` (CharField, blank)
  - `preparation_extra_price` (DecimalField, default 0)
  - `preparation_instructions` (TextField, nullable)

**Backward Compatibility**: Existing orders without preparation specs will have `NULL` values (safe).

## Testing

### Unit Tests Example

```python
def test_create_order_item_with_preparation():
    """Test order item creation with preparation specification."""
    product = Product.objects.create(name="Whole Fish", price=50)
    prep_spec = ProductPreparationSpecification.objects.create(
        product=product,
        name="Live (Air bag)",
        extra_price=0
    )
    order = Order.objects.create(user=user, total_amount=50)
    
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=2,
        price=50,
        preparation_specification=prep_spec,
        preparation_specification_name=prep_spec.name,
        preparation_extra_price=prep_spec.extra_price,
        preparation_instructions="Handle with care"
    )
    
    assert item.total_with_preparation == 100  # 50*2 + 0*2
    assert item.preparation_specification_name == "Live (Air bag)"

def test_preparation_price_calculation():
    """Test total price with preparation extra cost."""
    product = Product.objects.create(name="Whole Fish", price=50)
    prep_spec = ProductPreparationSpecification.objects.create(
        product=product,
        name="Cleaned",
        extra_price=5
    )
    order = Order.objects.create(user=user, total_amount=100)
    
    item = OrderItem.objects.create(
        order=order,
        product=product,
        quantity=2,
        price=50,
        preparation_specification=prep_spec,
        preparation_specification_name=prep_spec.name,
        preparation_extra_price=5
    )
    
    assert item.total_with_preparation == 110  # (50*2) + (5*2)
```

## Admin Tasks Checklist

- [ ] Add preparation specifications to existing products in admin
- [ ] Verify images upload correctly
- [ ] Test extra price calculations
- [ ] Train kitchen staff on viewing instructions
- [ ] Test order creation with preparation specs
- [ ] Update frontend to display prep options
- [ ] Update API documentation
