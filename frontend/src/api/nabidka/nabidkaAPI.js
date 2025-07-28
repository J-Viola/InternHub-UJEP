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

    const getOrganizationPractices = async () => {
        try {
            const response = await api.get('/practices/practices/organization_practices/');

            if (response && response.data) {
                return response.data;
            }
            return []

        } catch (error) {
            console.error('Chyba při získávání praxí organizace:', error);
            throw error;
        }
    };

    const getNabidkyByUserDepartment = async () => {
        try {
            const response = await api.get('/practices/practices/by_user_department/');
            if (response && response.data) {
                return response.data;
            }
            return { approved_practices: [], to_approve_practices: [] };
        } catch (error) {
            console.error('Chyba při získávání nabídek podle katedry uživatele:', error);
            throw error;
        }
    };

    const changeStatus = async (id, status) => {
        try {
            const response = await api.post(`/practices/${id}/change-pending/`, status);
            if (response && response.data) {
                return response.data;
            }
        } catch (error) {
            console.error('Chyba při změně stavu nabídky:', error);
            throw error;
        }
    };

    const calculateEndDate = async (startDate, employmentLoad) => {
        try {
            const response = await api.post('/practices/get-end-date/', {
                start_date: startDate,
                coefficient: employmentLoad
            });
            
            if (response && response.data) {
                return response.data.end_date;
            }
            return null;
        } catch (error) {
            console.error('Chyba při výpočtu koncového data:', error);
            throw error;
        }
    };

    const updateNabidka = async (id, data, isPartial = false) => {
        try {
            const formData = new FormData();
            
            Object.keys(data).forEach(key => {
                formData.append(key, data[key]);
            });

            const method = isPartial ? 'patch' : 'put';
            const response = await api[method](`/practices/practices/${id}/`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            
            if (response && response.data) {
                sessionStorage.setItem("pendingMessage", JSON.stringify({
                    text: `Nabídka byla úspěšně aktualizována`,
                    type: "S"
                }));
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při aktualizaci nabídky:", error);
            throw error;
        }
    };

    return {
        getNabidky,
        getNabidkaById,
        createNabidka,
        applyNabidka,
        getPracticeUserRelations,
        getOrganizationPractices,
        getNabidkyByUserDepartment,
        changeStatus,
        calculateEndDate,
        updateNabidka
    };
};