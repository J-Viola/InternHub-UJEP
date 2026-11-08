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

jest.mock('@api/student_practice/student_practiceAPI');
jest.mock('@api/nabidka/nabidkaAPI');
jest.mock('@api/documents/documentsAPI');
jest.mock('@hooks/UserProvider');
jest.mock('@hooks/MessageContext');
// Timeline volá přes useApi (Auth kontext) — v testu ho nahradíme prázdným clientem
jest.mock('@hooks/useApi', () => ({
    useApi: () => ({ get: jest.fn().mockResolvedValue({ data: [] }) }),
}));


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
      jest.useRealTimers();
      jest.restoreAllMocks();
      jest.clearAllMocks();
    });

    test('C19-B: garant (VY) rozhoduje o DOCUMENTS_RESUBMITTED, terminální REJECTED jen admin', async () => {
        useUser.mockReturnValue({ user: makeUser('VY') });
        renderPage();

        await waitFor(() => {
            expect(screen.getByText("Schválit opravu (Ukončeno)")).toBeInTheDocument();
        });
        expect(screen.getByText("Schválit opravu (kontrola dokumentů)")).toBeInTheDocument();
        expect(screen.getByText("Zamítnout opravu")).toBeInTheDocument();
        // garant není admin → terminální zamítnutí se nezobrazuje
        expect(screen.queryByText("Trvale zamítnout (REJECTED)")).not.toBeInTheDocument();

        fireEvent.click(screen.getByText("Schválit opravu (Ukončeno)"));
        await waitFor(() => {
            expect(mockTransition).toHaveBeenCalledWith('5', 5, '');
        });
    });

    test('C19-B: admin vidí i terminální REJECTED a schválí opravu pokračováním', async () => {
        useUser.mockReturnValue({ user: makeUser('admin') });
        renderPage();

        await waitFor(() => {
            expect(screen.getByText("Trvale zamítnout (REJECTED)")).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText("Schválit opravu (kontrola dokumentů)"));
        await waitFor(() => {
            expect(mockTransition).toHaveBeenCalledWith('5', 8, '');
        });
    });

    test('C19-B: student ve DOCUMENTS_RESUBMITTED vidí stav, ale žádné review akce', async () => {
        useUser.mockReturnValue({ user: makeUser('ST') });
        renderPage();

        await waitFor(() => {
            expect(
                screen.getByText("Opravené dokumenty byly nahrány a čekají na kontrolu garantem. Schválení provede garant nebo škola.")
            ).toBeInTheDocument();
        });
        expect(screen.queryByText("Schválit opravu (Ukončeno)")).not.toBeInTheDocument();
        expect(screen.queryByText("Zamítnout opravu")).not.toBeInTheDocument();
        expect(screen.queryByText("Trvale zamítnout (REJECTED)")).not.toBeInTheDocument();
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
                screen.getByText("Dokumenty byly zamítnuty. Nahraďte opravené soubory v panelu dokumentů níže — po nahrání odejdou ke kontrole garantovi.")
            ).toBeInTheDocument();
        });
        // důvod se zobrazí v obou banerech (rejected + opravný)
        expect(screen.getAllByText('Chybí podpis').length).toBeGreaterThan(0);
    });

    test('feedback review is available only for ENDED or corrective states', async () => {
        const feedbackDoc = { id: 31, type: 'feedback', status: 0 };
        mockGetCard.mockResolvedValue(makeEntity({
            student_practice_documents: [feedbackDoc],
            student_practice_status: { ...makeEntity().student_practice_status, workflow_status: 'APPLIED' },
        }));
        useUser.mockReturnValue({ user: makeUser('VY') });
        const { unmount } = renderPage();
        await waitFor(() => expect(mockGetCard).toHaveBeenCalled());
        expect(screen.queryByText("Schválit")).not.toBeInTheDocument();
        unmount();

        mockGetCard.mockResolvedValue(makeEntity({
            student_practice_documents: [feedbackDoc],
            student_practice_status: { ...makeEntity().student_practice_status, workflow_status: 'ENDED' },
        }));
        renderPage();
        expect((await screen.findAllByText("Zpětná vazba")).length).toBeGreaterThan(0);
    });

  test('refreshes detail and timeline when window regains focus', async () => {
        useUser.mockReturnValue({ user: makeUser('ST') });
        renderPage();
        await waitFor(() => expect(mockGetCard).toHaveBeenCalledTimes(1));
        fireEvent.focus(window);
        await waitFor(() => expect(mockGetCard).toHaveBeenCalledTimes(2));
  });

  test('focus/visibility refresh keeps an open dialog and deduplicates requests', async () => {
    mockGetCard.mockResolvedValue(makeEntity({
      student_practice_status: { ...makeEntity().student_practice_status, workflow_status: 'CONTRACTED' },
    }));
    useUser.mockReturnValue({ user: makeUser('ST') });
    renderPage();
    fireEvent.click(await screen.findByText("Stornovat praxi"));
    const textarea = screen.getByPlaceholderText("Důvod ukončení");
    fireEvent.change(textarea, { target: { value: 'Rozepsaný důvod žádosti' } });

    mockGetCard.mockClear();
    fireEvent.focus(window);
    fireEvent(document, new Event('visibilitychange'));

    expect(screen.getByPlaceholderText("Důvod ukončení")).toBe(textarea);
    expect(textarea).toHaveValue('Rozepsaný důvod žádosti');
    expect(mockGetCard).toHaveBeenCalledTimes(1);
  });

    test('A-12: student stornuje praxi z CONTRACTED (důvod povinný)', async () => {
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

        const requestButton = await screen.findByText("Stornovat praxi");
        fireEvent.click(requestButton);

        const textarea = screen.getByPlaceholderText("Důvod ukončení");
        fireEvent.change(textarea, { target: { value: 'Zrušeno ze zdravotních důvodů' } });
        fireEvent.click(screen.getByTestId('popup-submit'));

        await waitFor(() => {
            expect(mockRequestCancellation).toHaveBeenCalledWith('5', 'Zrušeno ze zdravotních důvodů');
        });
        expect(mockAddMessage).toHaveBeenCalledWith("Praxe byla stornována", 'S');
        // žádost se neposílá bez důvodu
        expect(mockRequestCancellation).toHaveBeenCalledTimes(1);
    });

    test('A-12: bez důvodu se storno neodešle', async () => {
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

        fireEvent.click(await screen.findByText("Stornovat praxi"));
        fireEvent.click(screen.getByTestId('popup-submit'));

        expect(mockRequestCancellation).not.toHaveBeenCalled();
        expect(mockAddMessage).toHaveBeenCalledWith(
            "Důvod storno je povinný",
            'E'
        );
    });

    const cancelledByStudent = (extra = {}) =>
        makeEntity({
            cancellation_reason: 'Z rodinných důvodů',
            is_cancelled: true,
            cancellation_requested_at: '2026-10-10T10:00:00Z',
            cancellation_resolved_at: null,
            ...extra,
        });

    test('A-12: storno studentem — student vidí stav bez akce, garant může vzít na vědomí', async () => {
        mockGetCard.mockResolvedValue(cancelledByStudent());

        // student: banner stavu, žádná nová akce
        useUser.mockReturnValue({ user: makeUser('ST') });
        const { unmount } = renderPage();
        await waitFor(() => {
            expect(
                screen.getByText("Praxe je stornována. Novou žádost o praxi můžete podat, až garant storno vezme na vědomí.")
            ).toBeInTheDocument();
        });
        expect(screen.queryByText("Stornovat praxi")).not.toBeInTheDocument();
        expect(screen.queryByText("Vzít na vědomí")).not.toBeInTheDocument();
        unmount();

        // garant VK: vezme storno na vědomí (bez rozhodnutí a bez důvodu)
        useUser.mockReturnValue({ user: makeUser('VK') });
        renderPage();
        await waitFor(() => {
            expect(
                screen.getByText("Student tuto praxi stornoval. Vezměte storno na vědomí:")
            ).toBeInTheDocument();
        });
        fireEvent.click(screen.getByText("Vzít na vědomí"));
        await waitFor(() => {
            expect(mockResolveCancellation).toHaveBeenCalledWith('5');
        });
    });

    test('A-12: vzaté na vědomí storno už banner ani tlačítko nezobrazuje', async () => {
        mockGetCard.mockResolvedValue(cancelledByStudent({ cancellation_resolved_at: '2026-10-11T10:00:00Z' }));
        useUser.mockReturnValue({ user: makeUser('VK') });
        renderPage();
        await waitFor(() => {
            expect(mockGetCard).toHaveBeenCalled();
        });
        expect(screen.queryByText("Vzít na vědomí")).not.toBeInTheDocument();
    });

    test('A-12: organizace nemůže vzít storno na vědomí', async () => {
        mockGetCard.mockResolvedValue(cancelledByStudent());
        useUser.mockReturnValue({ user: makeUser('OWNER') });
        renderPage();
        await waitFor(() => {
            expect(mockGetCard).toHaveBeenCalled();
        });
        expect(screen.queryByText("Vzít na vědomí")).not.toBeInTheDocument();
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
        useUser.mockReturnValue({ user: makeUser('OWNER') });
        const { unmount } = renderPage();
        await waitFor(() => {
            expect(
                screen.getByText("Potvrdit přijetí smlouvy")
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
        expect(screen.queryByText("Potvrdit přijetí smlouvy")).not.toBeInTheDocument();
    });

    test('T2b: školní role vidí potvrzení smlouvy v AWAITING_CONTRACT', async () => {
        mockGetCard.mockResolvedValue(makeEntity({
            student_practice_status: { ...makeEntity().student_practice_status, workflow_status: 'AWAITING_CONTRACT' },
        }));
        useUser.mockReturnValue({ user: makeUser('VY') });
        renderPage();
        fireEvent.click(await screen.findByText("Potvrdit přijetí smlouvy"));
        await waitFor(() => expect(mockConfirmContract).toHaveBeenCalledWith('5'));
    });

    test('resubmit passes the current content-rejected state', async () => {
        mockGetCard.mockResolvedValue(makeEntity({
            student_practice_status: { ...makeEntity().student_practice_status, workflow_status: 'CONTENT_REJECTED' },
        }));
        useUser.mockReturnValue({ user: makeUser('ST') });
        renderPage();
        fireEvent.click(await screen.findByText("Upravit a znovu odeslat"));
        await waitFor(() => expect(mockUpdateStatus).toHaveBeenCalledWith('5', 'resubmit', { workflowStatus: 'CONTENT_REJECTED' }));
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

        fireEvent.click(await screen.findByText("Spravovat"));
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
            Object.assign(new Error('capacity'), { code: 'CAPACITY_FULL', details: 'Kapacita partnera je plně obsazena' })
        );

        renderPage();

        fireEvent.click(await screen.findByText("Podat přihlášku"));
        fireEvent.click(screen.getByTestId('popup-submit'));

        await waitFor(() => {
            expect(mockAddMessage).toHaveBeenCalledWith(
                'Kapacita partnera je plně obsazena',
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
        expect(screen.queryByText("Udělit zápočet (Splněno)")).not.toBeInTheDocument();
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

        fireEvent.click(await screen.findByText("Udělit zápočet (Splněno)"));
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

        fireEvent.click(await screen.findByText("Schválit"));
        await waitFor(() => {
            expect(mockReviewDocument).toHaveBeenCalledWith(42, 1, '');
        });
    });
});
