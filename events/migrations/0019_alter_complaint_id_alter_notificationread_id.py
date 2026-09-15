import mongo_apps
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0018_complaint'),
    ]

    operations = [
        migrations.AlterField(
            model_name='complaint',
            name='id',
            field=mongo_apps.MongoObjectIdAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name='ID',
            ),
        ),
        migrations.AlterField(
            model_name='notificationread',
            name='id',
            field=mongo_apps.MongoObjectIdAutoField(
                auto_created=True,
                primary_key=True,
                serialize=False,
                verbose_name='ID',
            ),
        ),
    ]