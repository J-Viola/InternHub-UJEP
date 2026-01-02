import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, useSearchParams } from 'react-router-dom';
import LoginPage from './LoginPage';
import { useAuth } from '@auth/Auth';
import { useMessage } from '@hooks/MessageContext';
import { STAGLogin } from '@auth/STAGLogin';

// Mock hooks
jest.mock('@auth/Auth');
jest.mock('@hooks/MessageContext');
jest.mock('@auth/STAGLogin');
jest.mock('react-router-dom', () => ({
    ...jest.requireActual('react-router-dom'),
    useSearchParams: jest.fn()
}));

// Mock child components
jest.mock('@core/Form/TextField', () => ({ id, label, onChange, type }) => (
    <div>
        <label htmlFor={id}>{label}</label>
        <input id={id} type={type} onChange={(e) => onChange({ [id]: e.target.value })} />
    </div>
));

describe('LoginPage', () => {
    const mockLogin = jest.fn();
    const mockAddMessage = jest.fn();
    let mockSearchParams = new URLSearchParams();

    beforeEach(() => {
        useAuth.mockReturnValue({ login: mockLogin });
        useMessage.mockReturnValue({ addMessage: mockAddMessage });
        useSearchParams.mockReturnValue([mockSearchParams, jest.fn()]);
    });

    afterEach(() => {
        jest.clearAllMocks();
        mockSearchParams = new URLSearchParams();
    });

    test('renders STAG login by default', () => {
        render(
            <MemoryRouter>
                <LoginPage />
            </MemoryRouter>
        );

        expect(screen.getByText('Přihlášení pomocí systému STAG příslušné univerzity.')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /Přihlaste se/i })).toBeInTheDocument();
    });

    test('initiates STAG login on button click', async () => {
        render(
            <MemoryRouter>
                <LoginPage />
            </MemoryRouter>
        );

        fireEvent.click(screen.getByRole('button', { name: /Přihlaste se/i }));
        expect(STAGLogin).toHaveBeenCalled();
    });

    test('auto-logins when ticket is present in URL', async () => {
        mockSearchParams.set('stagUserTicket', 'test-ticket');
        
        render(
            <MemoryRouter initialEntries={['/?stagUserTicket=test-ticket']}>
                <LoginPage />
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(mockLogin).toHaveBeenCalledWith({ service_ticket: 'test-ticket' });
        });
    });

    test('switches to organization login and submits', async () => {
        render(
            <MemoryRouter>
                <LoginPage />
            </MemoryRouter>
        );

        // Switch to "Jsem firma" (Department switch)
        fireEvent.click(screen.getByText('Jsem firma'));

        expect(screen.getByLabelText('E-mail')).toBeInTheDocument();
        expect(screen.getByLabelText('Heslo')).toBeInTheDocument();

        fireEvent.change(screen.getByLabelText('E-mail'), { target: { value: 'org@test.com' } });
        fireEvent.change(screen.getByLabelText('Heslo'), { target: { value: 'password123' } });

        mockLogin.mockResolvedValue({ status: 200 });

        fireEvent.click(screen.getByRole('button', { name: /Přihlaste se/i }));

        await waitFor(() => {
            expect(mockLogin).toHaveBeenCalledWith({ email: 'org@test.com', password: 'password123' });
        });
    });

    test('displays error message on failed login', async () => {
        render(
            <MemoryRouter>
                <LoginPage />
            </MemoryRouter>
        );

        fireEvent.click(screen.getByText('Jsem firma'));
        
        mockLogin.mockRejectedValue({
            response: { data: { detail: 'Invalid credentials' } }
        });

        fireEvent.click(screen.getByRole('button', { name: /Přihlaste se/i }));

        await waitFor(() => {
            expect(mockAddMessage).toHaveBeenCalledWith('Chyba při přihlášení: Invalid credentials', 'E');
        });
    });
});
