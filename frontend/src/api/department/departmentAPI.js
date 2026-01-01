import { useApi } from "@hooks/useApi";
import { useMessage } from "@hooks/MessageContext";

export const useDepartmentAPI = () => {
    const api = useApi();

    const getNabidky = async (params = {}) => {
        try {
            const response = await api.get('/practices/student/', { params })

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

    const getAllDepartments = async () => {
        try {
            // Přidáme page_size=100 pro získání více kateder, nebo implementovat stránkování na FE
            const response = await api.get('/departments/admin-departments/?page_size=100');
            if (response?.data) {
                return response.data.results || response.data;
            }
            return [];
        } catch (error) {
            console.error("Chyba při získávání kateder:", error);
            return [];
        }
    };

    const getDepartmentById = async (id) => {
        try {
            const response = await api.get(`/departments/admin-departments/${id}/`);
            if (response?.data) {
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při získávání katedry:", error);
            return null;
        }
    };

    const createDepartment = async (departmentData) => {
        try {
            const response = await api.post('/departments/admin-departments/', departmentData);
            if (response?.data) {
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při vytváření katedry:", error);
            throw error;
        }
    };

    const updateDepartment = async (id, departmentData) => {
        try {
            const response = await api.put(`/departments/admin-departments/${id}/`, departmentData);
            if (response?.data) {
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při aktualizaci katedry:", error);
            throw error;
        }
    };

    const deleteDepartment = async (id) => {
        try {
            await api.delete(`/departments/admin-departments/${id}/`);
            return true;
        } catch (error) {
            console.error("Chyba při mazání katedry:", error);
            throw error;
        }
    };

    const getProfessorById = async (id) => {
        try {
            const response = await api.get(`/departments/department-professor/${id}/`);
            if (response?.data) {
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při získávání profesora:", error);
            throw error;
        }
    };

    const updateProfessor = async (id, data) => {
        try {
            const response = await api.patch(`/departments/department-professor/${id}/`, data);
            if (response?.data) {
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při aktualizaci profesora:", error);
            throw error;
        }
    };

    return {
        getAllDepartments,
        getDepartmentById,
        createDepartment,
        updateDepartment,
        deleteDepartment,
        getDepartmentStudents,
        getProfessorById,
        updateProfessor,
    };
};
