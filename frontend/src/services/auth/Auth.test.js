import React from 'react';
import { render, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import AuthProvider from './Auth';

const mockCleanUser = jest.fn();
// Mocks
jest.mock('@api/apiClient', () => {
    const accessToken = { current: null };
    return {
        __esModule: true,
        default: jest.fn(),
        createApiClient: jest.fn(),
        setAccessToken: jest.fn(),
        getAccessToken: jest.fn(() => accessToken.current),
    };
});

jest.mock('@hooks/UserProvider', () => ({
    __esModule: true,
    default: ({ children }) => children,
    useUser: () => ({
        user: { isLoggedIn: () => false },
        setUser: jest.fn(),
        cleanUser: mockCleanUser,
    }),
}));

jest.mock('react-router-dom', () => {
    const original = jest.requireActual('react-router-dom');
    return {
        ...original,
        useNavigate: () => jest.fn(),
    };
});

jest.mock('@hooks/MessageContext', () => ({
    MessageProvider: ({ children }) => children,
    useMessage: () => ({ addMessage: jest.fn() }),
}));

const { createApiClient, setAccessToken } = require('@api/apiClient');

describe('AuthProvider - concurrent 401 race', () => {
    let mockApiClient;
    let responseInterceptors;

    beforeEach(() => {
        jest.clearAllMocks();
        responseInterceptors = { fulfilled: null, rejected: null };

        mockApiClient = Object.assign(jest.fn((config) => Promise.resolve({ data: {}, config })), {
            interceptors: {
                request: { use: jest.fn(), eject: jest.fn() },
                response: {
                    use: jest.fn((onFulfilled, onRejected) => {
                        responseInterceptors.fulfilled = onFulfilled;
                        responseInterceptors.rejected = onRejected;
                        return 42; // interceptor id
                    }),
                    eject: jest.fn(),
                },
            },
            post: jest.fn(),
            get: jest.fn(),
        });
        mockCleanUser.mockClear();

        createApiClient.mockReturnValue(mockApiClient);
    });

    test('prevents concurrent token refresh using ref (not state)', async () => {
        // Render AuthProvider to register interceptors
        render(
            <MemoryRouter>
                <AuthProvider>
                    <div>Children</div>
                </AuthProvider>
            </MemoryRouter>
        );

        // Wait for interceptors to be registered
        await waitFor(() => {
            expect(responseInterceptors.rejected).not.toBeNull();
        });

        // Clear the mount-time refreshUX call count
        mockApiClient.post.mockClear();
        // Mock the token refresh to succeed after a delay
        mockApiClient.post.mockImplementation(() => {
            return new Promise((resolve) => {
                setTimeout(() => {
                    resolve({
                        data: { access: 'new-token-xyz', user: null },
                    });
                }, 10);
            });
        });

        const err1 = {
            response: { status: 401 },
            config: { headers: {}, url: '/api/resource1' },
        };
        const err2 = {
            response: { status: 401 },
            config: { headers: {}, url: '/api/resource2' },
        };

        // Fire two 401 errors concurrently
        const result1Promise = responseInterceptors.rejected(err1);
        const result2Promise = responseInterceptors.rejected(err2);

        // Await both
        // The second one should NOT trigger another refresh call
        // (because ref is already true)
        await Promise.all([result1Promise, result2Promise]);

        // Token refresh endpoint should be called EXACTLY ONCE
        // (not twice, which would happen with stale state closure)
        expect(mockApiClient.post).toHaveBeenCalledTimes(1);
        expect(mockApiClient).toHaveBeenCalledTimes(2);
        expect(mockApiClient.mock.calls.map(([config]) => config.headers.Authorization)).toEqual([
            'Bearer new-token-xyz', 'Bearer new-token-xyz',
        ]);

        // The Authorization header on the retry should have the new token
        // At least on the first request's retry
        expect(setAccessToken).toHaveBeenCalledWith('new-token-xyz');
    });

    test('handles refresh failure without deadlock', async () => {
        render(
            <MemoryRouter>
                <AuthProvider>
                    <div>Children</div>
                </AuthProvider>
            </MemoryRouter>
        );

        await waitFor(() => {
            expect(responseInterceptors.rejected).not.toBeNull();
        });

        // Clear the mount-time refreshUX call count
        mockApiClient.post.mockClear();
        // Mock refresh failure
        mockApiClient.post.mockRejectedValue(new Error('Refresh failed'));

        const err = {
            response: { status: 401 },
            config: { headers: {}, url: '/api/resource1' },
        };
        const err2 = {
            response: { status: 401 },
            config: { headers: {}, url: '/api/resource2' },
        };
        const results = await Promise.allSettled([
            responseInterceptors.rejected(err),
            responseInterceptors.rejected(err2),
        ]);
        expect(results.every(result => result.status === 'rejected')).toBe(true);
        expect(mockApiClient.post).toHaveBeenCalledTimes(1);
        expect(mockCleanUser).toHaveBeenCalledTimes(1);
    });

    test('does not refresh a 401 from refresh endpoint', async () => {
        render(<MemoryRouter><AuthProvider><div>Children</div></AuthProvider></MemoryRouter>);
        await waitFor(() => expect(responseInterceptors.rejected).not.toBeNull());
        mockApiClient.post.mockClear();
        const error = { response: { status: 401 }, config: { headers: {}, url: '/users/token/refresh/' } };
        await expect(responseInterceptors.rejected(error)).rejects.toBe(error);
        expect(mockApiClient.post).not.toHaveBeenCalled();
    });

    test('počáteční refresh pod StrictMode proběhne právě jednou (F-8)', async () => {
        // StrictMode spouští efekt dvakrát; rotující refresh cookie by druhému
        // souběžnému požadavku vrátilo 401, proto se musí sdílet jeden požadavek.
        mockApiClient.post.mockResolvedValue({ data: { access: 'tok', user: null } });

        render(
            <React.StrictMode>
                <MemoryRouter>
                    <AuthProvider>
                        <div>Children</div>
                    </AuthProvider>
                </MemoryRouter>
            </React.StrictMode>
        );

        await waitFor(() => expect(setAccessToken).toHaveBeenCalledWith('tok'));
        const refreshCalls = mockApiClient.post.mock.calls.filter(([url]) => url === '/users/token/refresh/');
        expect(refreshCalls).toHaveLength(1);
    });
});
