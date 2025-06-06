import { useAuth } from '@auth/AuthContext';

export const useApi = () => {
    const { apiClient } = useAuth();
    return apiClient;
};