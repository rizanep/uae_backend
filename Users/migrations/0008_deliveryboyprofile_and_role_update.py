from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('Users', '0007_alter_userprofile_preferred_language'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryBoyProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('assigned_emirates', models.JSONField(blank=True, default=list, help_text='List of emirate keys assigned to this delivery boy.')),
                ('is_available', models.BooleanField(default=True)),
                ('identity_number', models.CharField(blank=True, max_length=100, null=True)),
                ('vehicle_number', models.CharField(blank=True, max_length=50, null=True)),
                ('emergency_contact', models.CharField(blank=True, max_length=20, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='delivery_profile', to='Users.user', verbose_name='delivery boy user')),
            ],
            options={
                'verbose_name': 'Delivery Boy Profile',
                'verbose_name_plural': 'Delivery Boy Profiles',
                'db_table': 'delivery_boy_profiles',
            },
        ),
        migrations.AlterField(
            model_name='user',
            name='role',
            field=models.CharField(choices=[('admin', 'Admin'), ('user', 'User'), ('delivery_boy', 'Delivery Boy')], db_index=True, default='user', max_length=20, verbose_name='role'),
        ),
    ]
