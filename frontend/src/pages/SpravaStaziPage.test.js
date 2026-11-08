import React from 'react';
import { fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import SpravaStaziPage from './SpravaStaziPage';
import { useNabidkaAPI } from '@api/nabidka/nabidkaAPI';
import { useUser } from '@hooks/UserProvider';
import { useMessage } from '@hooks/MessageContext';
import { useApi } from '@hooks/useApi';
import { useSubjectAPI } from '@api/subject/subjectAPI';

jest.mock('@api/nabidka/nabidkaAPI');
jest.mock('@hooks/UserProvider');
jest.mock('@hooks/MessageContext');
jest.mock('@hooks/useApi');
jest.mock('@api/subject/subjectAPI');
jest.mock('@core/Button/BackButton', () => () => null);
jest.mock('@components/Praxe/PraxeDepartmentEntity', () => () => null);

const riskTypes = ['APPROVAL_STALLED', 'ENDED_NO_CREDIT', 'OVERDUE_END', 'FUTURE_TYPE', undefined];
const items = riskTypes.map((risk_type, index) => ({
    student_practice_id: index + 1,
    student_name: `Student ${index + 1}`,
    practice_title: `Praxe ${index + 1}`,
    employer_name: 'Firma',
    workflow_state: 'STARTED',
    risk_type,
    risk_reason: `Důvod ${index + 1}`,
}));

async function loadDashboard(total = 60) {
    useNabidkaAPI.mockReturnValue({ getNabidkyByUserDepartment: jest.fn().mockResolvedValue({}) });
    useUser.mockReturnValue({ user: { isAdmin: () => false } });
    useMessage.mockReturnValue({ addMessage: jest.fn() });
    useSubjectAPI.mockReturnValue({
        getDepartmentSubjects: jest.fn().mockResolvedValue([{ subject_id: 7, subject_name: 'Odborná praxe' }]),
    });
    useApi.mockReturnValue({ get: jest.fn().mockResolvedValue({ data: { at_risk_items: items, at_risk_count: total } }) });
    render(<MemoryRouter><SpravaStaziPage /></MemoryRouter>);
    return screen.findByRole('region', { name: 'Praxe vyžadující pozornost' });
}

test('rozlišuje všechny typy rizika textem a ikonou, neznámé a chybějící typy neutrálně', async () => {
    const panel = await loadDashboard();
    const rows = within(panel).getAllByRole('listitem');
    const labels = ['Zdlouhavé schvalování', 'Ukončeno bez zápočtu déle než 14 dní', 'Po termínu ukončení', 'Jiné upozornění', 'Jiné upozornění'];
    labels.forEach((label, index) => {
        expect(within(rows[index]).getByText(label)).toBeInTheDocument();
        expect(within(rows[index]).getByText(`Důvod ${index + 1}`)).toBeInTheDocument();
        expect(within(rows[index]).getByText(index < 3 ? '⚠' : 'ⓘ')).toHaveAttribute('aria-hidden', 'true');
    });
    expect(within(rows[3]).getByText('Jiné upozornění')).toHaveClass('text-gray-800');
    expect(within(rows[4]).getByText('Jiné upozornění')).toHaveClass('text-gray-800');
});

test('uvádí zobrazený a skutečný počet, když je seznam zkrácený', async () => {
    const panel = await loadDashboard();
    expect(within(panel).getByText('Zobrazeno 5 z 60')).toBeInTheDocument();
});

test('neuvádí zkrácení při úplném seznamu', async () => {
    const panel = await loadDashboard(items.length);
    expect(within(panel).queryByText(/Zobrazeno/)).not.toBeInTheDocument();
});

describe('filtry exportu', () => {
    let createObjectURL;
    let revokeObjectURL;

    beforeEach(() => {
        createObjectURL = window.URL.createObjectURL;
        revokeObjectURL = window.URL.revokeObjectURL;
        window.URL.createObjectURL = jest.fn().mockReturnValue('blob:export');
        window.URL.revokeObjectURL = jest.fn();
        jest.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => {});
    });

    afterEach(() => {
        window.URL.createObjectURL = createObjectURL;
        window.URL.revokeObjectURL = revokeObjectURL;
        jest.restoreAllMocks();
    });

    function exportResponse(status = 200) {
        const api = useApi.mock.results[useApi.mock.results.length - 1].value;
        api.get.mockResolvedValue({ status, data: new Blob(['data']), headers: {} });
        return api.get;
    }

    test.each(['XLSX', 'CSV'])('export %s bez filtrů zachová autorizovaný blob download', async (format) => {
        await loadDashboard();
        const get = exportResponse();
        fireEvent.click(screen.getByRole('button', { name: `Export ${format}` }));
        await waitFor(() => expect(get).toHaveBeenCalledWith('/export-data/', {
            params: { format: format.toLowerCase() }, responseType: 'blob',
        }));
        await waitFor(() => expect(window.URL.revokeObjectURL).toHaveBeenCalledWith('blob:export'));
        expect(HTMLAnchorElement.prototype.click).toHaveBeenCalledTimes(1);
    });

    test.each([200, 202])('posílá všechny vyplněné filtry přes params i pro HTTP %s', async (status) => {
        await loadDashboard();
        await screen.findByRole('option', { name: 'Odborná praxe' });
        const get = exportResponse(status);
        fireEvent.change(screen.getByLabelText('Rok'), { target: { value: '2026' } });
        fireEvent.change(screen.getByLabelText('Stav praxe'), { target: { value: '4' } });
        fireEvent.change(screen.getByLabelText('Předmět'), { target: { value: '7' } });
        fireEvent.change(screen.getByLabelText('Instituce'), { target: { value: '  Firma & syn  ' } });
        fireEvent.click(screen.getByRole('button', { name: 'Export CSV' }));
        await waitFor(() => expect(get).toHaveBeenCalledWith('/export-data/', {
            params: { format: 'csv', year: '2026', workflow_state: '4', subject_id: '7', institution: 'Firma & syn' },
            responseType: 'blob',
        }));
        const expectedMessage = status === 202 ? 'Export se zpracovává. Budete notifikováni po dokončení.' : 'Export CSV byl úspěšně vygenerován.';
        await waitFor(() => expect(useMessage.mock.results[useMessage.mock.results.length - 1].value.addMessage)
            .toHaveBeenCalledWith(expectedMessage, status === 202 ? 'I' : 'S'));
        expect(window.URL.createObjectURL).toHaveBeenCalledTimes(status === 202 ? 0 : 1);
    });

    test('vymazané hodnoty a samotné mezery neposílá', async () => {
        await loadDashboard();
        await screen.findByRole('option', { name: 'Odborná praxe' });
        const get = exportResponse();
        for (const [label, value] of [['Rok', '2026'], ['Stav praxe', '6'], ['Předmět', '7']]) {
            fireEvent.change(screen.getByLabelText(label), { target: { value } });
            fireEvent.change(screen.getByLabelText(label), { target: { value: '' } });
        }
        fireEvent.change(screen.getByLabelText('Instituce'), { target: { value: '   ' } });
        fireEvent.click(screen.getByRole('button', { name: 'Export XLSX' }));
        await waitFor(() => expect(get).toHaveBeenCalledWith('/export-data/', {
            params: { format: 'xlsx' }, responseType: 'blob',
        }));
    });
});
