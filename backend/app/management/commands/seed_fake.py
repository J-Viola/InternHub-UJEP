import random

from django.contrib.auth.hashers import make_password
from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from department.models import Department
from practices.models import Practice, ProgressStatus
from student_practices.models import DocumentHelper, StudentPractice
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
    UserSubject,
    UserSubjectType,
)


class Command(BaseCommand):
    help = "Vygeneruje náhodná (fake) data pro testování zátěže a UI."

    def add_arguments(self, parser):
        parser.add_argument("--students", type=int, default=10, help="Počet studentů k vytvoření")
        parser.add_argument("--companies", type=int, default=5, help="Počet firem k vytvoření")
        parser.add_argument("--practices", type=int, default=20, help="Počet praxí k vytvoření")
        parser.add_argument("--applications", type=int, default=15, help="Počet přihlášek k vytvoření")

    def handle(self, *args, **options):
        self.stdout.write("Zahajuji generování fake dat...")

        # Inicializace Faker s českou lokalizací
        fake = Faker("cs_CZ")
        hashed_password = make_password("demodemo")

        # Ověření prerekvizit (musí existovat základní číselníky)
        try:
            student_role = StagRole.objects.get(role="st")
            teacher_role = StagRole.objects.get(role="vy")
        except StagRole.DoesNotExist:
            self.stdout.write(self.style.ERROR("Chybí role 'st' nebo 'vy'. Nejdříve spusťte 'python manage.py seed_db'."))
            return

        # 0. Generování Profesora (Vyučujícího) a Kateder
        self.stdout.write(" - Generuji Profesory a Katedry...")

        ki_dept, _ = Department.objects.get_or_create(
            department_name="Katedra informatiky",
            defaults={"department_code": "KI", "description": "KI PřF UJEP"},
        )

        kg_dept, _ = Department.objects.get_or_create(
            department_name="Katedra geografie",
            defaults={"department_code": "KG", "description": "KG PřF UJEP"},
        )

        professor = ProfessorUser.objects.filter(email="professor@ujep.cz").first()
        if not professor:
            professor = ProfessorUser.objects.create(
                email="professor@ujep.cz",
                password=hashed_password,
                first_name="Petr",
                last_name="Vomáčka",
                username="professor@ujep.cz",
                is_active=True,
                stag_role=teacher_role,
                department=ki_dept,  # POUŽIJEME NOVĚ VYTVOŘENOU KATEDRU
                department_role=DepartmentRole.HEAD,  # VK - Vedení katedry
                ucit_idno=fake.unique.numerify(text="######"),
            )
            self.stdout.write("   + Vytvořen Vedoucí katedry: professor@ujep.cz")
        else:
            professor.password = hashed_password
            professor.department = ki_dept  # AKTUALIZUJEME KATEDRU NA TU NOVOU
            professor.department_role = DepartmentRole.HEAD
            professor.save()

        # Omezíme předměty na 2 hlavní
        StudentPractice.objects.all().delete()
        Practice.objects.all().delete()
        Subject.objects.all().delete()  # Vyčistíme pro konzistenci

        subj1 = Subject.objects.create(
            subject_name="Odborná praxe 1",
            subject_code="OP1",
            department=ki_dept,
            subject_manager=professor,
            hours_required=160,
        )
        subj2 = Subject.objects.create(
            subject_name="Terénní praxe",
            subject_code="TP",
            department=kg_dept,
            subject_manager=professor,  # Stejný prof pro testování obou kateder
            hours_required=80,
        )
        subjects = [subj1, subj2]

        for subj in subjects:
            UserSubject.objects.get_or_create(
                user=professor,
                subject=subj,
                defaults={"role": UserSubjectType.Professor},
            )

        # 1. Generování Studentů
        count_students = options["students"]
        self.stdout.write(f" - Generuji {count_students} studentů...")

        created_students = []
        for i in range(count_students):
            email = fake.unique.email()
            # Střídáme studenty mezi KI a KG katedrou (sudí/lichí)
            is_ki = i % 2 == 0
            field = "Informatika" if is_ki else "Geografie"
            target_subj = subj1 if is_ki else subj2

            student = StudentUser.objects.create(
                email=email,
                password=hashed_password,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                username=email,
                is_active=True,
                stag_role=student_role,
                os_cislo=fake.unique.bothify(text="??######").upper(),
                field_of_study=field,
                year_of_study=random.randint(1, 5),
                city=fake.city(),
                street=fake.street_name(),
                street_number=fake.building_number(),
                zip_code=fake.postcode().replace(" ", ""),
            )
            created_students.append(student)

            # KLÍČOVÉ: Propojíme studenta s konkrétním předmětem katedry
            UserSubject.objects.create(user=student, subject=target_subj, role=UserSubjectType.Student)

        # 2. Generování Firem a jejich Uživatelů
        count_companies = options["companies"]
        self.stdout.write(f" - Generuji {count_companies} firem...")

        created_profiles = []
        for _ in range(count_companies):
            comp_name = fake.company()
            ico = fake.unique.numerify(text="########")

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

            email_comp = fake.unique.company_email()
            OrganizationUser.objects.create(
                email=email_comp,
                password=hashed_password,
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                is_active=True,
                employer_profile=profile,
                organization_role=OrganizationRole.OWNER,
            )

        # 3. Generování Praxí (Nabídek)
        count_practices = options["practices"]
        created_practices = []

        if not created_profiles:
            created_profiles = list(EmployerProfile.objects.all())

        if not created_profiles or not subjects:
            self.stdout.write(self.style.WARNING("Nedostatek firem nebo předmětů pro generování praxí."))
        else:
            self.stdout.write(f" - Generuji {count_practices} praxí...")
            for _ in range(count_practices):
                profile = random.choice(created_profiles)
                contact_user = profile.organization_users.first()

                practice = Practice.objects.create(
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
                created_practices.append(practice)

        # 4. Generování Přihlášek (StudentPractice)
        count_apps = options["applications"]
        if created_students and created_practices:
            self.stdout.write(f" - Generuji {count_apps} přihlášek...")
            for _ in range(count_apps):
                student = random.choice(created_students)
                practice = random.choice(created_practices)

                # Zabráníme duplicitám
                if StudentPractice.objects.filter(user=student, practice=practice).exists():
                    continue

                # Náhodný stav přihlášky
                rand = random.random()
                if rand < 0.4:  # 40% PENDING
                    app_status = ApprovalStatus.PENDING
                    prog_status = ProgressStatus.NOT_STARTED
                    school_app = False
                    emp_app = False
                elif rand < 0.8:  # 40% APPROVED
                    app_status = ApprovalStatus.APPROVED
                    prog_status = ProgressStatus.IN_PROGRESS
                    school_app = True
                    emp_app = True
                else:  # 20% REJECTED
                    app_status = ApprovalStatus.REJECTED
                    prog_status = ProgressStatus.NOT_STARTED
                    school_app = False
                    emp_app = False

                student_practice = StudentPractice.objects.create(
                    user=student,
                    practice=practice,
                    application_date=timezone.now().date() - timezone.timedelta(days=random.randint(1, 10)),
                    approval_status=app_status,
                    progress_status=prog_status,
                    school_approved=school_app,
                    employer_approved=emp_app,
                    start_date=practice.start_date,
                    end_date=practice.end_date,
                    hours_completed=random.randint(0, 50) if prog_status == ProgressStatus.IN_PROGRESS else 0,
                )

                # Přiřadíme defaultní dokumenty
                DocumentHelper.assign_default_documents(student_practice)

        self.stdout.write(
            self.style.SUCCESS(
                f"Hotovo! Vytvořeno: {count_students} studentů, {count_companies} firem, {count_practices} praxí, {count_apps} přihlášek."
            )
        )
