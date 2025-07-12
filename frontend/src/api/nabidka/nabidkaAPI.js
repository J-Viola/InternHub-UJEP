import { useApi } from "@hooks/useApi";
//import { createParams } from "@api/createParams";

export const useNabidkaAPI = () => {
    const api = useApi();
    //const practices = api.dummyDB.practices;

    const getNabidky = async (params = {}) => {
        try {

            const response = api.get('/practices/practices/')
            
            if (response) {
                return(response)
            }

        } catch (error) {
            console.error("Chyba při získávání nabídek:", error);
            throw error;
        }
    };

    const getNabidkaById = async (id) => {
        try {
            const response = api.get(`/practices/practices/${id}`)
            
            if (response) {
                return(response)
            }

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