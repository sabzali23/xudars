from django.db import migrations, models


def fill_placeholder(apps, schema_editor):
    """Заглушка для уже загруженных материалов; настоящий текст подставит `manage.py load_content`."""
    Material = apps.get_model("curriculum", "Material")
    Material.objects.filter(parent_guide_md="").update(
        parent_guide_md="Руководство для родителя ещё не загружено. Выполните manage.py load_content.",
        parent_guide_html="<p>Руководство для родителя ещё не загружено.</p>",
    )


class Migration(migrations.Migration):
    dependencies = [
        ("curriculum", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="material",
            name="parent_guide_md",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="material",
            name="parent_guide_html",
            field=models.TextField(default=""),
            preserve_default=False,
        ),
        migrations.RunPython(fill_placeholder, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="material",
            constraint=models.CheckConstraint(
                condition=~models.Q(parent_guide_md=""), name="material_parent_guide_required"
            ),
        ),
    ]
