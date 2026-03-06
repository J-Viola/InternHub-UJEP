import { useApi } from "@hooks/useApi";
import { useMessage } from "@hooks/MessageContext";
import { buildFormData } from "@utils/formDataUtils";

export const useCompanyAPI = () => {
    const api = useApi();

    // CRUD operace pro společnosti
    const getAllCompanies = async () => {
        try {
            const response = await api.get('/users/companies/');
            if (response && response.data) {
                return response.data.results || response.data;
            }
            return [];
        } catch (error) {
            console.error("Chyba při získávání společností:", error);
            throw error;
        }
    };

    const getCompanyById = async (id) => {
        try {
            const response = await api.get(`/users/companies/${id}/`);
            if (response && response.data) {
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při získávání společnosti:", error);
            throw error;
        }
    };

    const createCompany = async (companyData) => {
        try {
            const formData = buildFormData(companyData);

            const response = await api.post('/users/companies/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            if (response && response.data) {
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při vytváření společnosti:", error);
            throw error;
        }
    };

    const updateCompany = async (id, companyData) => {
        try {
            const formData = buildFormData(companyData);

            const response = await api.put(`/users/companies/${id}/`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            if (response && response.data) {
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Chyba při aktualizaci společnosti:", error);
            throw error;
        }
    };

    const deleteCompany = async (id) => {
        try {
            await api.delete(`/users/companies/${id}/`);
            return true;
        } catch (error) {
            console.error("Chyba při mazání společnosti:", error);
            throw error;
        }
    };

    return {
        getAllCompanies,
        getCompanyById,
        createCompany,
        updateCompany,
        deleteCompany,
    };
};
