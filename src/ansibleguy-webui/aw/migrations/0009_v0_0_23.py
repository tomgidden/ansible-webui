# Generated by Django 5.0.7 on 2024-07-15 14:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("aw", "0008_v0_0_22"),
    ]

    operations = [
        migrations.AlterField(
            model_name="job",
            name="execution_prompts",
            field=models.CharField(default="limit,mode_check,tags", max_length=5000),
        ),
    ]
