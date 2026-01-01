import random
from datetime import date, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction

from department.models import Department
from practices.models import Practice, ProgressStatus
from subject.models import Subject
from users.models import (
    ApprovalStatus,
    EmployerProfile,
    OrganizationRole,
    OrganizationUser,
    StagRole,
    User,
)


class Command(BaseCommand):
    help = "Naplní databázi testovacími daty (Role, Firmy, Praxe, Uživatelé)"

    def handle(self, *args, **kwargs):
        self.stdout.write("Zahajuji seedování dat...")

        try:
            with transaction.atomic():
                self.seed_stag_roles()
                dept = self.seed_department()
                subjects = self.seed_subjects(dept)
                self.seed_superuser()
                self.seed_companies_and_practices(subjects)

            self.stdout.write(self.style.SUCCESS("Seedování úspěšně dokončeno!"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Chyba při seedování: {e}"))
            # V debug módu vypíšeme celý traceback, pokud chcete
            import traceback

            traceback.print_exc()

    def seed_stag_roles(self):
        self.stdout.write(" - Kontrola STAG rolí...")
        roles = [
            {"role": "st", "role_name": "Student", "description": "Student VŠ"},
            {
                "role": "vy",
                "role_name": "Vyučující",
                "description": "Vyučující na katedře",
            },
            {
                "role": "vk",
                "role_name": "Vedení katedry",
                "description": "Vedoucí nebo tajemník",
            },
        ]

        for data in roles:
            obj, created = StagRole.objects.get_or_create(
                role=data["role"],
                defaults={
                    "role_name": data["role_name"],
                    "description": data["description"],
                },
            )
            if created:
                self.stdout.write(f"   + Vytvořena role: {data['role_name']}")

    def seed_department(self):
        self.stdout.write(" - Kontrola Katedry...")
        dept, created = Department.objects.get_or_create(
            department_name="Katedra informatiky",
            defaults={"description": "KI PřF UJEP"},
        )
        if created:
            self.stdout.write("   + Vytvořena Katedra informatiky")
        return dept

    def seed_subjects(self, department):
        self.stdout.write(" - Kontrola Předmětů...")
        subjects_data = [
            {"code": "KI/PRAX1", "name": "Odborná praxe 1", "hours": 100},
            {"code": "KI/PRAX2", "name": "Odborná praxe 2", "hours": 150},
            {"code": "KI/BAKP", "name": "Bakalářská práce", "hours": 300},
        ]

        created_subjects = []
        for data in subjects_data:
            subj, created = Subject.objects.get_or_create(
                subject_code=data["code"],
                defaults={
                    "subject_name": data["name"],
                    "department": department,
                    "hours_required": data["hours"],
                },
            )
            if created:
                self.stdout.write(f"   + Vytvořen předmět: {data['name']}")
            created_subjects.append(subj)
        return created_subjects

    def seed_superuser(self):
        email = "admin@admin.com"
        if not User.objects.filter(email=email).exists():
            User.objects.create_superuser(
                email=email,
                password="demodemo",
                first_name="Hlavní",
                last_name="Administrátor",
                is_active=True,
            )
            self.stdout.write(f"   + Vytvořen Superuser: {email} (heslo: demodemo)")

    def seed_companies_and_practices(self, subjects):
        companies = [
            {
                "name": "TechCorp s.r.o.",
                "ico": "12345678",
                "email": "hr@techcorp.cz",
                "desc": "Vývoj softwaru a cloudová řešení.",
                "practices": [
                    {
                        "title": "Junior Python Developer",
                        "desc": "Vývoj backendu v Djangu.",
                    },
                    {"title": "React Frontend Trainee", "desc": "Tvorba UI komponent."},
                ],
            },
            {
                "name": "SoftVision a.s.",
                "ico": "87654321",
                "email": "jobs@softvision.cz",
                "desc": "Konzultace a enterprise systémy.",
                "practices": [
                    {
                        "title": "Java Enterprise Intern",
                        "desc": "Práce na bankovních systémech.",
                    },
                    {
                        "title": "Tester Automation",
                        "desc": "Psaní automatizovaných testů v Seleniu.",
                    },
                ],
            },
            {
                "name": "DataSmart Solutions",
                "ico": "11223344",
                "email": "info@datasmart.cz",
                "desc": "Analýza dat a AI.",
                "practices": [
                    {
                        "title": "Data Analyst Junior",
                        "desc": "Zpracování dat v Python Pandas.",
                    },
                ],
            },
        ]

        self.stdout.write(" - Vytváření Firem a Praxí...")

        for comp_data in companies:
            # 1. Firma
            profile, created = EmployerProfile.objects.get_or_create(
                ico=comp_data["ico"],
                defaults={
                    "company_name": comp_data["name"],
                    "dic": "CZ" + comp_data["ico"],
                    "city": "Ústí nad Labem",
                    "address": "Hlavní 123",
                    "company_profile": comp_data["desc"],
                    "approval_status": ApprovalStatus.APPROVED,
                },
            )
            if created:
                self.stdout.write(f"   + Firma: {comp_data['name']}")

            # 2. Uživatel firmy (Owner)
            if not User.objects.filter(email=comp_data["email"]).exists():
                org_user = OrganizationUser.objects.create_user(
                    email=comp_data["email"],
                    password="password123",
                    first_name="Jan",
                    last_name="Manažer",
                    employer_profile=profile,
                    organization_role=OrganizationRole.OWNER,
                    is_active=True,
                )
                self.stdout.write(f"   + Uživatel: {comp_data['email']}")
            else:
                org_user = OrganizationUser.objects.get(email=comp_data["email"])

            # 3. Praxe
            for prac_data in comp_data["practices"]:
                # Vybereme náhodný předmět pro praxi
                subject = random.choice(subjects) if subjects else None

                if not Practice.objects.filter(
                    title=prac_data["title"], employer=profile
                ).exists():
                    Practice.objects.create(
                        employer=profile,
                        subject=subject,
                        title=prac_data["title"],
                        description=prac_data["desc"],
                        responsibilities="Dochvilnost, chuť se učit, základní znalost GITu.",
                        available_positions=2,
                        start_date=date.today() + timedelta(days=10),
                        end_date=date.today() + timedelta(days=90),
                        progress_status=ProgressStatus.NOT_STARTED,
                        approval_status=ApprovalStatus.APPROVED,
                        contact_user=org_user,
                        is_active=True,
                        coefficient=1.0,
                    )
                    self.stdout.write(f"     -> Praxe: {prac_data['title']}")
