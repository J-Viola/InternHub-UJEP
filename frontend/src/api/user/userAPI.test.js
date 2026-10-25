import { renderHook } from '@testing-library/react';
import { useUserAPI } from './userAPI';

jest.mock('@hooks/useApi', () => ({ useApi: () => ({ get: jest.fn() }) }));

describe('useUserAPI stability', () => {
    test('returns a stable API object and getAllStudents callback', () => {
        const { result, rerender } = renderHook(() => useUserAPI());
        const firstApi = result.current;
        const firstGetAllStudents = result.current.getAllStudents;
        rerender();
        expect(result.current).toBe(firstApi);
        expect(result.current.getAllStudents).toBe(firstGetAllStudents);
    });
});
