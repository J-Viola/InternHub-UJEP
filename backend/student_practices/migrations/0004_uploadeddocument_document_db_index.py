from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("student_practices", "0003_alter_studentpractice_content_document_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="uploadeddocument",
            name="document",
            field=models.FileField(
                blank=True, db_index=True, null=True, upload_to="documents"
            ),
        ),
    ]
