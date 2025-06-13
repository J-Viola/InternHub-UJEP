//https://medium.com/@gahrmicc/basic-implementation-of-interceptors-in-react-js-using-axios-222bf0db6c3f
import React, { createContext, useContext, useEffect, useState } from "react";
import { createApiClient } from "@api/apiClient";
import axios from 'axios';
import { useUser } from "@hooks/UserProvider"; // předpokládám, že máte useUser hook

const AuthContext = createContext(null);

function AuthProvider({ children }) {
    const [accessToken, setAccessToken] = useState(null);
    const [refreshToken, setRefreshToken] = useState(localStorage.getItem("refreshToken") || null);
    const [apiClient] = useState(() => createApiClient()); // Inicializace při vytvoření
    const { user, setUser, cleanUser } = useUser(); // použití useUser hooku místo UserProvider komponenty

    // Funkce pro aktualizaci session - refresh tokenu
    const refreshUX = async () => {
        if (!apiClient || !refreshToken) return;
        
        try {
            const res = await apiClient.post('/refresh', {'refresh': refreshToken}, { withCredentials: true });
            if (res?.data?.access && res?.data?.refresh) {
                setAccessToken(res.data.access);
                setRefreshToken(res.data.refresh);
                if (res.data.user) {
                    setUser(res.data.user);
                }
            }
        } catch (error) {
            console.error('Refresh token failed:', error);
        }
    }

    // Aktualizace session pro lepší UX - intervalově
    useEffect(() => {
        if (refreshToken) {
            let intervalId = setInterval(refreshUX, 1000 * 60 * 4.5); // 4.5 min - předělat na env proměnnou
            return () => clearInterval(intervalId); // odstraním interval při změně refresh tokenu - cleanup funkce
        }
    }, [refreshToken]);

    // Debug logging
    useEffect(() => {
        console.log("AccessT:", accessToken);
        console.log("RefreshT:", refreshToken);
    }, [accessToken, refreshToken]);

    // Aktualizace API klienta při změně ACCESS tokenu
    useEffect(() => {
        if (!apiClient) return;

        // Request interceptor
        const requestInterceptor = apiClient.interceptors.request.use(
            (config) => {
                if (accessToken) {
                    config.headers['Authorization'] = `Bearer ${accessToken}`;
                }
                return config;
            },
            (error) => {
                return Promise.reject(error);
            }
        );

        // Response interceptor
        const responseInterceptor = apiClient.interceptors.response.use(
            (response) => response,
            async (error) => {
                if (error.response?.status === 401) {
                    try {
                        const res = await apiClient.post('/refresh', {'refresh': refreshToken}, { withCredentials: true });
                        if (res?.data?.access) {
                            setAccessToken(res.data.access);
                            error.config.headers.Authorization = `Bearer ${res.data.access}`;
                            return apiClient(error.config);
                        }
                    } catch (refreshError) {
                        setAccessToken(null);
                        setRefreshToken(null);
                        localStorage.removeItem("refreshToken");
                        cleanUser();
                        window.location.href = '/login';
                    }
                }
                throw error;
            }
        );

        return () => {
            apiClient.interceptors.request.eject(requestInterceptor);
            apiClient.interceptors.response.eject(responseInterceptor);
        };
    }, [accessToken, apiClient]);

    const login = async (stagData) => {
        if (!apiClient) throw new Error('API není inicializován!');
        
        try {
            const response = await apiClient.post('/users/login/', stagData, {
                headers: {
                    'Content-Type': 'application/json'
                },
                withCredentials: true
            });
            
            console.log('Login response:', response.data);  // Debug log
            
            if (response?.data?.access) {
                setAccessToken(response.data.access);
                setRefreshToken(response.data.refresh);
                if (response.data.user) {
                    setUser(response.data.user);
                }
                
                if (response.data.refresh) {
                    localStorage.setItem("refreshToken", response.data.refresh);
                }
            }
            
            return response;
        } catch (error) {
            console.error('Login error:', error);  // Debug log
            throw error;
        }
    };

    const logout = async () => {
        if (!apiClient) throw new Error('API není inicializován!');
        
        try {
            await apiClient.post('logout');
            setAccessToken(null);
            setRefreshToken(null);
            localStorage.removeItem("refreshToken");
            cleanUser();
        } catch (error) {
            throw error;
        }
    };

    return (
        <AuthContext.Provider value={{ 
            accessToken, 
            refreshToken, 
            login, 
            logout,
            apiClient 
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
