import React, { createContext, useContext, useEffect, useState } from "react";
import { createApiClient } from "@api/apiClient";
import axios from 'axios';
import { useUser } from "@hooks/UserProvider"; // předpokládám, že máte useUser hook
import { useNavigate } from "react-router-dom";
import { useMessage } from "@hooks/MessageContext";

const AuthContext = createContext(null);

function AuthProvider({ children }) {
    const [accessToken, setAccessToken] = useState(localStorage.getItem("accessToken") || null);
    const [refreshToken, setRefreshToken] = useState(localStorage.getItem("refreshToken") || null);
    const [apiClient] = useState(() => createApiClient()); // Inicializace při vytvoření
    const [isInitializing, setIsInitializing] = useState(true); // Loading state
    const { user, setUser, cleanUser } = useUser(); // použití useUser hooku
    const navigate = useNavigate();
    const { addMessage } = useMessage();
    
    console.log("STORAGE:", localStorage?.getItem("refreshToken"));

    // Funkce pro aktualizaci session - refresh tokenu
    const refreshUX = async () => {
        console.log("refreshUX called, apiClient:", !!apiClient, "refreshToken:", !!refreshToken);
        if (!apiClient || !refreshToken) {
            console.log("refreshUX: missing apiClient or refreshToken");
            return;
        }
        
        try {
            console.log("Calling refresh endpoint with token:", refreshToken);
            const res = await apiClient.post('/users/token/refresh/', {'refresh': refreshToken}, { withCredentials: true });
            console.log("Refresh response:", res?.data);
            
            if (res?.data?.access) {
                console.log("Setting new access token:", res.data.access);
                setAccessToken(res.data.access);
                
                // Pokud je v response i refresh token, aktualizujeme ho
                if (res.data.refresh) {
                    setRefreshToken(res.data.refresh);
                }
                
                // USER DATA
                if (res.data.user) {
                    setUser(res.data.user);
                    localStorage.setItem("user", JSON.stringify(res.data.user));
                }
                addMessage(`Uživatel ${user.email ? user.email : ""} byl úspěšně přihlášen`)
                return true;
            }
        } catch (error) {
            console.error('Refresh token failed:', error);
            return false;
        }
    }

    // Mám refresh token v localStorage, tak ho rovnou lognu
    useEffect(() => {
        const storedRefreshToken = localStorage.getItem("refreshToken");
        const currentPath = window.location.pathname;
        console.log("useEffect check - stored token:", !!storedRefreshToken, "current path:", currentPath);
        
        if (storedRefreshToken) {
            console.log("Mám refresh token v localStorage, volám refreshUX");
            
            refreshUX().then((success) => {
                if (success) {
                    console.log("Refresh successful");
                    // Přesměrujeme pouze pokud nejsme už na /nabidka
                    if (currentPath !== '/nabidka') {
                        console.log("Redirecting to /nabidka");
                        setTimeout(() => {
                            navigate('/nabidka');
                        }, 1000);
                    } else {
                        console.log("Already on /nabidka, no redirect needed");
                    }
                } else {
                    console.log("Refresh failed, staying on current page");
                }
            });
        }
    }, [])

    // Aktualizace session pro lepší UX - intervalově
    useEffect(() => {
        // Spustíme interval pouze pokud máme refresh token
        if (refreshToken) {
            console.log("Nastavuji interval pro refresh token..");
            let intervalId = setInterval(refreshUX, 1000 * 60 * 4.5); // 4.5 minuty
            return () => {
                console.log("Clearing refresh interval");
                clearInterval(intervalId);
            };
        }
    }, [refreshToken]); // Spustí se při změně refreshToken, ale interval se nastaví pouze jednou    

    // Debug logging
    useEffect(() => {
        console.log("RefreshT:", refreshToken);
        if (accessToken) {
            console.log("Access Token", accessToken);
        }
    }, [refreshToken]);

    // Aktualizace API klienta při změně ACCESS tokenu
    useEffect(() => {
        if (!apiClient) return;

        // Request interceptor
        const requestInterceptor = apiClient.interceptors.request.use(
            (config) => {
                if (accessToken) {
                    config.headers['Authorization'] = `Bearer ${accessToken ? accessToken : "NENÍ"}`;
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
                        const res = await apiClient.post('/users/token/refresh/', {'refresh': refreshToken}, { withCredentials: true });
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
                        //window.location.href = '/';
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

    const login = async (loginData) => {
        if (!apiClient) throw new Error('API není inicializován!');
        
        try {
            const response = await apiClient.post('/users/login/', loginData, {
                headers: {
                    'Content-Type': 'application/json'
                },
                withCredentials: true
            });
            
            //console.log('Login response:', response.data);  // Debug log
            
            if (response.data) {
                console.log("RESPONSE", response.data)
                console.log("Nastavuji access token:", response.data.access);
                setAccessToken(response.data.access);
                setRefreshToken(response.data.refresh);
                
                // Access token se ukládá pouze do state, ne do localStorage
                
                // USER DATA
                if (response.data.user) {
                    setUser(response.data.user);
                    sessionStorage.setItem("pendingMessage", JSON.stringify({
                        text: `Uživatel ${user?.email ? user.email : ""} byl úspěšně přihlášen`,
                        type: "S"
                    }));
                }
                
                if (response.data.refresh) {
                    localStorage.setItem("refreshToken", response.data.refresh);
                }
                
                // Store user data in localStorage
                if (response.data.user) {
                    localStorage.setItem("user", JSON.stringify(response.data.user));
                }
        
                
                // Počkáme chvilku než se state aktualizuje a pak redirect
                setTimeout(() => {
                    console.log("Redirect na /nabidka");
                    navigate('/nabidka');
                }, 100);
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
            await apiClient.post('/users/logout/', {'refresh': refreshToken});
            setAccessToken(null);
            setRefreshToken(null);
            localStorage.removeItem("refreshToken");

            cleanUser();
            navigate('/');
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
