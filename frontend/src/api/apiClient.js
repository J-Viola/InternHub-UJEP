import axios from 'axios';
import dummyData from './_data_/localDatabase';
import { useNavigate } from "react-router-dom"

const API_ROOT = '/api';
const DUMMY_DATA = false;
const DEFAULT_URL = 'http://localhost:8000';

// Pro lokální vývoj použijeme DEFAULT_URL, pro produkci REACT_APP_API_URL
const BASE_URL = process.env.REACT_APP_API_URL 
    ? `${process.env.REACT_APP_API_URL}${API_ROOT}`
    : `${DEFAULT_URL}${API_ROOT}`;

console.log("API URL:", BASE_URL);


export const createApiClient = (navigate) => {
    // API client - default
    const apiClient = axios.create({
        baseURL: BASE_URL,
        headers: {
            'Content-Type': 'application/json',
        },
        withCredentials: true,
    });

    if (DUMMY_DATA) {
        const dummyDB = dummyData;
        console.log("Dummy Data:", dummyData);
        
        return {
            ...apiClient,
            dummyDB: dummyDB
        };
    }

    // Interceptor pro request
    apiClient.interceptors.request.use(request => {
        console.log('Starting Request:', request);
        return request;
    });

    // Interceptor pro response requestu
    apiClient.interceptors.response.use(
        response => {
            console.log('Response:', response);
            return response;
        },
        error => {
            console.error('Response Error:', error);
            if (error.response) {
                console.error('Error Response Data:', error.response.data);
                console.error('Error Response Status:', error.response.status);
                console.error('Error Response Headers:', error.response.headers);
                if(error.response.status === 401){
                    navigate('/');
                }
            }
            return Promise.reject(error);
        }
    );

    return apiClient;
};
