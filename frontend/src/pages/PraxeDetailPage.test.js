import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import PraxeDetailPage from './PraxeDetailPage';
import { useStudentPracticeAPI } from '@api/student_practice/student_practiceAPI';
import { useNabidkaAPI } from '@api/nabidka/nabidkaAPI';
import { useDocumentsAPI } from '@api/documents/documentsAPI';
import { useUser } from '@hooks/UserProvider';
import { useMessage } from '@hooks/MessageContext';
import User from '@auth/UserObj';
import translations from '../../public/locales/cs/translation.json';

jest.mock('@api/student_practice/student_practiceAPI');
jest.mock('@api/nabidka/nabidkaAPI');
jest.mock('@api/documents/documentsAPI');
jest.mock('@hooks/UserProvider');
jest.mock('@hooks/MessageContext');
// Timeline volá přes useApi (Auth kontext) — v testu ho nahradíme prázdným clientem
jest.mock('@hooks/useApi', () => ({
    useApi: () => ({ get: jest.fn().mockResolvedValue({ data: [] }) }),
}));

jest.mock('react-i18next', () => {
    const dict = require('../../public/locales/cs/translation.json');
    const resolve = (obj, key) =>
        key.split('.').reduce((acc, part) => (acc && typeof acc === 'object' ? acc[part] : undefined), obj);
    return {
        useTranslation: () => ({
            t: (key) => resolve(dict, key) ?? key,
            i18n: { language: 'cs' },
        }),
    };
});

jest.mock('@core/Button/BackButton', () => () => <button>Back</button>);

jest.mock('@core/Container/PopUpCon', () => ({
    __esModule: true,
    default: ({ title, text, onSubmit, onReject, onSubmitText, onRejectText, children }) => (
        <div data-testid="popup">
            <div data-testid="popup-title">{title}</div>
            <div data-testid="popup-text">{text}</div>
            {children}
            <button data-testid="popup-submit" onClick={onSubmit}>
                {onSubmitText || 'submit'}
            </button>
            <button data-testid="popup-reject" onClick={onReject}>
                {onRejectText || 'reject'}
            </button>
        </div>
    ),
}));

const resolve = (obj, key) =>
    key.split('.').reduce((acc, part) => (acc && typeof acc === 'object' ? acc[part] : undefined), obj);
const tr = (key) => resolve(translations, key) ?? key;

const makeUser = (role) => {
    const user = new User();
    user.setUser({ role, user_id: 1, username: `u_${role}`, email: `${role}@test.cz` });
    return user;
};

const makeEntity = (overrides = {}) => ({
    student_practice_id: 5,
    title: 'Praxe v týmu',
    description: 'Popis praxe',
    responsibilities: 'Požadavky',
    start_date: '01.01.2026',
    end_date: '30.06.2026',
    image_base64: null,
    employer: { address: 'Ústí nad Labem' },
    subject: { subject_code: 'KI', hours_required: 480 },
    contact_user_info: null,
    can_approve: false,
    is_cancelled: false,
    progress_status: 0,
    student_practice_documents: [],
    student_practice_status: {
        application_date: '01.01.2026',
        workflow_status: 'DOCUMENTS_RESUBMITTED',
        workflow_status_label: 'Opravené dokumenty čekají na kontrolu',
        rejection_reason: '',
        hours_completed: 0,
        school_approved: false,
        employer_approved: false,
        student_info: {
            user_id: 7,
            full_name: 'Jan Novák',
            os_cislo: 'n12345',
            email: 'jan@test.cz',
        },
    },
    ...overrides,
});

describe('PraxeDetailPage — BL-04 role visibility / workflow akce', () => {
    const mockGetCard = jest.fn();
    const mockTransition = jest.fn();
    const mockUpdateStatus = jest.fn();
    const mockRequestCancellation = jest.fn();
    const mockResolveCancellation = jest.fn();
    const mockConfirmContract = jest.fn();
    const mockWithdraw = jest.fn();
    const mockApply = jest.fn();
    const mockAddMessage = jest.fn();

    const renderPage = () =>
        render(
            <MemoryRouter initialEntries={['/karta-praxe/5']}>
                <Routes>
                    <Route path="/karta-praxe/:id" element={<PraxeDetailPage />} />
                </Routes>
            </MemoryRouter>
        );

    beforeEach(() => {
        useStudentPracticeAPI.mockReturnValue({
            getStudentPracticeCard: mockGetCard,
            transitionStudentPractice: mockTransition,
            updateStudentPracticeStatus: mockUpdateStatus,
            requestCancellation: mockRequestCancellation,
            resolveCancellation: mockResolveCancellation,
            confirmContract: mockConfirmContract,
            withdrawApplication: mockWithdraw,
            downloadGeneratedDocument: jest.fn(),
            reapplyToPractice: jest.fn(),
        });
        useNabidkaAPI.mockReturnValue({ applyNabidka: mockApply });
        useDocumentsAPI.mockReturnValue({
            downloadDocument: jest.fn(),
            uploadDocument: jest.fn(),
            reviewDocument: jest.fn(),
        });
        useMessage.mockReturnValue({ addMessage: mockAddMessage });
        mockGetCard.mockResolvedValue(makeEntity());
        mockTransition.mockResolvedValue({});
        mockUpdateStatus.mockResolvedValue({});
        mockRequestCancellation.mockResolvedValue({});
        mockResolveCancellation.mockResolvedValue({});
        mockConfirmContract.mockResolvedValue({});
        mockApply.mockResolvedValue({ ok: true });
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('C19-B: garant (VY) rozhoduje o DOCUMENTS_RESUBMITTED, terminální REJECTED jen admin', async () => {
        useUser.mockReturnValue({ user: makeUser('VY') });
        renderPage();

        await waitFor(() => {
            expect(screen.getByText(tr('practice_detail.repair_approve'))).toBeInTheDocument();
        });
        expect(screen.getByText(tr('practice_detail.repair_approve_continue'))).toBeInTheDocument();
        expect(screen.getByText(tr('practice_detail.repair_reject'))).toBeInTheDocument();
        // garant není admin → terminální zamítnutí se nezobrazuje
        expect(screen.queryByText(tr('practice_detail.terminal_reject'))).not.toBeInTheDocument();

        fireEvent.click(screen.getByText(tr('practice_detail.repair_approve')));
        await waitFor(() => {
            expect(mockTransition).toHaveBeenCalledWith('5', 5, '');
        });
    });

    test('C19-B: admin vidí i terminální REJECTED a schválí opravu pokračováním', async () => {
        useUser.mockReturnValue({ user: makeUser('admin') });
        renderPage();

        await waitFor(() => {
            expect(screen.getByText(tr('practice_detail.terminal_reject'))).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText(tr('practice_detail.repair_approve_continue')));
        await waitFor(() => {
            expect(mockTransition).toHaveBeenCalledWith('5', 8, '');
        });
    });

    test('C19-B: student ve DOCUMENTS_RESUBMITTED vidí stav, ale žádné review akce', async () => {
        useUser.mockReturnValue({ user: makeUser('ST') });
        renderPage();

        await waitFor(() => {
            expect(
                screen.getByText(tr('practice_detail.documents_resubmitted_banner'))
            ).toBeInTheDocument();
        });
        expect(screen.queryByText(tr('practice_detail.repair_approve'))).not.toBeInTheDocument();
        expect(screen.queryByText(tr('practice_detail.repair_reject'))).not.toBeInTheDocument();
        expect(screen.queryByText(tr('practice_detail.terminal_reject'))).not.toBeInTheDocument();
    });

    test('C19-B: student ve DOCUMENTS_REJECTED dostane opravný banner', async () => {
        mockGetCard.mockResolvedValue(
            makeEntity({
                student_practice_status: {
                    ...makeEntity().student_practice_status,
                    workflow_status: 'DOCUMENTS_REJECTED',
                    rejection_reason: 'Chybí podpis',
                },
            })
        );
        useUser.mockReturnValue({ user: makeUser('ST') });
        renderPage();

        await waitFor(() => {
            expect(
                screen.getByText(tr('practice_detail.documents_rejected_banner'))
            ).toBeInTheDocument();
        });
        // důvod se zobrazí v obou banerech (rejected + opravný)
        expect(screen.getAllByText('Chybí podpis').length).toBeGreaterThan(0);
    });

    test('C02-A: student požádá o storno z CONTRACTED (důvod povinný)', async () => {
        mockGetCard.mockResolvedValue(
            makeEntity({
                student_practice_status: {
                    ...makeEntity().student_practice_status,
                    workflow_status: 'CONTRACTED',
                },
            })
        );
        useUser.mockReturnValue({ user: makeUser('ST') });
        renderPage();

        const requestButton = await screen.findByText(tr('practice_detail.cancel_request_button'));
        fireEvent.click(requestButton);

        const textarea = screen.getByPlaceholderText(tr('practice_detail.cancel_request_placeholder'));
        fireEvent.change(textarea, { target: { value: 'Zrušeno ze zdravotních důvodů' } });
        fireEvent.click(screen.getByTestId('popup-submit'));

        await waitFor(() => {
            expect(mockRequestCancellation).toHaveBeenCalledWith('5', 'Zrušeno ze zdravotních důvodů');
        });
        expect(mockAddMessage).toHaveBeenCalledWith(tr('practice_detail.cancel_request_success'), 'S');
        // žádost se neposílá bez důvodu
        expect(mockRequestCancellation).toHaveBeenCalledTimes(1);
    });

    test('C02-A: bez důvodu se žádost o storno neodešle', async () => {
        mockGetCard.mockResolvedValue(
            makeEntity({
                student_practice_status: {
                    ...makeEntity().student_practice_status,
                    workflow_status: 'CONTRACTED',
                },
            })
        );
        useUser.mockReturnValue({ user: makeUser('ST') });
        renderPage();

        fireEvent.click(await screen.findByText(tr('practice_detail.cancel_request_button')));
        fireEvent.click(screen.getByTestId('popup-submit'));

        expect(mockRequestCancellation).not.toHaveBeenCalled();
        expect(mockAddMessage).toHaveBeenCalledWith(
            tr('practice_detail.cancel_request_reason_required'),
            'E'
        );
    });

    test('C02-A: pending žádost — student vidí stav bez akce, garant vidí rozhodnutí', async () => {
        mockGetCard.mockResolvedValue(
            makeEntity({
                cancellation_reason: 'Z rodinných důvodů',
                is_cancelled: false,
            })
        );

        // student: banner stavu, žádná nová žádost ani rozhodovací tlačítka
        useUser.mockReturnValue({ user: makeUser('ST') });
        const { unmount } = renderPage();
        await waitFor(() => {
            expect(
                screen.getByText(tr('practice_detail.cancellation_pending_student'))
            ).toBeInTheDocument();
        });
        expect(screen.queryByText(tr('practice_detail.cancel_request_button'))).not.toBeInTheDocument();
        expect(screen.queryByText(tr('practice_detail.cancellation_approve'))).not.toBeInTheDocument();
        expect(screen.queryByText(tr('practice_detail.cancellation_reject'))).not.toBeInTheDocument();
        unmount();

        // garant VK: vidí rozhodnutí a schvaluje
        useUser.mockReturnValue({ user: makeUser('VK') });
        renderPage();
        await waitFor(() => {
            expect(
                screen.getByText(tr('practice_detail.cancellation_pending_resolver'))
            ).toBeInTheDocument();
        });
        fireEvent.click(screen.getByText(tr('practice_detail.cancellation_approve')));
        fireEvent.click(screen.getByTestId('popup-submit'));
        await waitFor(() => {
            expect(mockResolveCancellation).toHaveBeenCalledWith('5', 'approve');
        });
    });

    test('C02-A: organizace ani student nemohou rozhodovat o stornu', async () => {
        mockGetCard.mockResolvedValue(
            makeEntity({ cancellation_reason: 'důvod', is_cancelled: false })
        );
        useUser.mockReturnValue({ user: makeUser('OWNER') });
        const { unmount } = renderPage();
        await waitFor(() => {
            expect(mockGetCard).toHaveBeenCalled();
        });
        expect(screen.queryByText(tr('practice_detail.cancellation_approve'))).not.toBeInTheDocument();
        unmount();

        useUser.mockReturnValue({ user: makeUser('ST') });
        renderPage();
        await waitFor(() => {
            expect(
                screen.getByText(tr('practice_detail.cancellation_pending_student'))
            ).toBeInTheDocument();
        });
        expect(screen.queryByText(tr('practice_detail.cancellation_approve'))).not.toBeInTheDocument();
    });

    test('T2b: potvrzení smlouvy jen ve AWAITING_CONTRACT, ne ve CONTRACTED', async () => {
        mockGetCard.mockResolvedValue(
            makeEntity({
                student_practice_status: {
                    ...makeEntity().student_practice_status,
                    workflow_status: 'AWAITING_CONTRACT',
                },
            })
        );
        useUser.mockReturnValue({ user: makeUser('VY') });
        const { unmount } = renderPage();
        await waitFor(() => {
            expect(
                screen.getByText(tr('practice_detail.confirm_contract'))
            ).toBeInTheDocument();
        });
        unmount();

        mockGetCard.mockResolvedValue(
            makeEntity({
                student_practice_status: {
                    ...makeEntity().student_practice_status,
                    workflow_status: 'CONTRACTED',
                },
            })
        );
        renderPage();
        await waitFor(() => {
            expect(mockGetCard).toHaveBeenCalled();
        });
        expect(screen.queryByText(tr('practice_detail.confirm_contract'))).not.toBeInTheDocument();
    });

    test('FE-002: schválení posílá workflowStatus pro volbu explicitního cíle', async () => {
        mockGetCard.mockResolvedValue(
            makeEntity({
                can_approve: true,
                student_practice_status: {
                    ...makeEntity().student_practice_status,
                    workflow_status: 'APPLIED',
                },
            })
        );
        useUser.mockReturnValue({ user: makeUser('VK') });
        renderPage();

        fireEvent.click(await screen.findByText(tr('common.manage')));
        fireEvent.click(screen.getByTestId('popup-submit'));

        await waitFor(() => {
            expect(mockUpdateStatus).toHaveBeenCalledWith('5', 'approve', {
                workflowStatus: 'APPLIED',
            });
        });
    });

    test('kapacita při podání přihlášky se zobrazí čistě (400 CAPACITY_FULL)', async () => {
        mockGetCard.mockResolvedValue({
            ...makeEntity(),
            student_practice_status: null,
        });
        useUser.mockReturnValue({ user: makeUser('ST') });
        mockApply.mockRejectedValue(
            Object.assign(new Error('capacity'), { code: 'CAPACITY_FULL' })
        );

        renderPage();

        fireEvent.click(await screen.findByText(tr('offers.apply')));
        fireEvent.click(screen.getByTestId('popup-submit'));

        await waitFor(() => {
            expect(mockAddMessage).toHaveBeenCalledWith(
                'Kapacita partnera je plně obsazena.',
                'E'
            );
        });
    });

    test('FE-007: dokončení ENDED → COMPLETED jen pro garanty/admina, gate se zobrazí čistě', async () => {
        mockGetCard.mockResolvedValue(
            makeEntity({
                student_practice_status: {
                    ...makeEntity().student_practice_status,
                    workflow_status: 'ENDED',
                },
            })
        );

        // student akci nevidí
        useUser.mockReturnValue({ user: makeUser('ST') });
        const { unmount } = renderPage();
        await waitFor(() => {
            expect(mockGetCard).toHaveBeenCalled();
        });
        expect(screen.queryByText(tr('practice_detail.complete_button'))).not.toBeInTheDocument();
        unmount();

        // garant: akci vidí a server gate (400) se zobrazí čistě
        useUser.mockReturnValue({ user: makeUser('VK') });
        mockTransition.mockRejectedValue(
            Object.assign(new Error('gate'), {
                code: 'DRF_ERROR',
                details: 'Dokončení vyžaduje hodnotící podklady: evaluace nebyla vytvořena.',
            })
        );
        renderPage();

        fireEvent.click(await screen.findByText(tr('practice_detail.complete_button')));
        await waitFor(() => {
            expect(mockTransition).toHaveBeenCalledWith('5', 6, '');
        });
        expect(mockAddMessage).toHaveBeenCalledWith(
            'Dokončení vyžaduje hodnotící podklady: evaluace nebyla vytvořena.',
            'E'
        );
    });

    test('FE-007: garant schvaluje FEEDBACK dokument přímo na kartě', async () => {
        mockGetCard.mockResolvedValue(
            makeEntity({
                student_practice_documents: [
                    {
                        id: 42,
                        type: 'feedback',
                        status: 0,
                        review_note: '',
                        uploaded_at: null,
                        late_submission: false,
                    },
                ],
                student_practice_status: {
                    ...makeEntity().student_practice_status,
                    workflow_status: 'ENDED',
                },
            })
        );
        const mockReviewDocument = jest.fn().mockResolvedValue({});
        useDocumentsAPI.mockReturnValue({
            downloadDocument: jest.fn(),
            uploadDocument: jest.fn(),
            reviewDocument: mockReviewDocument,
        });
        useUser.mockReturnValue({ user: makeUser('VK') });
        renderPage();

        fireEvent.click(await screen.findByText(tr('common.approve')));
        await waitFor(() => {
            expect(mockReviewDocument).toHaveBeenCalledWith(42, 1, '');
        });
    });
});
