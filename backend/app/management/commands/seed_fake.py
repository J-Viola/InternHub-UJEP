import random

from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from department.models import Department
from practices.models import Practice, ProgressStatus
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    DepartmentRole,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    ProfessorUser,
    StagRole,
    StudentUser,
)


class Command(BaseCommand):
    help = "Vygeneruje náhodná (fake) data pro testování zátěže a UI."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=10, help="Počet studentů k vytvoření")
        parser.add_argument("--companies", type=int, default=5, help="Počet firem k vytvoření")
        parser.add_argument("--practices", type=int, default=20, help="Počet praxí k vytvoření")

    def handle(self, *args, **options):
        self.stdout.write("Zahajuji generování fake dat...")

        # Inicializace Faker s českou lokalizací
        fake = Faker("cs_CZ")

        # Ověření prerekvizit (musí existovat základní číselníky)
        try:
            student_role = StagRole.objects.get(role="st")
            teacher_role = StagRole.objects.get(role="vy")
        except StagRole.DoesNotExist:
            self.stdout.write(self.style.ERROR("Chybí role 'st' nebo 'vy'. Nejdříve spusťte 'python manage.py seed_db'."))
            return

        # 0. Generování Profesora (Vyučujícího)
        self.stdout.write(" - Generuji Profesora...")
        department, _ = Department.objects.get_or_create(department_name="Katedra informatiky", defaults={"description": "KI PřF UJEP"})

        if not ProfessorUser.objects.filter(email="professor@ujep.cz").exists():
            ProfessorUser.objects.create(
                email="professor@ujep.cz",
                password="password123",
                first_name="Petr",
                last_name="Vomáčka",
                username="professor@ujep.cz",
                is_active=True,
                stag_role=teacher_role,
                department=department,
                department_role=DepartmentRole.TEACHER,
                ucit_idno=fake.unique.numerify(text="######"),
            )
            self.stdout.write("   + Vytvořen Profesor: professor@ujep.cz")

        # 1. Generování Studentů
        count_students = options["students"]
        self.stdout.write(f" - Generuji {count_students} studentů...")

        for _ in range(count_students):
            # Musíme generovat ručněji, protože django-seed má někdy potíže s Polymorphic a specifickými constraints
            email = fake.unique.email()
            StudentUser.objects.create(
                email=email,
                password="demodemo",  # Všechna hesla stejná pro snadné testování
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                username=email,  # Username často kopíruje email
                is_active=True,
                stag_role=student_role,
                os_cislo=fake.unique.bothify(text="??######").upper(),  # Např. AB123456
                field_of_study="Informatika",
                year_of_study=random.randint(1, 3),
                city=fake.city(),
                street=fake.street_name(),
                street_number=fake.building_number(),
                zip_code=fake.postcode().replace(" ", ""),
            )

        # 2. Generování Firem a jejich Uživatelů
        count_companies = options["companies"]
        self.stdout.write(f" - Generuji {count_companies} firem...")

        created_profiles = []
        for _ in range(count_companies):
            comp_name = fake.company()
            ico = fake.unique.numerify(text="########")

            # Profil firmy
            profile = EmployerProfile.objects.create(
                company_name=comp_name,
                ico=ico,
                dic="CZ" + ico,
                city=fake.city(),
                address=fake.street_address(),
                company_profile=fake.text(max_nb_chars=200),
                approval_status=ApprovalStatus.APPROVED,
            )
            created_profiles.append(profile)

            # Vytvoření uživatele pro firmu (aby měla praxe kontaktní osobu)
            email_comp = fake.unique.company_email()
            OrganizationUser.objects.create(
                email=email_comp,
                password="password123",
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                is_active=True,
                employer_profile=profile,
                organization_role=OrganizationRole.OWNER,
            )

        # 3. Generování Praxí
        count_practices = options["practices"]
        subjects = list(Subject.objects.all())

        if not created_profiles:
            # Pokud jsme nevytvořili firmy teď, zkusíme najít existující
            created_profiles = list(EmployerProfile.objects.all())

        if not created_profiles or not subjects:
            self.stdout.write(self.style.WARNING("Nedostatek firem nebo předmětů pro generování praxí."))
        else:
            self.stdout.write(f" - Generuji {count_practices} praxí...")
            for _ in range(count_practices):
                profile = random.choice(created_profiles)
                # Najdeme kontaktní osobu firmy
                contact_user = profile.organization_users.first()

                Practice.objects.create(
                    employer=profile,
                    subject=random.choice(subjects),
                    title=fake.job(),
                    description=fake.text(max_nb_chars=500),
                    responsibilities=fake.text(max_nb_chars=200),
                    available_positions=random.randint(1, 5),
                    start_date=timezone.now().date() + timezone.timedelta(days=random.randint(10, 30)),
                    end_date=timezone.now().date() + timezone.timedelta(days=random.randint(90, 180)),
                    progress_status=ProgressStatus.NOT_STARTED,
                    approval_status=ApprovalStatus.APPROVED,
                    contact_user=contact_user,
                    is_active=True,
                    coefficient=1.0,
                )

        self.stdout.write(
            self.style.SUCCESS(f"Hotovo! Vytvořeno: {count_students} studentů, {count_companies} firem, {count_practices} praxí.")
        )
