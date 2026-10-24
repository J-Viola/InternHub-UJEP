import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom';
import EvaluationForm from './EvaluationForm';
import { useStudentPracticeAPI } from '@api/student_practice/student_practiceAPI';
import { useApi } from '@hooks/useApi';
import { useUser } from '@hooks/UserProvider';
import { useMessage } from '@hooks/MessageContext';
import User from '@auth/UserObj';
import translations from '../../public/locales/cs/translation.json';

jest.mock('@api/student_practice/student_practiceAPI');
jest.mock('@hooks/useApi');
jest.mock('@hooks/UserProvider');
jest.mock('@hooks/MessageContext');

jest.mock('react-i18next', () => {
    const dict = require('../../public/locales/cs/translation.json');
    const resolve = (obj, key) =>
        key.split('.').reduce((acc, part) => (acc && typeof acc === 'object' ? acc[part] : undefined), obj);
    return {
        useTranslation: () => ({ t: (key) => resolve(dict, key) ?? key, i18n: { language: 'cs' } }),
        // src/i18n.js (přes Auth → apiClient) potřebuje tyto exporty
        initReactI18next: { type: '3rdParty', init: () => {} },
        Trans: ({ children }) => children,
    };
});

jest.mock('@core/Button/BackButton', () => () => <button>Back</button>);

const resolve = (obj, key) =>
    key.split('.').reduce((acc, part) => (acc && typeof acc === 'object' ? acc[part] : undefined), obj);
const tr = (key) => resolve(translations, key) ?? key;

const makeUser = (role) => {
    const user = new User();
    user.setUser({ role, user_id: 2, username: `u_${role}`, email: `${role}@test.cz` });
    return user;
};

const endedEntity = {
    student_practice_id: 9,
    student_practice_status: { workflow_status: 'ENDED' },
};

const LocationDisplay = () => {
    const location = useLocation();
    return <div data-testid="location">{location.pathname}</div>;
};

describe('EvaluationForm — FE-014 role guard a navigace po uložení', () => {
    const mockGetCard = jest.fn();
    const mockPost = jest.fn();
    const mockAddMessage = jest.fn();

    const renderForm = () =>
        render(
            <MemoryRouter initialEntries={['/evaluace/9']}>
                <LocationDisplay />
                <Routes>
                    <Route path="/evaluace/:id" element={<EvaluationForm />} />
                </Routes>
            </MemoryRouter>
        );

    beforeEach(() => {
        useStudentPracticeAPI.mockReturnValue({ getStudentPracticeCard: mockGetCard });
        useApi.mockReturnValue({ post: mockPost });
        useMessage.mockReturnValue({ addMessage: mockAddMessage });
        mockGetCard.mockResolvedValue(endedEntity);
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('student nemůže odevzdat evaluaci (role guard)', async () => {
        useUser.mockReturnValue({ user: makeUser('ST') });
        renderForm();

        await waitFor(() => {
            expect(screen.getByText(tr('evaluation.mentor_only'))).toBeInTheDocument();
        });
        expect(screen.queryByRole('button', { name: tr('evaluation.submit') })).not.toBeInTheDocument();
    });

    test('po úspěšném uložení naviguje na kartu praxes (ne na neexistující /praxe/:id)', async () => {
        useUser.mockReturnValue({ user: makeUser('VY') });
        mockPost.mockResolvedValue({ data: { evaluation_id: 1 } });

        renderForm();

        await waitFor(() => {
            expect(screen.getByRole('button', { name: tr('evaluation.submit') })).toBeInTheDocument();
        });

        // PDF protokol je povinný
        const file = new File(['%PDF-1.4 test'], 'protokol.pdf', { type: 'application/pdf' });
        const fileInput = screen.getByLabelText(tr('evaluation.pdf_upload_label'));
        fireEvent.change(fileInput, { target: { files: [file] } });

        fireEvent.click(screen.getByRole('button', { name: tr('evaluation.submit') }));

        await waitFor(() => {
            expect(mockPost).toHaveBeenCalledTimes(1);
        });
        expect(mockAddMessage).toHaveBeenCalledWith(tr('evaluation.success'), 'S');
        // FE-014: dříve `/praxe/:id` (neexistující route → 404 stránka)
        await waitFor(() => {
            expect(screen.getByTestId('location')).toHaveTextContent('/karta-praxe/9');
        });
        expect(mockPost).toHaveBeenCalledTimes(1);
    });
});
