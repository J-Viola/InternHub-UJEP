import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LoginForm from './LoginForm';

describe('LoginForm', () => {
    test('allows typing in email and password fields', () => {
        render(
            <MemoryRouter>
                <LoginForm handleSTAGLogin={() => {}} handleOrganizationLogin={() => {}} />
            </MemoryRouter>
        );

        // Switch to Company login first
        const companySwitch = screen.getByText('login.i_am_firma');
        fireEvent.click(companySwitch);

        const emailInput = screen.getByPlaceholderText('login.email');
        const passwordInput = screen.getByPlaceholderText('*****');

        fireEvent.change(emailInput, { target: { value: 'test@firma.cz' } });
        fireEvent.change(passwordInput, { target: { value: 'heslo123' } });

        expect(emailInput.value).toBe('test@firma.cz');
        expect(passwordInput.value).toBe('heslo123');
    });

    test('switches between STAG and Organization login', () => {
        render(
            <MemoryRouter>
                <LoginForm handleSTAGLogin={() => {}} handleOrganizationLogin={() => {}} />
            </MemoryRouter>
        );

        // Default is STAG
        expect(screen.getByText('login.stag_info')).toBeInTheDocument();

        // Switch to Company login
        const companySwitch = screen.getByText('login.i_am_firma');
        fireEvent.click(companySwitch);

        expect(screen.getByPlaceholderText('login.email')).toBeInTheDocument();
        expect(screen.queryByText('login.stag_info')).not.toBeInTheDocument();

        // Switch back to STAG
        const stagSwitch = screen.getByText('login.stag_label');
        fireEvent.click(stagSwitch);

        expect(screen.queryByPlaceholderText('login.email')).not.toBeInTheDocument();
        expect(screen.getByText('login.stag_info')).toBeInTheDocument();
    });
});
