from django.db import migrations, models
import django.db.models.deletion


DEFAULT_UNITS = ["piece", "kg", "100g"]


def seed_product_units(apps, schema_editor):
    Product = apps.get_model("Products", "Product")
    ProductUnit = apps.get_model("Products", "ProductUnit")

    unit_id_by_name = {}
    for index, name in enumerate(DEFAULT_UNITS):
        unit, _ = ProductUnit.objects.get_or_create(
            name=name,
            defaults={"sort_order": index, "is_active": True},
        )
        unit_id_by_name[name] = unit.id

    existing_units = (
        Product.objects.exclude(unit__isnull=True)
        .exclude(unit__exact="")
        .values_list("unit", flat=True)
        .distinct()
    )
    next_sort_order = ProductUnit.objects.count()
    for name in existing_units:
        if name in unit_id_by_name:
            continue
        unit, _ = ProductUnit.objects.get_or_create(
            name=name,
            defaults={"sort_order": next_sort_order, "is_active": True},
        )
        unit_id_by_name[name] = unit.id
        next_sort_order += 1

    for name, unit_id in unit_id_by_name.items():
        Product.objects.filter(unit=name).update(unit_option_id=unit_id)


class Migration(migrations.Migration):

    dependencies = [
        ("Products", "0017_alter_product_unit"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductUnit",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=50, unique=True, verbose_name="name")),
                ("is_active", models.BooleanField(default=True, verbose_name="is active")),
                ("sort_order", models.PositiveIntegerField(default=0, verbose_name="sort order")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Product Unit",
                "verbose_name_plural": "Product Units",
                "ordering": ["sort_order", "name"],
            },
        ),
        migrations.AddField(
            model_name="product",
            name="unit_option",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="products", to="Products.productunit", verbose_name="unit option"),
        ),
        migrations.AlterField(
            model_name="product",
            name="unit",
            field=models.CharField(default="piece", max_length=50, verbose_name="unit"),
        ),
        migrations.RunPython(seed_product_units, migrations.RunPython.noop),
    ]
