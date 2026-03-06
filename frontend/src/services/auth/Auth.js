import React, { createContext, useContext, useEffect, useState } from "react";
import { createApiClient } from "@api/apiClient";
import { useUser } from "@hooks/UserProvider";
import { useNavigate } from "react-router-dom";

const AuthContext = createContext(null);

// Routes that should stay on the current page after a successful token refresh
const PUBLIC_PATHS = ['/', '/login', '/registrace', '/reset-password'];

function AuthProvider({ children }) {
    const [accessToken, setAccessToken] = useState(localStorage.getItem("accessToken") || null);
    const [refreshToken, setRefreshToken] = useState(localStorage.getItem("refreshToken") || null);
    const [isInitializing, setIsInitializing] = useState(true);
    const { setUser, cleanUser } = useUser();
    const navigate = useNavigate();
    const [apiClient] = useState(() => createApiClient(navigate));

    // Refresh the access token using the stored refresh token
    const refreshUX = async () => {
        const currentRefreshToken = localStorage.getItem("refreshToken");
        if (!apiClient || !currentRefreshToken) {
            return false;
        }

        try {
            const res = await apiClient.post('/users/token/refresh/', { 'refresh': currentRefreshToken }, { withCredentials: true });

            if (res?.data?.access) {
                setAccessToken(res.data.access);
                localStorage.setItem("accessToken", res.data.access);

                if (res.data.refresh) {
                    setRefreshToken(res.data.refresh);
                    localStorage.setItem("refreshToken", res.data.refresh);
                }

                if (res.data.user) {
                    setUser(res.data.user);
                    localStorage.setItem("user", JSON.stringify(res.data.user));
                }
                return true;
            }
        } catch (error) {
            handleAuthFailure();
            return false;
        }
        return false;
    };

    const handleAuthFailure = () => {
        setAccessToken(null);
        setRefreshToken(null);
        localStorage.removeItem("accessToken");
        localStorage.removeItem("refreshToken");
        localStorage.removeItem("user");
        cleanUser();
    };

    // On mount: attempt to restore session from stored refresh token
    useEffect(() => {
        const storedRefreshToken = localStorage.getItem("refreshToken");
        const currentPath = window.location.pathname;

        if (storedRefreshToken) {
            refreshUX().then((success) => {
                if (success && PUBLIC_PATHS.some(p => currentPath === p || currentPath.startsWith('/reset-password'))) {
                    // Only redirect to /nabidka when the user is currently on a public/login page
                    navigate('/nabidka');
                }
            }).finally(() => {
                setIsInitializing(false);
            });
        } else {
            setIsInitializing(false);
        }
    }, []);

    // Periodic token refresh every 4.5 minutes
    useEffect(() => {
        if (refreshToken) {
            const intervalId = setInterval(refreshUX, 1000 * 60 * 4.5);
            return () => clearInterval(intervalId);
        }
    }, [refreshToken]);

    // Handle 401 auto-refresh
    useEffect(() => {
        if (!apiClient) return;

        const responseInterceptor = apiClient.interceptors.response.use(
            (response) => response,
            async (error) => {
                if (error.response?.status === 401) {
                    const currentRefreshToken = localStorage.getItem("refreshToken");
                    if (currentRefreshToken) {
                        try {
                            const res = await apiClient.post('/users/token/refresh/', { 'refresh': currentRefreshToken }, { withCredentials: true });
                            if (res?.data?.access) {
                                setAccessToken(res.data.access);
                                localStorage.setItem("accessToken", res.data.access);
                                error.config.headers.Authorization = `Bearer ${res.data.access}`;
                                return apiClient(error.config);
                            }
                        } catch {
                            handleAuthFailure();
                        }
                    } else {
                        handleAuthFailure();
                    }
                }
                throw error;
            }
        );

        return () => {
            apiClient.interceptors.response.eject(responseInterceptor);
        };
    }, [apiClient]);

    const login = async (loginData) => {
        if (!apiClient) throw new Error('API není inicializován!');

        const response = await apiClient.post('/users/login/', loginData, {
            headers: { 'Content-Type': 'application/json' },
            withCredentials: true
        });

        if (response.data) {
            setAccessToken(response.data.access);
            localStorage.setItem("accessToken", response.data.access);
            setRefreshToken(response.data.refresh);

            if (response.data.user) {
                setUser(response.data.user);
                sessionStorage.setItem("pendingMessage", JSON.stringify({
                    text: `Uživatel ${response.data.user?.email ?? ""} byl úspěšně přihlášen`,
                    type: "S"
                }));
                localStorage.setItem("user", JSON.stringify(response.data.user));
            }

            if (response.data.refresh) {
                localStorage.setItem("refreshToken", response.data.refresh);
            }

            setTimeout(() => navigate('/nabidka'), 100);
        }

        return response;
    };

    const logout = async () => {
        if (!apiClient) throw new Error('API není inicializován!');

        try {
            await apiClient.post('/users/logout/', { 'refresh': refreshToken });
        } finally {
            setAccessToken(null);
            setRefreshToken(null);
            localStorage.removeItem("accessToken");
            localStorage.removeItem("refreshToken");
            localStorage.removeItem("user");
            cleanUser();
            navigate('/');
        }
    };

    return (
        <AuthContext.Provider value={{
            accessToken,
            refreshToken,
            login,
            logout,
            apiClient,
            isInitializing,
        }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth() {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth volej, pokud jsi pod AuthProvider!');
    }
    return context;
}

export default AuthProvider;
