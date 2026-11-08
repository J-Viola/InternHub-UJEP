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
        const companySwitch = screen.getByText("Jsem firma");
        fireEvent.click(companySwitch);

        const emailInput = screen.getByPlaceholderText("E-mail");
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
        expect(screen.getByText("Přihlášení pomocí systému STAG příslušné univerzity.")).toBeInTheDocument();

        // Switch to Company login
        const companySwitch = screen.getByText("Jsem firma");
        fireEvent.click(companySwitch);

        expect(screen.getByPlaceholderText("E-mail")).toBeInTheDocument();
        expect(screen.queryByText("Přihlášení pomocí systému STAG příslušné univerzity.")).not.toBeInTheDocument();

        // Switch back to STAG
        const stagSwitch = screen.getByText("STAG");
        fireEvent.click(stagSwitch);

        expect(screen.queryByPlaceholderText("E-mail")).not.toBeInTheDocument();
        expect(screen.getByText("Přihlášení pomocí systému STAG příslušné univerzity.")).toBeInTheDocument();
    });
});
