import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import LoginPage from './LoginPage';
import { useAuth } from '@auth/Auth';
import { useMessage } from '@hooks/MessageContext';
import { useUser } from '@hooks/UserProvider';
import { STAGLogin } from '@auth/STAGLogin';

// Mock hooks
jest.mock('@auth/Auth');
jest.mock('@hooks/MessageContext');
jest.mock('@hooks/UserProvider');
jest.mock('@auth/STAGLogin');

describe('LoginPage', () => {
    const mockLogin = jest.fn();
    const mockAddMessage = jest.fn();
    const mockUser = { hasData: jest.fn(() => false) };

    beforeEach(() => {
        useAuth.mockReturnValue({ login: mockLogin, isInitializing: false });
        useMessage.mockReturnValue({ addMessage: mockAddMessage });
        useUser.mockReturnValue({ user: mockUser });
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('renders STAG login by default', () => {
        render(
            <MemoryRouter initialEntries={['/login']}>
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                </Routes>
            </MemoryRouter>
        );

        expect(screen.getByText("Přihlášení pomocí systému STAG příslušné univerzity.")).toBeInTheDocument();
        expect(screen.getAllByText("Přihlaste se")[0]).toBeInTheDocument();
    });

    test('initiates STAG login on button click', async () => {
        render(
            <MemoryRouter initialEntries={['/login']}>
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                </Routes>
            </MemoryRouter>
        );

        fireEvent.click(screen.getAllByText("Přihlaste se")[0]);
        expect(STAGLogin).toHaveBeenCalled();
    });

    test('switches to organization login and submits', async () => {
        render(
            <MemoryRouter initialEntries={['/login']}>
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                </Routes>
            </MemoryRouter>
        );

        // Switch to "Jsem firma" (using its translation key)
        fireEvent.click(screen.getByText("Jsem firma"));

        expect(screen.getByLabelText("E-mail")).toBeInTheDocument();
        expect(screen.getByLabelText("Heslo")).toBeInTheDocument();

        fireEvent.change(screen.getByLabelText("E-mail"), { target: { value: 'org@test.com' } });
        fireEvent.change(screen.getByLabelText("Heslo"), { target: { value: 'password123' } });

        mockLogin.mockResolvedValue({ status: 200 });

        fireEvent.click(screen.getAllByText("Přihlaste se")[0]);

        await waitFor(() => {
            expect(mockLogin).toHaveBeenCalledWith({ email: 'org@test.com', password: 'password123' });
        });
    });
});
