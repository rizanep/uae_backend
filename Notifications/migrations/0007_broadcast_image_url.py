from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("Notifications", "0006_fcmdevice"),
    ]

    operations = [
        migrations.AddField(
            model_name="broadcast",
            name="image",
            field=models.ImageField(
                blank=True,
                null=True,
                help_text="Optional image for PUSH notifications.",
                upload_to="broadcast_images/",
                verbose_name="image",
            ),
        ),
    ]
