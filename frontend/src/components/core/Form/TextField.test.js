import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import TextField from './TextField';

describe('TextField Component', () => {
  test('renders label and input', () => {
    render(<TextField id="test-input" label="Test Label" />);

    expect(screen.getByLabelText("Test Label")).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  test('calls onChange callback when typing', () => {
    const handleChange = jest.fn();
    render(<TextField id="test-input" label="Test Label" onChange={handleChange} />);

    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'Hello' } });

    expect(handleChange).toHaveBeenCalledTimes(1);
    // TextField vrací objekt {id: value}
    expect(handleChange).toHaveBeenCalledWith({ "test-input": 'Hello' });
  });

  test('displays error message when error prop is provided', () => {
    const errorMessage = "Toto pole je povinné";
    render(<TextField id="test-input" label="Test Label" error={errorMessage} />);

    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    // Ověření, že error má červenou barvu (třída text-red-500)
    expect(screen.getByText(errorMessage)).toHaveClass('text-red-500');
  });

  test('changes border color when error is present', () => {
    render(<TextField id="test-input" label="Test Label" error="Error" />);
    const input = screen.getByRole('textbox');
    // Ověření, že input má červený border
    expect(input).toHaveClass('border-red-500');
  });

  test('toggles password visibility', () => {
    render(<TextField id="password-input" label="Password" type="password" />);

    const input = screen.getByLabelText("Password");
    expect(input).toHaveAttribute('type', 'password');

    // Najdeme tlačítko pro zobrazení hesla (podle ikony nebo role button)
    // TextField používá Button komponentu, která renderuje <button>
    const toggleButton = screen.getByRole('button');
    fireEvent.click(toggleButton);

    expect(input).toHaveAttribute('type', 'text');

    fireEvent.click(toggleButton);
    expect(input).toHaveAttribute('type', 'password');
  });
});
