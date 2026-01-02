import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import RegistracePage from './RegistracePage';
import { useUserAPI } from '@api/user/userAPI';
import { useAuth } from '@auth/Auth';
import { useMessage } from '@hooks/MessageContext';

// Mock hooks
jest.mock('@api/user/userAPI');
jest.mock('@auth/Auth');
jest.mock('@hooks/MessageContext');

// Mock child components
jest.mock('@components/Forms/CompanyForm', () => ({ handleCreate, errors }) => (
    <div data-testid="company-form">
        <button onClick={() => handleCreate({ 
            executiveEmail: 'boss@test.com', 
            executivePassword1: 'pass123',
            companyName: 'Test Corp'
        })}>
            Register
        </button>
        {errors && errors.detail && <span>{errors.detail}</span>}
    </div>
));
jest.mock('@core/Button/BackButton', () => () => <button>Back</button>);

describe('RegistracePage', () => {
    const mockPostRegister = jest.fn();
    const mockLogin = jest.fn();
    const mockAddMessage = jest.fn();

    beforeEach(() => {
        useUserAPI.mockReturnValue({ postRegister: mockPostRegister });
        useAuth.mockReturnValue({ login: mockLogin });
        useMessage.mockReturnValue({ addMessage: mockAddMessage });
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('handles successful registration and auto-login', async () => {
        mockPostRegister.mockResolvedValue({ status: 201 });
        mockLogin.mockResolvedValue({ status: 200 });

        render(
            <MemoryRouter>
                <RegistracePage />
            </MemoryRouter>
        );

        const registerBtn = screen.getByText('Register');
        registerBtn.click();

        await waitFor(() => {
            expect(mockPostRegister).toHaveBeenCalledWith(expect.objectContaining({
                companyName: 'Test Corp'
            }));
            expect(mockAddMessage).toHaveBeenCalledWith('Registrace úspěšná', 'S');
            expect(mockLogin).toHaveBeenCalledWith({
                email: 'boss@test.com',
                password: 'pass123'
            });
        });
    });

    test('handles registration failure', async () => {
        mockPostRegister.mockRejectedValue({
            response: { data: { detail: 'Email already exists' } }
        });

        render(
            <MemoryRouter>
                <RegistracePage />
            </MemoryRouter>
        );

        const registerBtn = screen.getByText('Register');
        registerBtn.click();

        await waitFor(() => {
            expect(mockAddMessage).toHaveBeenCalledWith('Chyba při registraci: Email already exists', 'E');
            expect(screen.getByText('Email already exists')).toBeInTheDocument();
        });
    });
});
