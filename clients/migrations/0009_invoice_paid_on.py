from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clients', '0008_clientassessment'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='paid_on',
            field=models.DateField(blank=True, null=True),
        ),
    ]
