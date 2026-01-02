import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import StudentApplicationsPage from './StudentApplicationsPage';
import { useNabidkaAPI } from '@api/nabidka/nabidkaAPI';

// Mock the API hook
jest.mock('@api/nabidka/nabidkaAPI');

// Mock child components to avoid deep dependencies
jest.mock('@components/Student/StudentApplicationCard', () => ({ entity }) => (
    <div data-testid="app-card">{entity.practice_title}</div>
));
jest.mock('@components/Student/StudentInvitationCard', () => ({ entity }) => (
    <div data-testid="inv-card">{entity.practice_title}</div>
));

// Mock BackButton
jest.mock('@core/Button/BackButton', () => () => <button>Back</button>);

describe('StudentApplicationsPage', () => {
    const mockGetRelations = jest.fn();

    beforeEach(() => {
        useNabidkaAPI.mockReturnValue({
            getPracticeUserRelations: mockGetRelations
        });
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('renders loading state initially', async () => {
        mockGetRelations.mockReturnValue(new Promise(() => {})); // Never resolves
        render(
            <MemoryRouter>
                <StudentApplicationsPage />
            </MemoryRouter>
        );

        expect(screen.getByText('Načítání...')).toBeInTheDocument();
    });

    test('renders applications and invitations when data is fetched', async () => {
        const mockData = {
            student_practices: [
                { student_practice_id: 1, practice_title: 'App 1' }
            ],
            employer_invitations: [
                { invitation_id: 10, practice_title: 'Inv 1' }
            ]
        };
        mockGetRelations.mockResolvedValue(mockData);

        render(
            <MemoryRouter>
                <StudentApplicationsPage />
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.queryByText('Načítání...')).not.toBeInTheDocument();
        });

        expect(screen.getByText('App 1')).toBeInTheDocument();
        expect(screen.getByText('Inv 1')).toBeInTheDocument();
        expect(screen.getAllByTestId('app-card')).toHaveLength(1);
        expect(screen.getAllByTestId('inv-card')).toHaveLength(1);
    });

    test('renders empty state when no applications exist', async () => {
        mockGetRelations.mockResolvedValue({ student_practices: [], employer_invitations: [] });

        render(
            <MemoryRouter>
                <StudentApplicationsPage />
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByText('Zatím nemáte žádné podané přihlášky.')).toBeInTheDocument();
        });

        expect(screen.queryByTestId('app-card')).not.toBeInTheDocument();
        expect(screen.queryByTestId('inv-card')).not.toBeInTheDocument();
    });
});
