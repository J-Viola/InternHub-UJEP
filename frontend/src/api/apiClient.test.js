import axios from 'axios';
import { createApiClient, setAccessToken } from './apiClient';

jest.mock('axios');

describe('apiClient', () => {
    beforeEach(() => {
        jest.clearAllMocks();
        // Reset module-level token
        setAccessToken(null);
    });

    describe('Authorization header (C6.6)', () => {
        test('does not set Authorization header when token is null', async () => {
            // Arrange
            const mockAxiosInstance = {
                interceptors: {
                    request: { use: jest.fn() },
                    response: { use: jest.fn() },
                },
            };
            axios.create.mockReturnValue(mockAxiosInstance);

            // Register request interceptor manually
            mockAxiosInstance.interceptors.request.use.mockImplementation((onFulfilled) => {
                mockAxiosInstance._requestHandler = onFulfilled;
            });

            createApiClient(() => {});

            const config = { headers: {} };
            mockAxiosInstance._requestHandler(config);

            expect(config.headers.Authorization).toBeUndefined();
        });

        test('sets Authorization header when token is set', async () => {
            // Arrange
            setAccessToken('test-token-123');

            const mockAxiosInstance = {
                interceptors: {
                    request: { use: jest.fn() },
                    response: { use: jest.fn() },
                },
            };
            axios.create.mockReturnValue(mockAxiosInstance);

            mockAxiosInstance.interceptors.request.use.mockImplementation((onFulfilled) => {
                mockAxiosInstance._requestHandler = onFulfilled;
            });

            createApiClient(() => {});

            const config = { headers: {} };
            mockAxiosInstance._requestHandler(config);

            expect(config.headers.Authorization).toBe('Bearer test-token-123');
        });

        test('does not send "Bearer null" when token is null', async () => {
            // Arrange
            setAccessToken(null);

            const mockAxiosInstance = {
                interceptors: {
                    request: { use: jest.fn() },
                    response: { use: jest.fn() },
                },
            };
            axios.create.mockReturnValue(mockAxiosInstance);

            mockAxiosInstance.interceptors.request.use.mockImplementation((onFulfilled) => {
                mockAxiosInstance._requestHandler = onFulfilled;
            });

            createApiClient(() => {});

            const config = { headers: {} };
            mockAxiosInstance._requestHandler(config);

            // The header should NOT be set at all (not "Bearer null")
            expect(config.headers.Authorization).toBeUndefined();
            expect(config.headers.Authorization).not.toBe('Bearer null');
        });
    });

    describe('Timeout (C6.H1)', () => {
        test('creates axios instance with timeout', () => {
            axios.create.mockReturnValue({
                interceptors: {
                    request: { use: jest.fn() },
                    response: { use: jest.fn() },
                },
            });

            createApiClient(() => {});

            expect(axios.create).toHaveBeenCalledWith(
                expect.objectContaining({
                    timeout: 30000,
                })
            );
        });
    });

    describe('Error normalization preserves response (C6.2)', () => {
        test('standardError includes error.response property', async () => {
            const mockAxiosInstance = {
                interceptors: {
                    request: { use: jest.fn() },
                    response: { use: jest.fn() },
                },
            };
            axios.create.mockReturnValue(mockAxiosInstance);

            const errorHandlers = {};
            mockAxiosInstance.interceptors.response.use.mockImplementation((onFulfilled, onRejected) => {
                errorHandlers.fulfilled = onFulfilled;
                errorHandlers.rejected = onRejected;
            });

            // Build real rejection handler
            createApiClient(() => {});

            const axiosError = {
                message: 'Request failed with status code 404',
                response: {
                    status: 404,
                    data: { detail: 'Not found' },
                },
                config: { url: '/api/test' },
            };

            await expect(errorHandlers.rejected(axiosError)).rejects.toMatchObject({
                response: axiosError.response,
                code: 'DRF_ERROR',
                details: 'Not found',
                status: 404,
            });
        });

        test('networkError includes error.response property', async () => {
            const mockAxiosInstance = {
                interceptors: {
                    request: { use: jest.fn() },
                    response: { use: jest.fn() },
                },
            };
            axios.create.mockReturnValue(mockAxiosInstance);

            const errorHandlers = {};
            mockAxiosInstance.interceptors.response.use.mockImplementation((onFulfilled, onRejected) => {
                errorHandlers.fulfilled = onFulfilled;
                errorHandlers.rejected = onRejected;
            });

            createApiClient(() => {});

            const axiosError = {
                message: 'Network Error',
                response: undefined, // no response = network error
                config: { url: '/api/test' },
            };

            const normalizedError = await errorHandlers.rejected(axiosError).catch((e) => e);
            expect(normalizedError.response).toBeUndefined();
            expect(normalizedError.code).toBeDefined();
            expect(normalizedError.status).toBe(0);
        });
    });
});
