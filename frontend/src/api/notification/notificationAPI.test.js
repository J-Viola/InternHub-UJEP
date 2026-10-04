import { renderHook } from '@testing-library/react';
import { useNotificationAPI } from './notificationAPI';

// Mock useApi hook
jest.mock('@hooks/useApi', () => ({
    useApi: jest.fn(),
}));

const { useApi } = require('@hooks/useApi');

describe('notificationAPI', () => {
    let api;

    beforeEach(() => {
        jest.clearAllMocks();
        api = {
            get: jest.fn(),
            patch: jest.fn(),
            post: jest.fn(),
        };
        useApi.mockReturnValue(api);
    });

    // useNotificationAPI is a hook — call it through renderHook so it runs
    // inside a React component (hooks cannot be invoked outside render).
    const renderNotificationAPI = () => {
        const { result } = renderHook(() => useNotificationAPI());
        return result.current;
    };

    describe('getNotifications', () => {
        test('returns response.data, not full Axios response', async () => {
            const mockData = {
                results: [{ id: 1, title: 'Test notification' }],
                count: 1,
            };
            api.get.mockResolvedValue({ data: mockData });

            const { getNotifications } = renderNotificationAPI();
            const result = await getNotifications({ limit: 5 });

            // Should return the data, not the Axios wrapper
            expect(result).toBe(mockData);
            expect(result.results).toEqual([{ id: 1, title: 'Test notification' }]);
            // Should NOT have Axios properties
            expect(result.status).toBeUndefined();
            expect(result.config).toBeUndefined();
        });

        test('passes params to api.get', async () => {
            api.get.mockResolvedValue({ data: [] });

            const { getNotifications } = renderNotificationAPI();
            await getNotifications({ page: 2, limit: 10 });

            expect(api.get).toHaveBeenCalledWith('/notifications/', {
                params: { page: 2, limit: 10 },
            });
        });
    });

    describe('getUnreadCount', () => {
        test('returns unread_count number, not undefined', async () => {
            api.get.mockResolvedValue({ data: { unread_count: 5 } });

            const { getUnreadCount } = renderNotificationAPI();
            const result = await getUnreadCount();

            // Should return the number, not undefined
            expect(result).toBe(5);
            expect(typeof result).toBe('number');
        });

        test('returns 0 when unread_count is missing', async () => {
            api.get.mockResolvedValue({ data: {} });

            const { getUnreadCount } = renderNotificationAPI();
            const result = await getUnreadCount();

            expect(result).toBe(0);
        });

        test('returns 0 when data is null', async () => {
            api.get.mockResolvedValue({ data: null });

            const { getUnreadCount } = renderNotificationAPI();
            const result = await getUnreadCount();

            expect(result).toBe(0);
        });
    });

    describe('markAsRead', () => {
        test('returns response.data, not full Axios response', async () => {
            const mockData = { id: 42, is_read: true };
            api.patch.mockResolvedValue({ data: mockData });

            const { markAsRead } = renderNotificationAPI();
            const result = await markAsRead(42);

            expect(result).toBe(mockData);
            expect(result.is_read).toBe(true);
            expect(result.status).toBeUndefined();
        });
    });

    describe('markAllAsRead', () => {
        test('returns response.data, not full Axios response', async () => {
            const mockData = { message: 'All marked as read' };
            api.post.mockResolvedValue({ data: mockData });

            const { markAllAsRead } = renderNotificationAPI();
            const result = await markAllAsRead();

            expect(result).toBe(mockData);
            expect(result.status).toBeUndefined();
        });
    });
});
