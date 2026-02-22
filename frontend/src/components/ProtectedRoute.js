import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@services/auth/Auth';

/**
 * Wraps a route so it is only accessible to authenticated users.
 * Unauthenticated visitors are redirected to the login page ("/").
 */
export default function ProtectedRoute({ children }) {
    const { accessToken, isInitializing } = useAuth();

    if (isInitializing) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-100">
                <div className="text-xl text-gray-600">Načítání aplikace...</div>
            </div>
        );
    }

    if (!accessToken) {
        return <Navigate to="/" replace />;
    }

    return children;
}
