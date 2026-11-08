import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Pagination from './Pagination';


describe('Pagination', () => {
  test('does not render if totalPages is 0 or 1', () => {
    const { container } = render(<Pagination currentPage={1} totalPages={1} onPageChange={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  test('renders correctly for multiple pages', () => {
    render(<Pagination currentPage={2} totalPages={5} onPageChange={() => {}} />);

    expect(screen.getByRole('button', { name: /Předchozí/ })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Další/ })).toBeInTheDocument();
    expect(screen.getByText(/Strana/).textContent).toBe('Strana 2 / 5');
  });

  test('disables previous button on first page', () => {
    render(<Pagination currentPage={1} totalPages={5} onPageChange={() => {}} />);

    const prevButton = screen.getByRole('button', { name: /Předchozí/ });
    expect(prevButton).toBeDisabled();

    const nextButton = screen.getByRole('button', { name: /Další/ });
    expect(nextButton).not.toBeDisabled();
  });

  test('disables next button on last page', () => {
    render(<Pagination currentPage={5} totalPages={5} onPageChange={() => {}} />);

    const prevButton = screen.getByRole('button', { name: /Předchozí/ });
    expect(prevButton).not.toBeDisabled();

    const nextButton = screen.getByRole('button', { name: /Další/ });
    expect(nextButton).toBeDisabled();
  });

  test('calls onPageChange when buttons are clicked', () => {
    const mockOnPageChange = jest.fn();
    render(<Pagination currentPage={3} totalPages={5} onPageChange={mockOnPageChange} />);

    fireEvent.click(screen.getByRole('button', { name: /Předchozí/ }));
    expect(mockOnPageChange).toHaveBeenCalledWith(2);

    fireEvent.click(screen.getByRole('button', { name: /Další/ }));
    expect(mockOnPageChange).toHaveBeenCalledWith(4);
  });
});
