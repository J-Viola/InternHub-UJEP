import { renderHook } from '@testing-library/react';
import { useCodeListAPI } from './code_listAPI';

const mockGet = jest.fn();
jest.mock('@hooks/useApi', () => ({ useApi: () => ({ get: (...args) => mockGet(...args) }) }));

describe('useCodeListAPI', () => {
    beforeEach(() => mockGet.mockReset());

    test('propagates API errors instead of masking them as an empty list', async () => {
        const error = new Error('request failed');
        mockGet.mockRejectedValue(error);
        const { result } = renderHook(() => useCodeListAPI());
        await expect(result.current.getSubjects()).rejects.toBe(error);
        await expect(result.current.getUniqueSubjects()).rejects.toBe(error);
    });
});
