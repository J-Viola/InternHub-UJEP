import axios from 'axios';
import i18n from '../i18n';

const API_ROOT = '/api';
const DEFAULT_URL = 'http://localhost:8000';

// Use REACT_APP_API_URL in production, fallback to localhost for dev
const getBaseUrl = () => {
    let url = process.env.REACT_APP_API_URL || DEFAULT_URL;
    // Remove trailing slash if present
    if (url.endsWith('/')) {
        url = url.slice(0, -1);
    }
    return `${url}${API_ROOT}`;
};

const BASE_URL = getBaseUrl();

const maskSensitiveData = (data) => {
    if (!data || typeof data !== 'object') return data;
    const masked = { ...data };
    const sensitiveKeys = ['password', 'password1', 'password2', 'token', 'access', 'refresh', 'service_ticket'];

    Object.keys(masked).forEach(key => {
        if (sensitiveKeys.some(sk => key.toLowerCase().includes(sk))) {
            masked[key] = '********';
        } else if (typeof masked[key] === 'object') {
            masked[key] = maskSensitiveData(masked[key]);
        }
    });
    return masked;
};

let _accessToken = null;

export const getAccessToken = () => _accessToken;
export const setAccessToken = (token) => { _accessToken = token; };

export const createApiClient = (navigate) => {
    const apiClient = axios.create({
        baseURL: BASE_URL,
        headers: {
            'Content-Type': 'application/json',
        },
        withCredentials: true,
    });

    // Request interceptor
    apiClient.interceptors.request.use(
        (config) => {
            config.headers.Authorization = `Bearer ${_accessToken}`;

            // Sync language with backend
            const lang = i18n.language || 'cs';
            config.headers['Accept-Language'] = lang;

            const isDev = process.env.NODE_ENV === 'development';
            if (isDev) {
                const maskedData = maskSensitiveData(config.data);
                console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`, maskedData);
            }
            return config;
        },
        (error) => Promise.reject(error)
    );


    // Response interceptor — redirect on persistent 401
    apiClient.interceptors.response.use(
        response => {
            const isDev = process.env.NODE_ENV === 'development';
            if (isDev) {
                console.log(`API Response: ${response.status} ${response.config.url}`, response.data);
            }
            return response;
        },
        error => {
            const isDev = process.env.NODE_ENV === 'development';

            if (!error.response) {
                if (isDev) {
                    console.error('API Network Error:', error.message);
                }
                let networkError = new Error(error.message);
                networkError.code = navigator.onLine ? "SERVER_UNREACHABLE" : "NETWORK_ERROR";
                networkError.details = null;
                networkError.status = 0;
                return Promise.reject(networkError);
            }

            if (isDev) {
                console.error(`API Error: ${error.response?.status} ${error.config?.url}`, error.response?.data);
            }

            let standardError = new Error(error.message);
            standardError.code = "UNKNOWN_ERROR";
            standardError.details = null;
            standardError.status = error.response?.status;

            if (error.response && error.response.data) {
                const data = error.response.data;
                if (data.error_code) {
                    standardError.code = data.error_code;
                    standardError.details = data.details;
                } else if (data.detail) {
                    standardError.code = "DRF_ERROR";
                    standardError.details = data.detail;
                }
            }

            return Promise.reject(standardError);
        }
    );

    return apiClient;
};
