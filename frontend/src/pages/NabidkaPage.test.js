import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import NabidkaPage from './NabidkaPage';
import { useNabidkaAPI } from '@api/nabidka/nabidkaAPI';
import { useCodeListAPI } from '@api/code_list/code_listAPI';
import { useMessage } from '@hooks/MessageContext';

// Mock hooks
jest.mock('@api/nabidka/nabidkaAPI');
jest.mock('@api/code_list/code_listAPI');
jest.mock('@hooks/MessageContext');
jest.mock('@hooks/UserProvider', () => ({
    useUser: () => ({ user: null }),
}));
jest.mock('@hooks/useDebounce', () => (value) => value);
jest.mock('@hooks/SearchParams', () => ({
    useCurrentUrl: () => 'http://localhost/nabidka',
    useSetParams: () => jest.fn(),
    useFullUrl: () => 'http://localhost/nabidka',
    useClearParams: () => jest.fn(),
    useStripParams: () => jest.fn(() => ({})),
    makeQuery: () => ''
}));

// Mock child components
jest.mock('@components/Nabidka/NabidkaEntity', () => ({ entity }) => (
    <div data-testid="nabidka-entity">{entity.title}</div>
));
jest.mock('@components/Nabidka/FilterNabidka', () => () => <div data-testid="filter-nabidka">Filter</div>);
jest.mock('@core/Nav', () => () => <nav>Nav</nav>);
jest.mock('@components/core/Pagination', () => () => null);

describe('NabidkaPage', () => {
    const mockGetNabidky = jest.fn();
    const mockGetUniqueLocations = jest.fn();
    const mockGetUniqueSubjects = jest.fn();
    const mockAddMessage = jest.fn();

    beforeEach(() => {
        useNabidkaAPI.mockReturnValue({ getNabidky: mockGetNabidky });
        useCodeListAPI.mockReturnValue({
            getUniqueLocations: mockGetUniqueLocations,
            getUniqueSubjects: mockGetUniqueSubjects
        });
        useMessage.mockReturnValue({ addMessage: mockAddMessage });

        mockGetUniqueLocations.mockResolvedValue(['Prague', 'Brno']);
        mockGetUniqueSubjects.mockResolvedValue(['Math', 'CS']);
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('renders list of offers', async () => {
        const mockData = [
            { practice_id: 1, title: 'Offer 1' },
            { practice_id: 2, title: 'Offer 2' }
        ];
        mockGetNabidky.mockResolvedValue({ results: mockData, count: 2 });

        render(
            <MemoryRouter>
                <NabidkaPage />
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getAllByTestId('nabidka-entity')).toHaveLength(2);
        });
        expect(screen.getByText('Offer 1')).toBeInTheDocument();
        expect(screen.getByText('Offer 2')).toBeInTheDocument();
        expect(mockGetNabidky).toHaveBeenCalled();
    });

    test('renders filter component', async () => {
        mockGetNabidky.mockResolvedValue({ results: [], count: 0 });

        render(
            <MemoryRouter>
                <NabidkaPage />
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByTestId('filter-nabidka')).toBeInTheDocument();
        });
        expect(mockGetUniqueLocations).toHaveBeenCalled();
        expect(mockGetUniqueSubjects).toHaveBeenCalled();
    });

    test('handles empty data', async () => {
        mockGetNabidky.mockResolvedValue({ results: [], count: 0 });

        render(
            <MemoryRouter>
                <NabidkaPage />
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(mockGetNabidky).toHaveBeenCalled();
        });
        expect(screen.queryByTestId('nabidka-entity')).not.toBeInTheDocument();
    });
});
