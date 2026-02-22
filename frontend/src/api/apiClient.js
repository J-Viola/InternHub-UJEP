import axios from 'axios';

const API_ROOT = '/api';
const DEFAULT_URL = 'http://localhost:8000';

// Use REACT_APP_API_URL in production, fallback to localhost for dev
const BASE_URL = process.env.REACT_APP_API_URL
    ? `${process.env.REACT_APP_API_URL}${API_ROOT}`
    : `${DEFAULT_URL}${API_ROOT}`;


export const createApiClient = (navigate) => {
    const apiClient = axios.create({
        baseURL: BASE_URL,
        headers: {
            'Content-Type': 'application/json',
        },
        withCredentials: true,
    });

    // Response interceptor — redirect on persistent 401
    apiClient.interceptors.response.use(
        response => response,
        error => {
            if (error.response?.status === 401) {
                navigate('/');
            }
            return Promise.reject(error);
        }
    );

    return apiClient;
};
