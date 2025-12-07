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
        formData.append('phone', data.executivePhone || '' )
        formData.append('address', data.address || '' )


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

    const getAllStudents = async () => {
        try {
            const response = await api.get('/users/all-students/');
            return response.data;
        } catch (error) {
            console.error('Chyba při získávání všech studentů:', error);
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
            const response = await api.patch('/users/profile/', userData);
            return response.data;
        } catch (error) {
            console.error('Chyba při aktualizaci profilu:', error);
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
        updateProfile
    };
};