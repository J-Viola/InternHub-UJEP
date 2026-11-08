import axios from 'axios';

const API_ROOT = '/api';
const DEFAULT_URL = 'http://localhost:8000';

// Use REACT_APP_API_URL in production, fallback to localhost for dev.
// When REACT_APP_API_URL is empty (unset or explicitly ''), use relative /api
// which goes through the CRA dev proxy (same-origin — no cookie issues).
const getBaseUrl = () => {
    let url = process.env.REACT_APP_API_URL;
    if (!url) {
        return API_ROOT;  // relative /api for dev proxy
    }
    if (url.endsWith('/')) {
        url = url.slice(0, -1);
    }
    return `${url}${API_ROOT}`;
};

const BASE_URL = getBaseUrl();

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
        timeout: 30000,
    });

    // Request interceptor
    apiClient.interceptors.request.use(
        (config) => {
            const token = _accessToken;
            if (token) {
                config.headers.Authorization = `Bearer ${token}`;
            }

            const isDev = process.env.NODE_ENV === 'development';
            if (isDev) {
                // Request bodies may contain personal data; log only request metadata.
                console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`);
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
                console.log(`API Response: ${response.status} ${response.config.url}`);
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
                networkError.response = error.response;
                networkError.config = error.config;
                networkError.responseData = error.response?.data ?? null;
                return Promise.reject(networkError);
            }

            if (isDev) {
                console.error(`API Error: ${error.response?.status} ${error.config?.url}`);
            }

            let standardError = new Error(error.message);
            standardError.code = "UNKNOWN_ERROR";
            standardError.details = null;
            standardError.status = error.response?.status;
            standardError.response = error.response;
            standardError.config = error.config;
            standardError.code = error.code || standardError.code;
            // Preserve raw response data for downstream consumers (e.g., form error handling)
            standardError.responseData = error.response?.data ?? null;

            if (error.response && error.response.data) {
                const data = error.response.data;
                if (data.error_code) {
                    standardError.code = data.error_code;
                    // additive: capacity/transition chyby vracejí text v `detail`
                    // (např. CAPACITY_FULL) — podržet ho i v `details`, aby FE
                    // mohl zobrazit konkrétní hlášku (BL-04).
                    standardError.details = data.details ?? data.detail ?? null;
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
