import { useAuth } from '@services/auth/Auth';

export const useApi = () => {
    const { apiClient } = useAuth();
    
    if (!apiClient) {
        throw Error('Auth provider neposkytl apiClienta!');
    }
    
    return apiClient;
};