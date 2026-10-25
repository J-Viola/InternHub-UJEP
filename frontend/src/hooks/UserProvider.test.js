import React from 'react';
import { render, act, screen } from '@testing-library/react';
import UserProvider, { useUser } from './UserProvider';

function Probe() {
    const { setUser } = useUser();
    return <button onClick={() => setUser({ email: 'private@example.test', access: 'secret-token' })}>set</button>;
}

describe('UserProvider logging', () => {
    const originalEnv = process.env.NODE_ENV;
    let log;
    beforeEach(() => {
        localStorage.clear();
        log = jest.spyOn(console, 'log').mockImplementation(() => {});
    });
    afterEach(() => {
        log.mockRestore();
        Object.defineProperty(process.env, 'NODE_ENV', { value: originalEnv, configurable: true });
    });

    test('persists user without logging user data in production', () => {
        Object.defineProperty(process.env, 'NODE_ENV', { value: 'production', configurable: true });
        render(<UserProvider><Probe /></UserProvider>);
        act(() => screen.getByText('set').click());
        expect(localStorage.getItem('user')).toContain('private@example.test');
        expect(log).not.toHaveBeenCalled();
    });

    test('development logs do not contain token or email', () => {
        Object.defineProperty(process.env, 'NODE_ENV', { value: 'development', configurable: true });
        render(<UserProvider><Probe /></UserProvider>);
        act(() => screen.getByText('set').click());
        expect(JSON.stringify(log.mock.calls)).not.toContain('private@example.test');
        expect(JSON.stringify(log.mock.calls)).not.toContain('secret-token');
    });
});
