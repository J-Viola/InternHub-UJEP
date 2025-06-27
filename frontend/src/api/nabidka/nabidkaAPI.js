import { useApi } from "@hooks/useApi";
//import { createParams } from "@api/createParams";

export const useNabidkaAPI = () => {
    const api = useApi();
    const practices = api.dummyDB.practices;

    const getNabidky = async (params = {}) => {
        try {
            
            let filteredData = practices;
            
            if (Object.keys(params).length > 0) {
                filteredData = practices.filter(practice => {
                    return Object.entries(params).every(([key, value]) => {
                        if (practice.hasOwnProperty(key)) {
                            if (typeof value === 'string' && typeof practice[key] === 'string') {
                                return practice[key].toLowerCase().includes(value.toLowerCase());
                            }
                            return practice[key] === value;
                        }
                        return false;
                    });
                });
            }

            const response = {
                data: filteredData
            };

            return response.data;
        } catch (error) {
            console.error("Chyba při získávání nabídek:", error);
            throw error;
        }
    };

    const getNabidkaById = async (id) => {
        try {
            const practice = practices.find(practice => practice.practice_id === parseInt(id));
            return practice || null;
        } catch (error) {
            console.error("Chyba při získávání nabídky podle ID:", error);
            throw error;
        }
    }

    return {
        getNabidky,
        getNabidkaById
    };
};