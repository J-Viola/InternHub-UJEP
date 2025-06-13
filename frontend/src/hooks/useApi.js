import { useAuth } from '@auth/AuthContext';

export const useApi = () => {
    const { apiClient } = useAuth();
    
    if (!apiClient) {
        throw Error('Auth provider neposkytl apiClienta!');
    }
    
    return apiClient;
};