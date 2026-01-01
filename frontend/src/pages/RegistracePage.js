import React, {useState} from "react";
import Container from "@core/Container/Container";
import BackButton from "@core/Button/BackButton";
import CompanyForm from "@components/Forms/CompanyForm";
import { useUserAPI } from "@api/user/userAPI";
import { useAuth } from "@auth/Auth";
import { useMessage } from "@hooks/MessageContext";
import { useTranslation } from "react-i18next";


export default function RegistracePage() {
    const { t } = useTranslation();
    const user = useUserAPI();
    const { addMessage } = useMessage();
    const [errors, setErrors] = useState({});
    const { login } = useAuth();

    const handleRegistration = async (companyData) => {
        setErrors({});
        try {
            await user.postRegister(companyData);
            addMessage(t('registration.success'), "S");

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
            const errorCode = error.code;
            const detail = error.response?.data?.detail;
            const fallback = detail || t('registration.check_form');
            const message = errorCode ? t(`api_errors.${errorCode}`, { defaultValue: fallback }) : fallback;
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
