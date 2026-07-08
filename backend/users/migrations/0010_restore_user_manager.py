# Generated manually to fix 0005 which cleared all user managers

import users.models
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_alter_employer_profile_fk'),
    ]

    operations = [
        migrations.AlterModelManagers(
            name='user',
            managers=[
                ('objects', users.models.UserManager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='organizationuser',
            managers=[
                ('objects', users.models.UserManager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='staguser',
            managers=[
                ('objects', users.models.UserManager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='studentuser',
            managers=[
                ('objects', users.models.UserManager()),
            ],
        ),
        migrations.AlterModelManagers(
            name='professoruser',
            managers=[
                ('objects', users.models.UserManager()),
            ],
        ),
    ]
