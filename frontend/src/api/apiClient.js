import axios from 'axios';

if (process.env.REACT_APP_API_URL) {
    console.log("ENV URL JE NAČTENA:", process.env.REACT_APP_API_URL);
}

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
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
