# Generated manually for transaction status tracking

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='transaction',
            name='status',
            field=models.CharField(choices=[('ACTIVE', 'Active'), ('REVERTED', 'Reverted')], default='ACTIVE', max_length=10),
        ),
        migrations.AddField(
            model_name='transaction',
            name='original_transaction',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='myapp.transaction'),
        ),
    ]