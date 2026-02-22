import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import NabidkaDetailPage from './NabidkaDetailPage';
import { useNabidkaAPI } from '@api/nabidka/nabidkaAPI';
import { useUser } from '@hooks/UserProvider';
import { useMessage } from '@hooks/MessageContext';

// Mock hooks
jest.mock('@api/nabidka/nabidkaAPI');
jest.mock('@hooks/UserProvider');
jest.mock('@hooks/MessageContext');
jest.mock('@api/documents/documentsAPI', () => ({
    useDocumentsAPI: () => ({})
}));
jest.mock('@utils/ToDoAlert', () => jest.fn());

// Mock child components
jest.mock('@core/Container/PopUpCon', () => ({ onSubmit, onClose }) => (
    <div data-testid="popup">
        <button onClick={onSubmit}>Confirm Apply</button>
        <button onClick={onClose}>Close</button>
    </div>
));

describe('NabidkaDetailPage', () => {
    const mockGetNabidkaById = jest.fn();
    const mockApplyNabidka = jest.fn();
    const mockAddMessage = jest.fn();
    const mockUser = {
        isStudent: jest.fn(),
        isDepartmentMg: jest.fn(),
        isOrganizationUser: jest.fn(),
        isAdmin: jest.fn(),
    };

    const mockOffer = {
        practice_id: 1,
        title: 'Test Offer',
        description: 'Test Desc',
        responsibilities: 'Test Resp',
        employer: { address: 'Test City', employer_id: 10 },
        start_date: '01.01.2025',
        end_date: '01.06.2025',
        approval_status: 1,
        contact_user_info: { email: 'contact@test.com' }
    };

    beforeEach(() => {
        useNabidkaAPI.mockReturnValue({
            getNabidkaById: mockGetNabidkaById,
            applyNabidka: mockApplyNabidka
        });
        useUser.mockReturnValue({ user: mockUser });
        useMessage.mockReturnValue({ addMessage: mockAddMessage });

        mockGetNabidkaById.mockResolvedValue(mockOffer);
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('renders offer details', async () => {
        mockUser.isStudent.mockReturnValue(true);

        render(
            <MemoryRouter initialEntries={['/nabidka/1']}>
                <Routes>
                    <Route path="/nabidka/:id" element={<NabidkaDetailPage />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('Test Offer')).toBeInTheDocument();
        });
        expect(screen.getByText('Test Desc')).toBeInTheDocument();
        expect(screen.getByText('Místo konání: Test City')).toBeInTheDocument();
    });

    test('shows apply button for student and handles submission', async () => {
        mockUser.isStudent.mockReturnValue(true);
        mockUser.isDepartmentMg.mockReturnValue(false);
        mockUser.isOrganizationUser.mockReturnValue(false);
        mockUser.isAdmin.mockReturnValue(false);

        render(
            <MemoryRouter initialEntries={['/nabidka/1']}>
                <Routes>
                    <Route path="/nabidka/:id" element={<NabidkaDetailPage />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('Podat přihlášku')).toBeInTheDocument();
        });

        fireEvent.click(screen.getByText('Podat přihlášku'));
        expect(screen.getByTestId('popup')).toBeInTheDocument();

        mockApplyNabidka.mockResolvedValue({ status: 201 });
        fireEvent.click(screen.getByText('Confirm Apply'));

        await waitFor(() => {
            expect(mockApplyNabidka).toHaveBeenCalledWith({ practice: '1' });
        });
        await waitFor(() => {
            expect(mockAddMessage).toHaveBeenCalledWith('Přihláška byla úspěšně podána', 'S');
        });
    });

    test('shows management buttons for organization owner', async () => {
        mockUser.isStudent.mockReturnValue(false);
        mockUser.isDepartmentMg.mockReturnValue(false);
        mockUser.isOrganizationUser.mockReturnValue(true);
        mockUser.isAdmin.mockReturnValue(false);

        render(
            <MemoryRouter initialEntries={['/nabidka/1']}>
                <Routes>
                    <Route path="/nabidka/:id" element={<NabidkaDetailPage />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('Zobrazit přihlášené')).toBeInTheDocument();
        });
        await waitFor(() => {
            expect(screen.getByText('Upravit nabídku')).toBeInTheDocument();
        });
    });
});
