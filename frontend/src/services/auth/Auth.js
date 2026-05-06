import React, { createContext, useContext, useEffect, useState } from "react";
import { createApiClient, setAccessToken as setApiClientToken } from "@api/apiClient";
import { useUser } from "@hooks/UserProvider";
import { useNavigate } from "react-router-dom";
import { useMessage } from "@hooks/MessageContext";

const AuthContext = createContext(null);

const PUBLIC_PATHS = ['/', '/login', '/registrace', '/reset-password'];

function AuthProvider({ children }) {
    const [accessToken, setAccessToken] = useState(null);
    const [isInitializing, setIsInitializing] = useState(true);
    const [isRefreshing, setIsRefreshing] = useState(false);
    const { setUser, cleanUser } = useUser();
    const navigate = useNavigate();
    const { addMessage } = useMessage();
    const [apiClient] = useState(() => createApiClient(navigate));

    const _updateToken = (token) => {
        setAccessToken(token);
        setApiClientToken(token);
    };

    const refreshUX = async () => {
        if (!apiClient) return false;

        try {
            const res = await apiClient.post('/users/token/refresh/', {}, { withCredentials: true });

            if (res?.data?.access) {
                _updateToken(res.data.access);

                if (res.data.user) {
                    setUser(res.data.user);
                    localStorage.setItem("user", JSON.stringify(res.data.user));
                }
                return true;
            }
        } catch {
            handleAuthFailure();
            return false;
        }
        return false;
    };

    const handleAuthFailure = () => {
        const wasLoggedIn = !!accessToken;
        _updateToken(null);
        localStorage.removeItem("user");
        cleanUser();
        if (wasLoggedIn) {
            sessionStorage.setItem("pendingMessage", JSON.stringify({
                text: "Vaše relace vypršela. Přihlaste se prosím znovu.",
                type: "W"
            }));
        }
    };

    // On mount: try to restore session via cookie-based refresh
    useEffect(() => {
        const currentPath = window.location.pathname;

        refreshUX().then((success) => {
            if (success && PUBLIC_PATHS.some(p => currentPath === p || currentPath.startsWith('/reset-password'))) {
                navigate('/nabidka');
            }
        }).finally(() => {
            setIsInitializing(false);
        });
    }, []);

    // Periodic token refresh every 4.5 minutes
    useEffect(() => {
        if (accessToken) {
            const intervalId = setInterval(refreshUX, 1000 * 60 * 4.5);
            return () => clearInterval(intervalId);
        }
    }, [accessToken]);

    // Handle 401 auto-refresh
    useEffect(() => {
        if (!apiClient) return;

        const responseInterceptor = apiClient.interceptors.response.use(
            (response) => response,
            async (error) => {
                if (error.response?.status === 401 && !isRefreshing) {
                    setIsRefreshing(true);
                    try {
                        const res = await apiClient.post('/users/token/refresh/', {}, { withCredentials: true });
                        if (res?.data?.access) {
                            _updateToken(res.data.access);
                            error.config.headers.Authorization = `Bearer ${res.data.access}`;
                            return apiClient(error.config);
                        }
                    } catch {
                        handleAuthFailure();
                    } finally {
                        setIsRefreshing(false);
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
            _updateToken(response.data.access);

            if (response.data.user) {
                setUser(response.data.user);
                sessionStorage.setItem("pendingMessage", JSON.stringify({
                    text: `Uživatel ${response.data.user?.email ?? ""} byl úspěšně přihlášen`,
                    type: "S"
                }));
                localStorage.setItem("user", JSON.stringify(response.data.user));
            }

            setTimeout(() => navigate('/nabidka'), 100);
        }

        return response;
    };

    const logout = async () => {
        if (!apiClient) throw new Error('API není inicializován!');

        try {
            await apiClient.post('/users/logout/', {}, { withCredentials: true });
        } finally {
            _updateToken(null);
            localStorage.removeItem("user");
            cleanUser();
            navigate('/');
        }
    };

    return (
        <AuthContext.Provider value={{
            accessToken,
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
