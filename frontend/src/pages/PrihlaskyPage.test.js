import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PrihlaskyPage from './PrihlaskyPage';
import { useStudentPracticeAPI } from '@api/student_practice/student_practiceAPI';
import { useUser } from '@hooks/UserProvider';
import { useMessage } from '@hooks/MessageContext';
import User from '@auth/UserObj';

// Mock the hooks
jest.mock('@api/student_practice/student_practiceAPI');
jest.mock('@hooks/UserProvider');
jest.mock('@hooks/MessageContext');

// Mock child components
jest.mock('@components/Prihlasky/PrihlaskaEntity', () => ({ entity, onPopup }) => (
    <div data-testid="prihlaska-entity">
        {entity.student_full_name} - {entity.practice_title}
        {entity.can_approve && <button onClick={() => onPopup(entity)}>Manage</button>}
    </div>
));
jest.mock('@components/Filter/SearchBar', () => ({ value, onChange }) => (
    <input data-testid="search-bar" value={value} onChange={onChange} />
));
jest.mock('@components/core/Form/DropDown', () => () => <div data-testid="drop-down">DropDown</div>);
jest.mock('@core/Button/BackButton', () => () => <button>Back</button>);
jest.mock('@core/Container/PopUpCon', () => ({ onSubmit, onReject, title }) => (
    <div data-testid="popup">
        {title}
        <button onClick={onSubmit}>Approve</button>
        <button onClick={onReject}>Reject</button>
    </div>
));

describe('PrihlaskyPage', () => {
    const mockGetProfessorApps = jest.fn();
    const mockUpdateStatus = jest.fn();

    // Create a real User instance for professor
    const professorUser = new User();
    professorUser.setUser({
        role: 'VY',
        user_id: 1,
        username: 'profesor',
        email: 'prof@ujep.cz'
    });

    beforeEach(() => {
        useStudentPracticeAPI.mockReturnValue({
            getProfessorApplications: mockGetProfessorApps,
            updateStudentPracticeStatus: mockUpdateStatus,
            getAdminPendingApplications: jest.fn(),
            getOrganizationApplications: jest.fn()
        });
        useUser.mockReturnValue({ user: professorUser });
        useMessage.mockReturnValue({ addMessage: jest.fn() });
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('renders professor applications grouped by employer', async () => {
        const mockData = [
            { student_practice_id: 1, student_full_name: 'Jan Novak', practice_title: 'Praxe 1', employer_name: 'Firma A', can_approve: true },
            { student_practice_id: 2, student_full_name: 'Petr Svoboda', practice_title: 'Praxe 2', employer_name: 'Firma A', can_approve: false },
            { student_practice_id: 3, student_full_name: 'Eva Bila', practice_title: 'Praxe 3', employer_name: 'Firma B', can_approve: true }
        ];
        mockGetProfessorApps.mockResolvedValue(mockData);

        render(
            <MemoryRouter>
                <PrihlaskyPage />
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('Firma A')).toBeInTheDocument();
        });
        await waitFor(() => {
            expect(screen.getByText('Firma B')).toBeInTheDocument();
        });

        expect(screen.getByText('Jan Novak - Praxe 1')).toBeInTheDocument();
        expect(screen.getByText('Petr Svoboda - Praxe 2')).toBeInTheDocument();
        expect(screen.getByText('Eva Bila - Praxe 3')).toBeInTheDocument();

        // Check "Manage" button visibility (based on can_approve)
        const manageButtons = screen.getAllByRole('button', { name: 'Manage' });
        expect(manageButtons).toHaveLength(2); // Only for Jan and Eva
    });

    test('shows search and filter for professor', async () => {
        mockGetProfessorApps.mockResolvedValue([]);

        render(
            <MemoryRouter>
                <PrihlaskyPage />
            </MemoryRouter>
        );

        expect(screen.getByTestId('search-bar')).toBeInTheDocument();
        expect(screen.getByTestId('drop-down')).toBeInTheDocument();
    });

    test('handles approval workflow', async () => {
        const mockData = [
            { student_practice_id: 1, student_full_name: 'Jan Novak', practice_title: 'Praxe 1', employer_name: 'Firma A', can_approve: true }
        ];
        mockGetProfessorApps.mockResolvedValue(mockData);
        mockUpdateStatus.mockResolvedValue({ status: 'success' });

        render(
            <MemoryRouter>
                <PrihlaskyPage />
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('Jan Novak - Praxe 1')).toBeInTheDocument();
        });

        // Click manage button
        fireEvent.click(screen.getByText('Manage'));

        // Check if popup appears
        expect(screen.getByTestId('popup')).toBeInTheDocument();
        expect(screen.getByText('applications.change_status_title')).toBeInTheDocument();

        // Click approve
        fireEvent.click(screen.getByText('Approve'));

        await waitFor(() => {
            expect(mockUpdateStatus).toHaveBeenCalledWith(1, 'approve');
        });
        await waitFor(() => {
            expect(mockGetProfessorApps).toHaveBeenCalledTimes(2); // Initial + Refresh
        });
    });
});
