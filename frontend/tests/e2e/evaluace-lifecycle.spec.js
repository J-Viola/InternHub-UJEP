import { test, expect } from '@playwright/test';
import { waitForAppLoad, safeClick } from './helpers';
import { execSync } from 'child_process';

test.describe('Evaluace Lifecycle (E2E)', () => {
  test.setTimeout(120000);

  test('Mentor vyplní evaluační formulář pro praxi ve stavu ENDED', async ({ browser }) => {
    const uniqueId = Date.now().toString();
    const practiceTitle = `E2E Eval ${uniqueId}`;

    // --- SETUP: Vytvořit praxi a StudentPractice ve stavu ENDED přes Django shell ---
    const setupScript = `
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app.settings')
django.setup()
from datetime import date, timedelta
from practices.models import Practice, PracticeWorkflowState
from student_practices.models import StudentPractice, StudentPracticeWorkflowState
from users.models import StudentUser, OrganizationUser, EmployerProfile, ApprovalStatus, ProgressStatus
from subject.models import Subject

student = StudentUser.objects.first()
company = OrganizationUser.objects.filter(organization_role='OWNER').first()
profile = company.employer_profile if company and company.employer_profile else EmployerProfile.objects.first()
subject = Subject.objects.first()

practice = Practice.objects.create(
    employer=profile, subject=subject, title='${practiceTitle}',
    description='Eval test', responsibilities='Testing',
    available_positions=2,
    start_date=date.today()-timedelta(days=30),
    end_date=date.today()-timedelta(days=5),
    progress_status=ProgressStatus.NOT_STARTED,
    approval_status=ApprovalStatus.APPROVED,
    workflow_state=PracticeWorkflowState.OPEN_FOR_APPLICATIONS,
    contact_user=company, is_active=True, coefficient=1.0,
)

sp = StudentPractice.objects.create(
    user=student, practice=practice,
    application_date=date.today()-timedelta(days=25),
    approval_status=ApprovalStatus.APPROVED,
    progress_status=ProgressStatus.IN_PROGRESS,
    school_approved=True, employer_approved=True,
    workflow_state=StudentPracticeWorkflowState.ENDED,
    start_date=practice.start_date, end_date=practice.end_date,
    hours_completed=100,
)
print(sp.student_practice_id)
`;
    const shellOutput = execSync(
      `cd /media/F/Github/InternHub-UJEP/backend && python manage.py shell -c "${setupScript.replace(/\n/g, ' ')}"`,
      { encoding: 'utf-8' }
    );
    const spId = shellOutput.trim().split('\n').pop();
    if (!spId || isNaN(parseInt(spId, 10))) {
      throw new Error('Failed to create ENDED student practice via shell. Output: ' + shellOutput);
    }

    // --- STEP 1: Login jako mentor (professor) ---
    const profContext = await browser.newContext({ storageState: 'playwright/.auth/professor.json' });
    const profPage = await profContext.newPage();

    await profPage.goto(`/evaluace/${spId}`);
    await waitForAppLoad(profPage);

    // --- STEP 2: Vyplnit evaluační formulář ---
    // Hodnocení: expertise, communication, initiative (range inputs)
    const ranges = profPage.locator('input[type="range"]');
    await expect(ranges.nth(0)).toBeVisible({ timeout: 10000 });
    await ranges.nth(0).fill('4');
    await ranges.nth(1).fill('5');
    await ranges.nth(2).fill('3');

    await profPage.locator('textarea[name="overall_comment"]').fill('E2E test evaluation comment');

    // --- STEP 3: Nahrát PDF protokol ---
    const pdfPath = '/tmp/e2e_eval_protocol.pdf';
    require('fs').writeFileSync(pdfPath, '%PDF-1.4 fake pdf content');
    await profPage.locator('input[type="file"]').setInputFiles(pdfPath);

    // --- STEP 4: Odeslat formulář ---
    await safeClick(profPage.getByRole('button', { name: /Odeslat|Submit|Uložit/i }));

    // --- STEP 5: Ověřit úspěch (redirect nebo success message) ---
    await expect(profPage).toHaveURL(/.*\/praxe/, { timeout: 20000 });

    await profContext.close();
  });
});
