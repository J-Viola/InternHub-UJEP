import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import Pagination from './Pagination';
import { useTranslation } from 'react-i18next';

jest.mock('react-i18next', () => ({
  useTranslation: jest.fn(),
}));

describe('Pagination', () => {
  beforeEach(() => {
    useTranslation.mockReturnValue({
      t: (key) => key,
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('does not render if totalPages is 0 or 1', () => {
    const { container } = render(<Pagination currentPage={1} totalPages={1} onPageChange={() => {}} />);
    expect(container).toBeEmptyDOMElement();
  });

  test('renders correctly for multiple pages', () => {
    render(<Pagination currentPage={2} totalPages={5} onPageChange={() => {}} />);

    expect(screen.getByText('← pagination.previous')).toBeInTheDocument();
    expect(screen.getByText('pagination.next →')).toBeInTheDocument();
    expect(screen.getByText('pagination.page 2 / 5')).toBeInTheDocument();
  });

  test('disables previous button on first page', () => {
    render(<Pagination currentPage={1} totalPages={5} onPageChange={() => {}} />);

    const prevButton = screen.getByText('← pagination.previous');
    expect(prevButton).toBeDisabled();

    const nextButton = screen.getByText('pagination.next →');
    expect(nextButton).not.toBeDisabled();
  });

  test('disables next button on last page', () => {
    render(<Pagination currentPage={5} totalPages={5} onPageChange={() => {}} />);

    const prevButton = screen.getByText('← pagination.previous');
    expect(prevButton).not.toBeDisabled();

    const nextButton = screen.getByText('pagination.next →');
    expect(nextButton).toBeDisabled();
  });

  test('calls onPageChange when buttons are clicked', () => {
    const mockOnPageChange = jest.fn();
    render(<Pagination currentPage={3} totalPages={5} onPageChange={mockOnPageChange} />);

    fireEvent.click(screen.getByText('← pagination.previous'));
    expect(mockOnPageChange).toHaveBeenCalledWith(2);

    fireEvent.click(screen.getByText('pagination.next →'));
    expect(mockOnPageChange).toHaveBeenCalledWith(4);
  });
});
