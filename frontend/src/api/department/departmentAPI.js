import { useApi } from "@hooks/useApi";
import { useMessage } from "@hooks/MessageContext";
//import { createParams } from "@api/createParams";

export const useDepartmentAPI = () => {
    const api = useApi();
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

    const getDepartmentStudents = async () => {
        try {
            const response = await api.get('/departments/department-students/');
            if (response && response.data) {
                return response.data;
            }
            return [];
        } catch (error) {
            throw error;
        }
    };


    return {
        getNabidky,
        getDepartmentStudents,
    };
};