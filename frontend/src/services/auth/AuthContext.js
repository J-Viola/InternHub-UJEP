//https://medium.com/@gahrmicc/basic-implementation-of-interceptors-in-react-js-using-axios-222bf0db6c3f
import React, { createContext, useContext, useEffect, useState } from "react";
import { createApiClient } from "@api/apiClient";
import axios from 'axios';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [accessToken, setAccessToken] = useState(null);
    const [refreshToken, setRefreshToken] = useState(localStorage.getItem("refreshToken") ||null);
    const [apiClient, setApiClient] = useState(createApiClient()); // init simple api client

    // Funkce pro aktualizaci session - refresh tokenu
    const refreshUX = async () => {
        const client = apiClient;
        if (refreshToken) {
            const res = await client.post('/api/refresh', {'refresh': refreshToken}, { withCredentials: true });
            if (res?.data?.accessToken && res?.data?.refreshToken) {
                setAccessToken(res.data.accessToken);
                setRefreshToken(res.data.refreshToken);
            }
        }
    }

    // Aktualizace session pro lepší UX - intervalově
    useEffect(() => {
        let intervalId = setInterval(refreshUX, 1000 * 60 * 4.5); // 4.5 min - předělat na env proměnnou
        return () => clearInterval(intervalId); // odstraním interval při změně refresh tokenu - cleanup funkce
    }, [refreshToken]);

    // Debug logging
    useEffect(() => {
        console.log("AccessT:", accessToken);
        console.log("RefreshT:", refreshToken);
    }, [accessToken, refreshToken]);

    // Aktualizace API klienta při změně ACCESS tokenu
    useEffect(() => {
        const client = apiClient;
        
        // Request interceptor - přidám access token do hlavičky před odesláním requestu
        const requestInterceptor = client.interceptors.request.use(async (config) => {
            if (accessToken) {
                config.headers['Authorization'] = `Bearer ${accessToken}`;
            }
            return config;
        });

        // Response interceptor - zpracování chyby 401 v response
        const responseInterceptor = client.interceptors.response.use(
            (res) => res,
            async (err) => {
                if (err.response?.status === 401) {
                    try {
                        // poslu starý REFRESH token na refresh
                        const res = await client.post('/api/refresh', {'refresh': refreshToken}, { withCredentials: true });
                        if (res?.data?.accessToken) {
                            setAccessToken(res.data.accessToken);
                            // přepíšu config
                            err.config.headers.Authorization = `Bearer ${res.data.accessToken}`;
                            return client(err.config);
                        }
                    // pokud neprojde refresh, tak smažu všechny tokeny a nechám uživatele 
                    // znovu přihlásit a získat oba tokeny
                    } catch (refreshErr) {
                        setAccessToken(null);
                        setRefreshToken(null);
                        // smažu refresh token - musí si ho znovu založit
                        localStorage.removeItem("refreshToken");
                        window.location.href = '/login';
                    }
                }
                throw err;
            }
        );

        setApiClient(client);

        return () => {
            client.interceptors.request.eject(requestInterceptor); // odstraním interceptor
            client.interceptors.response.eject(responseInterceptor); // odstraním interceptor
        };
    }, [accessToken]);


    const login = async (stagData) => {
        try {
            const response = await apiClient.post('api/login', stagData, {
                headers: {
                    'Content-Type': 'application/json'
                },
                withCredentials: true
            });
            
            if (response?.data?.accessToken) {
                setAccessToken(response.data.accessToken);
                setRefreshToken(response.data.refreshToken);
                
                if (response.data.refreshToken) {
                    localStorage.setItem("refreshToken", response.data.refreshToken);
                }
            }
            
            return response;
        } catch (error) {
            throw error;
        }
    };

    const logout = async () => {
        try {
            await apiClient.post('api/logout');
            setAccessToken(null);
            //setRefreshToken(null);
            //localStorage.removeItem("refreshToken");
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
};

export const useAuth = () => useContext(AuthContext);