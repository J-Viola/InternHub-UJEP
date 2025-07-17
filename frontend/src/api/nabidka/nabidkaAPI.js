import { useApi } from "@hooks/useApi";
import { useMessage } from "@hooks/MessageContext";
//import { createParams } from "@api/createParams";

export const useNabidkaAPI = () => {
    const api = useApi();
    const { addMessage } = useMessage(); 
    //const practices = api.dummyDB.practices;

    const getNabidky = async (params = {}) => {
        try {
            const response = await api.get('/practices/practices/search/', { params })
            
            if (response && response.data) {
                return response.data.results || response.data
            }
            
            return []

        } catch (error) {
            console.error("Chyba při získávání nabídek:", error);
            throw error;
        }
    };

    const getNabidkaById = async (id) => {
        try {
            const response = await api.get(`/practices/practices/${id}`)
            
            if (response && response.data) {
                return response.data
            }
            
            return null

        } catch (error) {
            console.error("Chyba při získávání nabídky podle ID:", error);
            throw error;
        }
    }

    const createNabidka = async (data) => {
        try {
            const formData = new FormData();
            
            Object.keys(data).forEach(key => {
                formData.append(key, data[key]);
            });

            const response = await api.post('/practices/practices/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            
            if (response && response.data) {
                sessionStorage.setItem("pendingMessage", JSON.stringify({
                    text: `Nabídka byla úspěšně vytvořena`,
                    type: "S"
                }));
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při vytváření nabídky:", error);
            throw error;
        }
    };

    const applyNabidka = async (data) => {
        try {
            const formData = new FormData();
            
            Object.keys(data).forEach(key => {
                formData.append(key, data[key]);
            });

            const response = await api.post('/practices/practices/apply_student_practice/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            
            if (response && response.data) {
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při vytváření nabídky:", error);
            throw error;
        }
    }

    const getPracticeUserRelations = async () => {
        try {
            const response = await api.get('/practices/practices/get_practice_user_relations/');

            if (response && response.data) {
                return response.data;
            }
            return null

        } catch (error) {
            console.error('Chyba při získávání uživatelů organizace:', error);
            throw error;
        }
    };

    return {
        getNabidky,
        getNabidkaById,
        createNabidka,
        applyNabidka,
        getPracticeUserRelations
    };
};