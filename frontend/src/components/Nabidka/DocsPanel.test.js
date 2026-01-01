import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import DocsPanel from './DocsPanel';
import { useTranslation } from 'react-i18next';
import { useUser } from '@hooks/UserProvider';

jest.mock('react-i18next', () => ({
  useTranslation: jest.fn(),
}));

jest.mock('@hooks/UserProvider', () => ({
  useUser: jest.fn(),
}));

describe('DocsPanel', () => {
  const mockHandleDownload = jest.fn();
  const mockHandleUpload = jest.fn();
  const mockHandleManage = jest.fn();

  const mockEntity = {
    progress_status: true // true for CHECKED, false for NOT_CHECKED
  };

  const mockDocData = [
    { id: 1, type: 'contract' },
    { id: 2, type: 'content' },
    { id: null, type: 'feedback' } // No ID means no document uploaded yet
  ];

  beforeEach(() => {
    useTranslation.mockReturnValue({
      t: (key) => key,
    });
    useUser.mockReturnValue({
      user: {
        isDepartmentMg: jest.fn().mockReturnValue(false),
        isDepartmentUser: jest.fn().mockReturnValue(false),
        isAdmin: jest.fn().mockReturnValue(false)
      }
    });
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  test('renders nothing if docData is not an array', () => {
    const { container } = render(
      <DocsPanel entity={mockEntity} docData={null} />
    );
    expect(container).toBeEmptyDOMElement();
  });

  test('renders document statuses and titles', () => {
    render(
      <DocsPanel
        entity={mockEntity}
        docData={mockDocData}
        handleDownload={mockHandleDownload}
        handleUpload={mockHandleUpload}
        handleManage={mockHandleManage}
      />
    );

    expect(screen.getByText('docs.check_status:')).toBeInTheDocument();
    expect(screen.getByText('docs.checked')).toBeInTheDocument();
    expect(screen.getByText('docs.title')).toBeInTheDocument();

    expect(screen.getByText('docs.contract_draft')).toBeInTheDocument();
    expect(screen.getByText('docs.internship_content')).toBeInTheDocument();
    expect(screen.getByText('docs.feedback')).toBeInTheDocument();
  });

  test('disables buttons when doc ID is missing', () => {
    render(
      <DocsPanel
        entity={mockEntity}
        docData={mockDocData}
        handleDownload={mockHandleDownload}
        handleUpload={mockHandleUpload}
        handleManage={mockHandleManage}
      />
    );

    const downloadButtons = screen.getAllByText('docs.download_file');
    const uploadButtons = screen.getAllByText('docs.upload_file');

    expect(downloadButtons).toHaveLength(3);
    expect(uploadButtons).toHaveLength(3);

    // The third document (feedback) has no ID, so buttons should be disabled
    expect(downloadButtons[0]).not.toBeDisabled();
    expect(downloadButtons[2]).toBeDisabled();

    expect(uploadButtons[0]).not.toBeDisabled();
    expect(uploadButtons[2]).toBeDisabled();
  });

  test('calls handle functions on click', () => {
    render(
      <DocsPanel
        entity={mockEntity}
        docData={mockDocData}
        handleDownload={mockHandleDownload}
        handleUpload={mockHandleUpload}
        handleManage={mockHandleManage}
      />
    );

    const downloadButtons = screen.getAllByText('docs.download_file');
    const uploadButtons = screen.getAllByText('docs.upload_file');

    fireEvent.click(downloadButtons[0]);
    expect(mockHandleDownload).toHaveBeenCalledWith(1);

    fireEvent.click(uploadButtons[1]);
    expect(mockHandleUpload).toHaveBeenCalledWith(2);
  });

  test('renders manage button for department manager', () => {
    useUser.mockReturnValue({
      user: {
        isDepartmentMg: jest.fn().mockReturnValue(true),
        isDepartmentUser: jest.fn().mockReturnValue(true),
        isAdmin: jest.fn().mockReturnValue(false)
      }
    });

    render(
      <DocsPanel
        entity={mockEntity}
        docData={mockDocData}
        handleManage={mockHandleManage}
      />
    );

    const manageButton = screen.getByText('docs.doc_check');
    expect(manageButton).toBeInTheDocument();

    fireEvent.click(manageButton);
    expect(mockHandleManage).toHaveBeenCalled();
  });
});
