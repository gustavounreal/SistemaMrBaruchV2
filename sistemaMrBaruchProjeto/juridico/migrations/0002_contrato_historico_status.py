# Generated manually for timeline feature
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('juridico', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='contrato',
            name='historico_status',
            field=models.JSONField(blank=True, default=list, help_text='Histórico de mudanças de status com timestamps'),
        ),
    ]
