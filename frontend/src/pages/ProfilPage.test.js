import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ProfilPage from './ProfilPage';
import { useUserAPI } from '@api/user/userAPI';
import { useMessage } from '@hooks/MessageContext';
import { useApi } from '@hooks/useApi';
import { fireEvent } from '@testing-library/react';

// Mock hooks
jest.mock('@api/user/userAPI');
jest.mock('@hooks/MessageContext');
jest.mock('@hooks/useApi');

// Mock child components
jest.mock('@components/Forms/ProfileForm', () => () => <div data-testid="profile-form">Profile Form</div>);
jest.mock('@core/Button/BackButton', () => () => <button>Back</button>);
jest.mock('@core/Nav', () => () => <nav>Nav</nav>);

describe('ProfilPage', () => {
    const mockGetCurrentUserProfile = jest.fn();
    const mockGetStudentProfile = jest.fn();
    const mockUpdateProfile = jest.fn();
    const mockAddMessage = jest.fn();
    const mockApiGet = jest.fn();

    const mockStudent = {
        user_id: 1,
        first_name: 'Jan',
        last_name: 'Student',
        email: 'jan@test.com',
        user_type: 'student',
        skills: ['React', 'Jest'],
        full_name: 'Jan Student'
    };

    beforeEach(() => {
        useUserAPI.mockReturnValue({
            getCurrentUserProfile: mockGetCurrentUserProfile,
            getStudentProfile: mockGetStudentProfile,
            updateProfile: mockUpdateProfile
        });
        useMessage.mockReturnValue({ addMessage: mockAddMessage });
        useApi.mockReturnValue({ get: mockApiGet });
    });

    afterEach(() => {
        jest.clearAllMocks();
    });

    test('renders loading state initially', async () => {
        mockGetCurrentUserProfile.mockReturnValue(new Promise(() => {})); // Never resolves
        render(
            <MemoryRouter initialEntries={['/profil']}>
                <Routes>
                    <Route path="/profil" element={<ProfilPage />} />
                </Routes>
            </MemoryRouter>
        );

        expect(screen.getByText('common.loading')).toBeInTheDocument();
    });

    test('renders own profile details', async () => {
        mockGetCurrentUserProfile.mockResolvedValue(mockStudent);

        render(
            <MemoryRouter initialEntries={['/profil']}>
                <Routes>
                    <Route path="/profil" element={<ProfilPage />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.queryByText('common.loading')).not.toBeInTheDocument();
        });

        expect(screen.getByText('Jan Student')).toBeInTheDocument();
        expect(screen.getAllByText('jan@test.com')[0]).toBeInTheDocument();
        expect(screen.getByText('React')).toBeInTheDocument();
        expect(screen.getByText('Jest')).toBeInTheDocument();
    });

    test('renders other student profile when ID is provided', async () => {
        mockGetStudentProfile.mockResolvedValue({ ...mockStudent, first_name: 'Petr', full_name: 'Petr Student' });

        render(
            <MemoryRouter initialEntries={['/profil/2']}>
                <Routes>
                    <Route path="/profil/:id" element={<ProfilPage />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(mockGetStudentProfile).toHaveBeenCalledWith('2');
        });
        await waitFor(() => {
            expect(screen.getByText('Petr Student')).toBeInTheDocument();
        });
    });

    test('renders edit form when edit query param is true', async () => {
        mockGetCurrentUserProfile.mockResolvedValue(mockStudent);

        render(
            <MemoryRouter initialEntries={['/profil?edit=true']}>
                <Routes>
                    <Route path="/profil" element={<ProfilPage />} />
                </Routes>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(screen.getByTestId('profile-form')).toBeInTheDocument();
        });
    });

    test('A-24: CV se stahuje přes /files/ API s tokenem (blob), ne přímým odkazem', async () => {
        mockGetCurrentUserProfile.mockResolvedValue({
            ...mockStudent,
            cv_file: 'http://localhost:8000/storage/storage/documents/cvs/a.pdf',
        });
        mockApiGet.mockResolvedValue({ data: new Blob(['x']) });
        global.URL.createObjectURL = jest.fn(() => 'blob:cv');
        global.URL.revokeObjectURL = jest.fn();
        const openSpy = jest.spyOn(window, 'open').mockImplementation(() => null);

        render(
            <MemoryRouter initialEntries={['/profil']}>
                <Routes>
                    <Route path="/profil" element={<ProfilPage />} />
                </Routes>
            </MemoryRouter>
        );

        const link = await screen.findByText('profile.download_cv');
        fireEvent.click(link);

        await waitFor(() => expect(mockApiGet).toHaveBeenCalledWith('/files/storage/documents/cvs/a.pdf/', { responseType: 'blob' }));
        await waitFor(() => expect(openSpy).toHaveBeenCalledWith('blob:cv', '_blank', 'noopener'));
        openSpy.mockRestore();
    });
});
