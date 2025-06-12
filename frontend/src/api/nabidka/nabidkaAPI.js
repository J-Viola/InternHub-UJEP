import { useApi } from "@hooks/useApi";
import { createParams } from "@api/createParams";

export const useNabidkaAPI = () => {
    const api = useApi();

    const getNabidky = async (params = {}) => {
        try {
            const queryString = createParams(params);
            console.log("getNabidky call, queryString: ", queryString);
            
            const response = await api.get(`nabidka${queryString}`);
            return response.data;
        } catch (error) {
            console.error("Chyba při získávání nabídek:", error);
            throw error;
        }
    };

    return {
        getNabidky
    };
};