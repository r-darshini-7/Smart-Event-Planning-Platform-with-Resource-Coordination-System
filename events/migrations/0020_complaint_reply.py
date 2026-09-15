import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0019_alter_complaint_id_alter_notificationread_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='complaint',
            name='reply',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='complaint',
            name='replied_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='complaint',
            name='replied_by',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='replied_complaints',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]