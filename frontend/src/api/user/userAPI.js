import { useApi } from "@hooks/useApi";

export const useUserAPI = () => {
    const api = useApi();

    const postRegister = async (data) => {
        const formData = new FormData();

        // data k předání
        formData.append('email', data.executiveEmail);
        formData.append('phone', data.executivePhone);
        formData.append('password', data.executivePassword1);
        formData.append('password2', data.executivePassword2);
        formData.append('ico', data.ico);
        formData.append('dic', data.dic);
        formData.append('companyName', data.company_name);
        formData.append('first_name', data.executiveName);
        formData.append('last_name', data.executiveSurname);
        formData.append('title_before', data.titleBefore || '');
        formData.append('title_after', data.titleAfter || '');
        formData.append('address', data.address || '')


        if (data.logo) {
            formData.append('logo', data.logo);
        }

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
            if (dropdown) {
                const dropDownData = response.data.map(res => ({
                    label: `${res.name}`,
                    value: res.id
                }));
                console.log(dropDownData);
                return dropDownData;
            } else {
                //console.log("RESPONSE DROPDOWN FALSE", response.data)
                return response.data;
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
            const formData = new FormData();

            // Append user data to formData
            Object.keys(userData).forEach(key => {
                if (userData[key] !== null && userData[key] !== undefined) {
                    formData.append(key, userData[key]);
                }
            });

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
            const formData = new FormData();

            // Append user data to formData
            Object.keys(userData).forEach(key => {
                if (userData[key] !== null && userData[key] !== undefined) {
                    formData.append(key, userData[key]);
                }
            });

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
            const formData = new FormData();

            Object.keys(userData).forEach(key => {
                const value = userData[key];

                if (value === null || value === undefined) return;

                if (key === 'employer_profile') return; // Skip nested read-only or complex objects if not needed for update

                // Skip cv_file if it is not a File object (meaning it's likely an existing URL string)
                if (key === 'cv_file' && !(value instanceof File)) {
                    return;
                }

                // Skip profile_picture if it is an existing URL (starts with http or /)
                // We only want to send it if it's a new Base64 string (starts with data:)
                if (key === 'profile_picture' && typeof value === 'string' && (value.startsWith('http') || value.startsWith('/'))) {
                    return;
                }

                if (key === 'skills' && Array.isArray(value)) {
                    // Send as JSON string for JSONField in multipart
                    formData.append(key, JSON.stringify(value));
                } else if (value instanceof File) {
                    formData.append(key, value);
                } else if (typeof value === 'object' && !Array.isArray(value)) {
                     formData.append(key, JSON.stringify(value));
                } else {
                    formData.append(key, value);
                }
            });

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
