import { useApi } from "@hooks/useApi";

export const useUserAPI = () => {
    const api = useApi();

    const postRegister = async (data) => {
        const formData = new FormData();
        
        formData.append('email', data.executiveEmail);
        formData.append('phone', data.executivePhone);
        formData.append('password', data.executivePassword1);
        formData.append('password2', data.executivePassword2);
        formData.append('ico', data.ico.toString());
        formData.append('companyName', data.companyName);
        formData.append('address', data.address);
        formData.append('executiveName', data.executiveName);
        formData.append('executiveSurname', data.executiveSurname);

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


    const postUpdateProfile = async (data) => {
        try {
            const response = await api.post('/users/XXXXXX/', data, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                },
            });
            return response.data;
        } catch (error) {
            console.error("Chyba při registraci organizace:", error);
            throw error;
        }
    }

    
    return {
        postRegister,
        postUpdateProfile
    };
};