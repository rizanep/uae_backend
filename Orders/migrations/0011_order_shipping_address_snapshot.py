from django.db import migrations, models


def backfill_shipping_address_snapshot(apps, schema_editor):
    Order = apps.get_model("Orders", "Order")

    for order in Order.objects.select_related("shipping_address").filter(
        shipping_address__isnull=False,
        shipping_address_snapshot__isnull=True,
    ).iterator(chunk_size=500):
        address = order.shipping_address
        if not address:
            continue

        snapshot = {
            "id": str(address.id) if address.id is not None else None,
            "user": address.user_id,
            "label": address.label,
            "address_type": address.address_type,
            "is_default": address.is_default,
            "full_name": address.full_name,
            "phone_number": address.phone_number,
            "building_name": address.building_name,
            "flat_villa_number": address.flat_villa_number,
            "street_address": address.street_address,
            "area": address.area,
            "city": address.city,
            "emirate": address.emirate,
            "postal_code": address.postal_code,
            "country": address.country,
            "latitude": str(address.latitude) if address.latitude is not None else None,
            "longitude": str(address.longitude) if address.longitude is not None else None,
            "created_at": address.created_at.isoformat() if address.created_at else None,
            "updated_at": address.updated_at.isoformat() if address.updated_at else None,
        }

        Order.objects.filter(pk=order.pk).update(shipping_address_snapshot=snapshot)


class Migration(migrations.Migration):

    dependencies = [
        ("Orders", "0010_orderitem_preparation_extra_price_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="order",
            name="shipping_address_snapshot",
            field=models.JSONField(
                blank=True,
                help_text="Frozen copy of shipping address to preserve order history if address is deleted.",
                null=True,
                verbose_name="shipping address snapshot",
            ),
        ),
        migrations.RunPython(backfill_shipping_address_snapshot, migrations.RunPython.noop),
    ]
