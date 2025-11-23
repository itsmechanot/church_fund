# Generated manually for profile picture field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('myapp', '0009_alter_transaction_fund'),
    ]

    operations = [
        migrations.AddField(
            model_name='treasurer',
            name='profile_picture',
            field=models.ImageField(blank=True, null=True, upload_to='profile_pics/'),
        ),
    ]