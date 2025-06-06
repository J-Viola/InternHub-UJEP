import React, { createContext, useContext, useEffect, useState } from "react";
import { _post } from "@api/apiClient";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [accessToken, setAccessToken] = useState(null);
    const [refreshToken, setRefreshToken] = useState(null);

    //FOR DEBUG :D
    useEffect(() => {
        console.log("AccessT:", accessToken);
        console.log("RefreshT:", RefreshToken);
    }, [accessToken, refreshToken])


    const login = async (credentials) => {
        try {
            const response = await _post('api/login', credentials, {
                headers: {
                    'Content-Type': 'application/json'
                },
                withCredentials: true
            });
            return response;
        } catch (error) {
            throw error;
        }
    };

    //SET TOKENY
    setAccessToken(login.accessToken);
    setRefreshToken(login.refreshToken);

    const logout = async () => {
        try {
            await _post('api/logout');
            setAccessToken(null);
        } catch (error) {
            throw error;
        }
    };

    return (
        <AuthContext.Provider value={{ accessToken, refreshToken, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);