/**
 * BL-05 / RF-02a — end-to-end wiring: volba „typ úvazku" ve filtru nabídek
 * se propsílá jako query param `employment_type` do backendového
 * GET /api/practices/student/ (PracticeFilter.employment_type).
 */
import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import NabidkaPage from './NabidkaPage';
import { useNabidkaAPI } from '@api/nabidka/nabidkaAPI';
import { useCodeListAPI } from '@api/code_list/code_listAPI';
import { useMessage } from '@hooks/MessageContext';

// Factory mocky (bez automocku) — jinak se načte reálný řetězec
jest.mock('@api/nabidka/nabidkaAPI', () => ({ useNabidkaAPI: jest.fn() }));
jest.mock('@api/code_list/code_listAPI', () => ({ useCodeListAPI: jest.fn() }));
jest.mock('@hooks/MessageContext', () => ({ useMessage: jest.fn() }));
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

// Lehké náhrady za těžké dětské komponenty (NabidkaPage test je jinak mockuje);
// nativní <select> filtry (včetně employment_type) zůstávají skutečné.
jest.mock('@components/Nabidka/NabidkaEntity', () => ({ entity }) => (
    <div data-testid="nabidka-entity">{entity.title}</div>
));
jest.mock('@components/core/Pagination', () => () => null);
jest.mock('@components/Filter/SearchBar', () => ({ id, value = '', placeholder, onChange }) => (
    <input data-testid={`search-${id}`} value={value} placeholder={placeholder} onChange={onChange} />
));
jest.mock('@core/Button/Button', () => ({ children, onClick }) => (
    <button type="button" onClick={onClick}>{children}</button>
));
jest.mock('@core/Form/DropDown', () => ({ id, value = '', options = [], onChange }) => (
    <select
        data-testid={`dropdown-${id}`}
        value={value}
        onChange={(e) => onChange({ [id]: e.target.value })}
    >
        {(options || []).map((opt, idx) => (
            <option key={idx} value={opt.value ?? opt}>{opt.label ?? opt}</option>
        ))}
    </select>
));

describe('NabidkaPage — odeslání filtru úvazku do API', () => {
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

        mockGetNabidky.mockResolvedValue({ results: [], count: 0 });
        mockGetUniqueLocations.mockResolvedValue(['Praha']);
        mockGetUniqueSubjects.mockResolvedValue([{ value: '1', label: 'Java' }]);
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    const renderPage = () =>
        render(
            <MemoryRouter>
                <NabidkaPage />
            </MemoryRouter>
        );

    test('vybraný typ úvazku se po kliknutí na Hledat odešle jako employment_type param', async () => {
        renderPage();

        await waitFor(() => expect(mockGetNabidky).toHaveBeenCalled());

        const select = screen.getByLabelText(/Typ úvazku/);
        fireEvent.change(select, { target: { value: 'uvazek_0_5' } });
        fireEvent.click(screen.getByText("Hledat"));

        await waitFor(() =>
            expect(mockGetNabidky).toHaveBeenLastCalledWith(
                expect.objectContaining({ employment_type: 'uvazek_0_5' })
            )
        );

        const lastParams = mockGetNabidky.mock.calls[mockGetNabidky.mock.calls.length - 1][0];
        expect(lastParams.page_size).toBe(10);
        expect(lastParams).not.toHaveProperty('min_duration');
    });

    test('změna úvazku na „Všechny" param employment_type z dotazu odebere', async () => {
        renderPage();

        await waitFor(() => expect(mockGetNabidky).toHaveBeenCalled());

        const select = screen.getByLabelText(/Typ úvazku/);
        fireEvent.change(select, { target: { value: 'uvazek_1_0' } });
        fireEvent.click(screen.getByText("Hledat"));
        await waitFor(() =>
            expect(mockGetNabidky).toHaveBeenLastCalledWith(
                expect.objectContaining({ employment_type: 'uvazek_1_0' })
            )
        );

        fireEvent.change(select, { target: { value: '' } });
        fireEvent.click(screen.getByText("Hledat"));
        await waitFor(() => {
            const lastParams = mockGetNabidky.mock.calls[mockGetNabidky.mock.calls.length - 1][0];
            expect(lastParams).not.toHaveProperty('employment_type');
        });
    });
});
