import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '@services/auth/Auth';
import { useUser } from '@hooks/UserProvider';
import { useTranslation } from 'react-i18next';

/**
 * Wraps a route so it is only accessible to authenticated users.
 * Optional 'allowedRoles' prop can restrict access to specific roles.
 * Unauthenticated visitors are redirected to the login page ("/").
 */
export default function ProtectedRoute({ children, allowedRoles }) {
    const { accessToken, isInitializing } = useAuth();
    const { user } = useUser();
    const { t } = useTranslation();

    if (isInitializing) {
        return (
            <div className="min-h-screen flex items-center justify-center bg-gray-100">
                <div className="text-xl text-gray-600">{t('common.loading_app')}</div>
            </div>
        );
    }

    if (!accessToken || !user || !user.isAuthenticated) {
        return <Navigate to="/" replace />;
    }

    if (allowedRoles && !allowedRoles.includes(user.role)) {
        console.warn(`Access denied for role "${user.role}" to a protected route. Allowed roles: ${allowedRoles.join(', ')}`);
        return <Navigate to="/nabidka" replace />;
    }

    return children;
}
