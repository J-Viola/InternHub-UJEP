import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import StudentApplicationCard from './StudentApplicationCard';

// Mock useNavigate
const mockedUsedNavigate = jest.fn();
jest.mock('react-router-dom', () => ({
   ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockedUsedNavigate,
}));

describe('StudentApplicationCard', () => {
    const mockEntity = {
        practice_id: 123,
        practice_title: 'Vývojář Reactu',
        application_date: '01.01.2026',
        company_logo: 'https://example.com/logo.png',
        status: 0 // PENDING
    };

    test('renders application details correctly', () => {
        render(
            <MemoryRouter>
                <StudentApplicationCard entity={mockEntity} />
            </MemoryRouter>
        );

        expect(screen.getByText('Vývojář Reactu')).toBeInTheDocument();
        expect(screen.getByText('Datum podání: 01.01.2026')).toBeInTheDocument();
        expect(screen.getByText('Čeká na schválení')).toBeInTheDocument();
    });

    test('renders approved status correctly', () => {
        const approvedEntity = { ...mockEntity, status: 1 };
        render(
            <MemoryRouter>
                <StudentApplicationCard entity={approvedEntity} />
            </MemoryRouter>
        );

        expect(screen.getByText('Schváleno')).toBeInTheDocument();
    });

    test('renders rejected status correctly', () => {
        const rejectedEntity = { ...mockEntity, status: 2 };
        render(
            <MemoryRouter>
                <StudentApplicationCard entity={rejectedEntity} />
            </MemoryRouter>
        );

        expect(screen.getByText('Zamítnuto')).toBeInTheDocument();
    });

    test('navigates to detail page on click', () => {
        render(
            <MemoryRouter>
                <StudentApplicationCard entity={mockEntity} />
            </MemoryRouter>
        );

        fireEvent.click(screen.getByText('Vývojář Reactu'));
        
        expect(mockedUsedNavigate).toHaveBeenCalledWith('/nabidka/123');
    });
});