import { useApi } from "@hooks/useApi";
import { buildFormData } from "@utils/formDataUtils";

export const useUserAPI = () => {
    const api = useApi();

    const postRegister = async (data) => {
        const mappedData = {
            email: data.executiveEmail,
            phone: data.executivePhone,
            password: data.executivePassword1,
            password2: data.executivePassword2,
            ico: data.ico,
            dic: data.dic,
            companyName: data.company_name,
            first_name: data.executiveName,
            last_name: data.executiveSurname,
            title_before: data.titleBefore || '',
            title_after: data.titleAfter || '',
            address: data.address || '',
            logo: data.logo
        };

        const formData = buildFormData(mappedData);

        try {
            const response = await api.post('/users/register/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            return response.data;
        } catch (error) {
            console.error("Chyba při registraci organizace:", error);
            throw error;
        }
    };

    const getOrganizationUsers = async (dropdown = true) => {
        try {
            const response = await api.get('/users/organization-users/');
            const data = response.data.results !== undefined ? response.data.results : response.data;

            if (dropdown) {
                const dropDownData = data.map(res => ({
                    label: `${res.name}`,
                    value: res.id
                }));
                console.log(dropDownData);
                return dropDownData;
            } else {
                return data;
            }
        } catch (error) {
            console.error('Chyba při získávání uživatelů organizace:', error);
            throw error;
        }
    };

    const getCurrentUserProfile = async () => {
        try {
            const response = await api.get('/users/profile/');
            return response.data;
        } catch (error) {
            console.error('Chyba při získávání profilu uživatele:', error);
            throw error;
        }
    };

    const getStudentProfile = async (id) => {
        try {
            const response = await api.get(`/users/student-profile/${id}`);
            return response.data;
        } catch (error) {
            console.error('Chyba při získávání profilu uživatele:', error);
            throw error;
        }
    };

    const getAllStudents = async ({ page = 1, pageSize = 10, search = '' } = {}) => {
        try {
            const params = { page, page_size: pageSize };
            if (search) params.search = search;
            const response = await api.get('/users/all-students/', { params });
            return response.data;
        } catch (error) {
            throw error;
        }
    };

    const getAllDepartmentProfessors = async () => {
        try {
            const response = await api.get('/departments/department-professor/all/');
            if (response && response.data) {
                return response.data;
            }
            return [];
        } catch (error) {
            throw error;
        }
    };

    const createUser = async (userData) => {
        try {
            const formData = buildFormData(userData);

            const response = await api.post('/users/organization-users/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            return response.data;
        } catch (error) {
            console.error("Chyba při vytváření uživatele:", error);
            throw error;
        }
    };

    const updateUser = async (id, userData) => {
        try {
            const formData = buildFormData(userData);

            const response = await api.put(`/users/organization-users/${id}/`, formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            return response.data;
        } catch (error) {
            console.error("Chyba při aktualizaci uživatele:", error);
            throw error;
        }
    };

    const getUserById = async (id) => {
        try {
            const response = await api.get(`/users/organization-users/${id}/`);
            return response.data;
        } catch (error) {
            console.error('Chyba při získávání uživatele:', error);
            throw error;
        }
    };

    const updateProfile = async (userData) => {
        try {
            const cleanData = { ...userData };

            // Special handling logic from original updateProfile
            if (cleanData.employer_profile) delete cleanData.employer_profile;

            if (cleanData.cv_file && !(cleanData.cv_file instanceof File)) {
                delete cleanData.cv_file;
            }

            if (cleanData.profile_picture && typeof cleanData.profile_picture === 'string' &&
                (cleanData.profile_picture.startsWith('http') || cleanData.profile_picture.startsWith('/'))) {
                delete cleanData.profile_picture;
            }

            const formData = buildFormData(cleanData);

            const response = await api.patch('/users/profile/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            return response.data;
        } catch (error) {
            console.error('Chyba při aktualizaci profilu:', error);
            throw error;
        }
    };

    const changePassword = async (passwordData) => {
        try {
            const response = await api.post('/users/change-password/', passwordData);
            return response.data;
        } catch (error) {
            console.error('Chyba při změně hesla:', error);
            throw error;
        }
    };

    const requestPasswordReset = async (email) => {
        try {
            const response = await api.post('/users/password-reset/', { email });
            return response.data;
        } catch (error) {
            console.error('Chyba při žádosti o reset hesla:', error);
            throw error;
        }
    };

    const confirmPasswordReset = async (data) => {
        try {
            const response = await api.post('/users/password-reset-confirm/', data);
            return response.data;
        } catch (error) {
            console.error('Chyba při potvrzení resetu hesla:', error);
            throw error;
        }
    };

    return {
        postRegister,
        getOrganizationUsers,
        getCurrentUserProfile,
        getStudentProfile,
        getAllStudents,
        getAllDepartmentProfessors,
        createUser,
        updateUser,
        getUserById,
        updateProfile,
        changePassword,
        requestPasswordReset,
        confirmPasswordReset
    };
};
