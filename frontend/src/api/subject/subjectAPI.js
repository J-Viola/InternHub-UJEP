import { useApi } from "@hooks/useApi";
import { useMessage } from "@hooks/MessageContext";

export const useSubjectAPI = () => {
    const api = useApi();

    const getMySubjects = async (params = {}) => {
        try {
            const response = await api.get('/subjects/my-subjects/', { params })
            
            if (response && response.data) {
                return response.data
            }
            
            return []

        } catch (error) {
            console.error("Chyba při získávání předmětů:", error);
            throw error;
        }
    };

    const getDepartmentSubjects = async (params = {}) => {
        try {
            const response = await api.get('/subjects/subjects/department-subjects/', { params })
            
            if (response && response.data) {
                return response.data
            }
            
            return []

        } catch (error) {
            console.error("Chyba při získávání předmětů katedry:", error);
            throw error;
        }
    };

    const getAllSubjects = async (params = {}) => {
        try {
            const response = await api.get('/subjects/subjects/', { params })
            
            if (response && response.data) {
                return response.data.results || response.data
            }
            
            return []

        } catch (error) {
            console.error("Chyba při získávání všech předmětů:", error);
            throw error;
        }
    };

    const createSubject = async (data) => {
        try{
            const formData = new FormData();

            Object.keys(data).forEach(key => {
                formData.append(key, data[key]);
            }
            );

            const response = await api.post('/subjects/subjects/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            if (response && response.data) {
                return response.data;
            }

            return null;
        }
        catch (error){
            console.error("Chyba při vytváření předmětu:", error);
            throw error;
        }
    }

    const updateSubject = async (id, data) => {
        try {
            const formData = new FormData();

            Object.keys(data).forEach(key => {
                if (data[key] !== null && data[key] !== undefined) {
                    formData.append(key, data[key]);
                }
            });

            const response = await api.put(`/subjects/subjects/${id}/`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });

            if (response && response.data) {
                return response.data;
            }

            return null;
        } catch (error) {
            console.error("Chyba při aktualizaci předmětu:", error);
            throw error;
        }
    };

    const getSubjectById = async (id) => {
        try {
            const response = await api.get(`/subjects/subjects/${id}/`);

            if (response && response.data) {
                return response.data;
            }

            return null;
        } catch (error) {
            console.error("Chyba při získávání předmětu:", error);
            throw error;
        }
    };

    return {
        getMySubjects,
        getDepartmentSubjects,
        getAllSubjects,
        createSubject,
        updateSubject,
        getSubjectById
    };
};
