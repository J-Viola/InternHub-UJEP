import { useApi } from "@hooks/useApi";

export const useUserAPI = () => {
    const api = useApi();

    // pro organizaci
    const postRegister = async (data) => {
        const registrationData = {
            email: data.executiveEmail,
            phone: data.executivePhone,
            password: data.executivePassword1,
            password2: data.executivePassword2,
            ico: data.ico,
            logo: "asdasdasdasd", //dodělat na soubor
            companyName: data.companyName,
            address: data.address,
            executiveName: data.executiveName,
            executiveSurname: data.executiveSurname
        };

        try {
            const response = await api.post('/users/register/', registrationData);
            return response.data;
        } catch (error) {
            console.error("Chyba při registraci organizace:", error);
            throw error;
        }
    };

    return {
        postRegister
    };
};