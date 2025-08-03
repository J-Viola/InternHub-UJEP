import { useApi } from "@hooks/useApi";

export const useAresAPI = () => {
    const api = useApi();

    const getData = async (ico) => {
        try {
            const response = await api.post('/users/ares-justice/', { ico: ico });
            return response.data;
        } catch (error) {
            console.error("Chyba při získávání nabídek:", error);
            throw error;
        }
    };

    return {
        getData
    };
};