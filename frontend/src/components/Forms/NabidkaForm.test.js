import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import NabidkaForm from '@components/Forms/NabidkaForm'; // Cesta k NabidkaForm.js

describe('NabidkaForm Component', () => {
  const mockOrganizationUsers = [
    { label: 'User 1', value: 1 },
    { label: 'User 2', value: 2 },
  ];
  const mockSubjects = [
    { label: 'Subject A', value: 101 },
    { label: 'Subject B', value: 102 },
  ];
  const mockFormData = {
    start_date: '01.01.2025',
    coefficient: '1',
    contact_user: 1,
    subject_id: 101,
    available_positions: '5',
    title: 'Test Offer',
    description: 'Test Description',
    responsibilities: 'Test Responsibilities',
  };
  const mockHandleChange = jest.fn();
  const mockHandleSubmit = jest.fn();

  test('renders all form fields', () => {
    render(
        <NabidkaForm
          organizationUsers={mockOrganizationUsers}
          subjects={mockSubjects}
          formData={mockFormData}
          handleChange={mockHandleChange}
          handleSubmit={mockHandleSubmit}
        />
    );

    expect(screen.getByTestId('datepicker-start_date')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Úvazek' })).toBeInTheDocument();
    expect(screen.getByTestId('datepicker-end_date')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Správce inzerátu' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Přiřazený předmět' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'Počet volných míst' })).toBeInTheDocument();
    expect(screen.getByLabelText('Název')).toBeInTheDocument();
    expect(screen.getByLabelText('Popis stáže')).toBeInTheDocument();
    expect(screen.getByLabelText('Odpovědnost stáže')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Vytvořit/i })).toBeInTheDocument();
  });

  test('displays form data correctly', () => {
    render(
        <NabidkaForm
          organizationUsers={mockOrganizationUsers}
          subjects={mockSubjects}
          formData={mockFormData}
          handleChange={mockHandleChange}
          handleSubmit={mockHandleSubmit}
        />
    );

    expect(screen.getByLabelText('Název')).toHaveValue('Test Offer');
    expect(screen.getByLabelText('Popis stáže')).toHaveValue('Test Description');
    expect(screen.getByLabelText('Odpovědnost stáže')).toHaveValue('Test Responsibilities');
    expect(screen.getByLabelText('Správce inzerátu')).toHaveValue('1'); // value of the selected option
  });

  test('calls handleChange on input change', () => {
    render(
        <NabidkaForm
          organizationUsers={mockOrganizationUsers}
          subjects={mockSubjects}
          formData={mockFormData}
          handleChange={mockHandleChange}
          handleSubmit={mockHandleSubmit}
        />
    );

    const titleInput = screen.getByLabelText('Název');
    fireEvent.change(titleInput, { target: { value: 'New Title' } });
    expect(mockHandleChange).toHaveBeenCalledWith({ title: 'New Title' });

    const descriptionInput = screen.getByLabelText('Popis stáže');
    fireEvent.change(descriptionInput, { target: { value: 'New Description' } });
    expect(mockHandleChange).toHaveBeenCalledWith({ description: 'New Description' });
  });

  test('calls handleSubmit on button click', () => {
    render(
        <NabidkaForm
          organizationUsers={mockOrganizationUsers}
          subjects={mockSubjects}
          formData={mockFormData}
          handleChange={mockHandleChange}
          handleSubmit={mockHandleSubmit}
        />
    );

    const submitButton = screen.getByRole('button', { name: /Vytvořit/i });
    fireEvent.click(submitButton);
    expect(mockHandleSubmit).toHaveBeenCalledTimes(1);
  });

  test('displays errors for specific fields', () => {
    const mockErrors = {
      title: 'Název je povinný.',
      description: 'Popis je povinný.',
    };
    render(
        <NabidkaForm
          organizationUsers={mockOrganizationUsers}
          subjects={mockSubjects}
          formData={{}} // Prázdná data pro zobrazení chyb
          handleChange={mockHandleChange}
          handleSubmit={mockHandleSubmit}
          errors={mockErrors}
        />
    );

    expect(screen.getByText('Název je povinný.')).toBeInTheDocument();
    expect(screen.getByLabelText('Název')).toHaveClass('border-red-500'); // Assuming TextField applies this class
    
    expect(screen.getByText('Popis je povinný.')).toBeInTheDocument();
    expect(screen.getByLabelText('Popis stáže')).toHaveClass('border-red-500'); // Assuming TextBox applies this class
  });
});
