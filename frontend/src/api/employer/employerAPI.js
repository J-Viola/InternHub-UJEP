import { useApi } from "@hooks/useApi";

export const useEmployerAPI = () => {
    const api = useApi();

    const getAllEmployers = async () => {
        const response = await api.get('/users/companies/');
        return response.data;
    };

    const getEmployerById = async (id) => {
        const response = await api.get(`/users/companies/${id}/`);
        return response.data;
    };

    const createEmployer = async (employerData) => {
        const response = await api.post('/users/companies/', employerData);
        return response.data;
    };

    const updateEmployer = async (id, employerData) => {
        const response = await api.patch(`/users/companies/${id}/`, employerData);
        return response.data;
    };

    const deleteEmployer = async (id) => {
        await api.delete(`/users/companies/${id}/`);
        return true;
    };

    return {
        getAllEmployers,
        getEmployerById,
        createEmployer,
        updateEmployer,
        deleteEmployer,
    };
};
