import React, {useState} from "react";
import Container from "@core/Container/Container";
import BackButton from "@core/Button/BackButton";
import CompanyForm from "@components/Forms/CompanyForm";
import { useUserAPI } from "@api/user/userAPI";
import { useAuth } from "@auth/Auth";
import { useMessage } from "@hooks/MessageContext";


import getApiErrorMessage from "@utils/apiErrorUtils";
export default function RegistracePage() {
    const user = useUserAPI();
    const { addMessage } = useMessage();
    const [errors, setErrors] = useState({});
    const { login } = useAuth();

    const handleRegistration = async (companyData) => {
        setErrors({});
        try {
            await user.postRegister(companyData);
            addMessage("Registrace úspěšná", "S");

            const logData = {
                "email": companyData.executiveEmail,
                "password": companyData.executivePassword1
            };
            await login(logData);

        } catch (error) {
            console.error(error);
            if (error.details) {
                setErrors(error.details);
            } else if (error.response?.data) {
                setErrors(error.response.data);
            }
            const detail = error.response?.data?.detail;
            const fallback = detail || "Zkontrolujte prosím formulář.";
            const message = getApiErrorMessage(error, fallback);
            addMessage(message, "E");
        }
    }

    const renderForm = () => {
        return <CompanyForm
            handleCreate={handleRegistration}
            errors={errors}
        />;
    };

    return(
        <>
            <BackButton></BackButton>
            <Container property={"bg-white mt-2 p-8 rounded-lg shadow-sm"}>
                {renderForm()}
            </Container>
        </>
    );
}
