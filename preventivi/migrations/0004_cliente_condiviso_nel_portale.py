from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('preventivi', '0003_preventivo_cliente_id_portale_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='preventivo',
            name='cliente',
        ),
        migrations.DeleteModel(
            name='Cliente',
        ),
        migrations.RenameField(
            model_name='preventivo',
            old_name='cliente_id_portale',
            new_name='cliente_id',
        ),
        migrations.AlterField(
            model_name='preventivo',
            name='cliente_id',
            field=models.UUIDField(
                help_text="Riferimento al cliente nell'anagrafica condivisa del Portale "
                          "(clienti/api/internal/).",
            ),
        ),
    ]
