import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import NabidkaForm from '@components/Forms/NabidkaForm';

// Mock react-i18next
jest.mock('react-i18next', () => ({
  useTranslation: () => ({ t: (key) => key }),
}));

// Explicit mocks for components used in NabidkaForm
jest.mock('@core/Form/DatePicker', () => ({ id, label, value, onChange }) => (
  <input
    data-testid={`datepicker-${id}`}
    aria-label={label}
    value={value || ''}
    onChange={(e) => onChange({ [id]: e.target.value })}
  />
));

jest.mock('@core/Form/DropDown', () => ({ id, label, options, value, onChange }) => (
  <select
    data-testid={`dropdown-${id}`}
    aria-label={label}
    value={value || ''}
    onChange={(e) => onChange({ [id]: e.target.value })}
  >
    {options.map(opt => (
      <option key={opt.value} value={opt.value}>{opt.label}</option>
    ))}
  </select>
));

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
    expect(screen.getByRole('combobox', { name: 'form.coefficient' })).toBeInTheDocument();
    expect(screen.getByTestId('datepicker-end_date')).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'form.contact_user' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'form.subject' })).toBeInTheDocument();
    expect(screen.getByRole('combobox', { name: 'form.available_positions' })).toBeInTheDocument();
    expect(screen.getByLabelText('form.title')).toBeInTheDocument();
    expect(screen.getByLabelText('form.description')).toBeInTheDocument();
    expect(screen.getByLabelText('form.responsibilities')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /form.create/i })).toBeInTheDocument();
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

    expect(screen.getByLabelText('form.title')).toHaveValue('Test Offer');
    expect(screen.getByLabelText('form.description')).toHaveValue('Test Description');
    expect(screen.getByLabelText('form.responsibilities')).toHaveValue('Test Responsibilities');
    expect(screen.getByLabelText('form.contact_user')).toHaveValue('1'); // value of the selected option
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

    const titleInput = screen.getByLabelText('form.title');
    fireEvent.change(titleInput, { target: { value: 'New Title' } });
    expect(mockHandleChange).toHaveBeenCalledWith({ title: 'New Title' });

    const descriptionInput = screen.getByLabelText('form.description');
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

    const submitButton = screen.getByRole('button', { name: /form.create/i });
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
    expect(screen.getByLabelText('form.title')).toHaveClass('border-red-500'); // Assuming TextField applies this class

    expect(screen.getByText('Popis je povinný.')).toBeInTheDocument();
    expect(screen.getByLabelText('form.description')).toHaveClass('border-red-500'); // Assuming TextBox applies this class
  });
});
