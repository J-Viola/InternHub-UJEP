import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import LanguageSwitcher from './LanguageSwitcher';
import { useTranslation } from 'react-i18next';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: jest.fn(),
}));

describe('LanguageSwitcher', () => {
  const mockChangeLanguage = jest.fn();

  beforeEach(() => {
    useTranslation.mockReturnValue({
      i18n: {
        language: 'cs',
        changeLanguage: mockChangeLanguage,
      },
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('renders current language correctly', () => {
    render(<LanguageSwitcher />);
    expect(screen.getByText('CS')).toBeInTheDocument();
    expect(screen.getByText('🇨🇿')).toBeInTheDocument();
  });

  test('opens dropdown on click', () => {
    render(<LanguageSwitcher />);

    // Initially dropdown is closed
    expect(screen.queryByText('Čeština')).not.toBeInTheDocument();
    expect(screen.queryByText('English')).not.toBeInTheDocument();

    // Click to open
    const button = screen.getByRole('button');
    fireEvent.click(button);

    // Dropdown options should be visible
    expect(screen.getByText('Čeština')).toBeInTheDocument();
    expect(screen.getByText('English')).toBeInTheDocument();
  });

  test('changes language on option click', () => {
    render(<LanguageSwitcher />);

    // Open dropdown
    const button = screen.getByRole('button');
    fireEvent.click(button);

    // Click English option
    const enOption = screen.getByText('English');
    fireEvent.click(enOption);

    expect(mockChangeLanguage).toHaveBeenCalledWith('en');
  });

  test('closes dropdown when clicking outside', () => {
    render(
      <div>
        <div data-testid="outside">Outside Element</div>
        <LanguageSwitcher />
      </div>
    );

    // Open dropdown
    const button = screen.getByRole('button');
    fireEvent.click(button);
    expect(screen.getByText('English')).toBeInTheDocument();

    // Click outside
    fireEvent.mouseDown(screen.getByTestId('outside'));

    // Dropdown should be closed
    expect(screen.queryByText('English')).not.toBeInTheDocument();
  });
});
