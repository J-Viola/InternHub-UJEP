import React, {useState} from "react";
import Container from "@core/Container/Container";
import BackButton from "@core/Button/BackButton";
import Nav from "@components/core/Nav";
import CompanyForm from "@components/Forms/CompanyForm";
import { useUserAPI } from "@api/user/userAPI";
import { useAuth } from "src/services/auth/Auth";
import { useMessage } from "@hooks/MessageContext";


export default function RegistracePage() {
    const user = useUserAPI();
    const { addMessage } = useMessage();
    const [errors, setErrors] = useState({});
    const { login } = useAuth();

    const handleRegistration = async (companyData) => {
        setErrors({});
        try {
            const res = await user.postRegister(companyData);
            addMessage("Registrace úspěšná", "S");
            
            const logData = {
                "email": companyData.executiveEmail,
                "password": companyData.executivePassword1   
            };
            await login(logData);

        } catch (error) {
            if (error.response?.data) {
                setErrors(error.response.data);
                if (error.response.data.detail) {
                    addMessage("Chyba při registraci: " + error.response.data.detail, "E");
                } else {
                    addMessage("Zkontrolujte prosím formulář.", "E");
                }
            } else {
                addMessage("Chyba při registraci: " + error.message, "E");
            }
        }
    }

    const renderForm = () => {
        return <CompanyForm 
            handleCreate={handleRegistration}
            errors={errors}
        />;
    };

    return(
        <Container property={"min-h-screen"}>
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <BackButton></BackButton>
                <Container property={"bg-gray-50 mt-2 p-4 rounded-lg"}>
                    {renderForm()}
                </Container>
            </Container>
        </Container>
    );
}