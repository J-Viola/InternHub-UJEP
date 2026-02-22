import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import VytvoritNabidku from './VytvoritNabidku';
import { useNabidkaAPI } from '@api/nabidka/nabidkaAPI';
import { useUserAPI } from '@api/user/userAPI';
import { useCodeListAPI } from '@api/code_list/code_listAPI';
import { useMessage } from '@hooks/MessageContext';

// Mock hooks
jest.mock('@api/nabidka/nabidkaAPI');
jest.mock('@api/user/userAPI');
jest.mock('@api/code_list/code_listAPI');
jest.mock('@hooks/MessageContext');

// Mock navigation
const mockNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
    ...jest.requireActual('react-router-dom'),
    useNavigate: () => mockNavigate
}));

// Mock child components
jest.mock('@components/Forms/NabidkaForm', () => ({ handleSubmit, handleChange, formData }) => (
    <div data-testid="nabidka-form">
        <button onClick={() => handleChange({ start_date: '01.01.2025', coefficient: '1.0' })}>
            Set Dates
        </button>
        <button onClick={() => handleSubmit()}>Create</button>
        <span data-testid="end-date">{formData.end_date}</span>
    </div>
));
jest.mock('@core/Button/BackButton', () => () => <button>Back</button>);

describe('VytvoritNabidku', () => {
    const mockCreateNabidka = jest.fn();
    const mockCalculateEndDate = jest.fn();
    const mockGetUniqueSubjects = jest.fn();
    const mockGetOrganizationUsers = jest.fn();
    const mockAddMessage = jest.fn();

    beforeEach(() => {
        useNabidkaAPI.mockReturnValue({
            createNabidka: mockCreateNabidka,
            calculateEndDate: mockCalculateEndDate
        });
        useUserAPI.mockReturnValue({
            getOrganizationUsers: mockGetOrganizationUsers
        });
        useCodeListAPI.mockReturnValue({
            getUniqueSubjects: mockGetUniqueSubjects
        });
        useMessage.mockReturnValue({ addMessage: mockAddMessage });

        // Default mock resolutions
        mockGetUniqueSubjects.mockResolvedValue([{ label: 'Math', value: 1 }]);
        mockGetOrganizationUsers.mockResolvedValue([{ label: 'Boss', value: 10 }]);
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('initializes data on mount', async () => {
        render(
            <MemoryRouter>
                <VytvoritNabidku />
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(mockGetUniqueSubjects).toHaveBeenCalled();
        });
        await waitFor(() => {
            expect(mockGetOrganizationUsers).toHaveBeenCalled();
        });
    });

    test('calculates end date when start date and coefficient change', async () => {
        mockCalculateEndDate.mockResolvedValue('01.06.2025');

        render(
            <MemoryRouter>
                <VytvoritNabidku />
            </MemoryRouter>
        );

        const setDatesBtn = screen.getByText('Set Dates');
        setDatesBtn.click();

        await waitFor(() => {
            expect(mockCalculateEndDate).toHaveBeenCalledWith('01.01.2025', '1.0');
        });
        await waitFor(() => {
            expect(screen.getByTestId('end-date')).toHaveTextContent('01.06.2025');
        });
    });

    test('handles successful creation', async () => {
        mockCreateNabidka.mockResolvedValue({ id: 100 });

        render(
            <MemoryRouter>
                <VytvoritNabidku />
            </MemoryRouter>
        );

        const createBtn = screen.getByText('Create');
        createBtn.click();

        await waitFor(() => {
            expect(mockCreateNabidka).toHaveBeenCalled();
        });
        await waitFor(() => {
            expect(mockNavigate).toHaveBeenCalledWith(-1);
        });
    });

    test('handles creation failure', async () => {
        mockCreateNabidka.mockRejectedValue({
            response: { data: { detail: 'Title required' } }
        });

        render(
            <MemoryRouter>
                <VytvoritNabidku />
            </MemoryRouter>
        );

        const createBtn = screen.getByText('Create');
        createBtn.click();

        await waitFor(() => {
            expect(mockAddMessage).toHaveBeenCalledWith('Title required', 'E');
        });
    });
});
