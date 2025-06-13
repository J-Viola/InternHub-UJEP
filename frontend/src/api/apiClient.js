import axios from 'axios';

const API_ROOT = '/api';
const DEFAULT_URL = 'http://localhost:8000';

const BASE_URL = process.env.REACT_APP_API_URL 
    ? `${process.env.REACT_APP_API_URL}${API_ROOT}`
    : `${DEFAULT_URL}${API_ROOT}`;

console.log("API URL:", BASE_URL);

export const createApiClient = () => {
  const apiClient = axios.create({
      baseURL: BASE_URL,
      headers: {
          'Content-Type': 'application/json'
      },
  });
  return apiClient;
};
