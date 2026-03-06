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

        expect(screen.getByText('login.stag_info')).toBeInTheDocument();
        expect(screen.getAllByText('login.login_button')[0]).toBeInTheDocument();
    });

    test('initiates STAG login on button click', async () => {
        render(
            <MemoryRouter initialEntries={['/login']}>
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                </Routes>
            </MemoryRouter>
        );

        fireEvent.click(screen.getAllByText('login.login_button')[0]);
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
        fireEvent.click(screen.getByText('login.i_am_firma'));

        expect(screen.getByLabelText('login.email')).toBeInTheDocument();
        expect(screen.getByLabelText('login.password')).toBeInTheDocument();

        fireEvent.change(screen.getByLabelText('login.email'), { target: { value: 'org@test.com' } });
        fireEvent.change(screen.getByLabelText('login.password'), { target: { value: 'password123' } });

        mockLogin.mockResolvedValue({ status: 200 });

        fireEvent.click(screen.getAllByText('login.login_button')[0]);

        await waitFor(() => {
            expect(mockLogin).toHaveBeenCalledWith({ email: 'org@test.com', password: 'password123' });
        });
    });
});
