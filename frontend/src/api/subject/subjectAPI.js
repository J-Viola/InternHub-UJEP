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

    return {
        getMySubjects,
        getDepartmentSubjects,
        getAllSubjects,
    };
}; 