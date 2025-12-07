import React, {useEffect, useState} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import BackButton from "@core/Button/BackButton";
import TextBox from "@core/Form/TextBox";
import Nav from "@components/core/Nav";
import CustomDatePicker from "@core/Form/DatePicker";
import Button from "@components/core/Button/Button";
import { useAresAPI } from "@api/ARES/aresJusticeAPI";
import { useUserAPI } from "@api/user/userAPI";
import CompanyForm from "@components/Forms/CompanyForm";
import { useAuth } from "src/services/auth/Auth";
import { useMessage } from "@hooks/MessageContext";

// UDĚLAT POLE PRO TITULY - PŘED A ZA + HANDLER NA SUCCESS REGISTRACI
export default function RegistracePage() {
    const ares = useAresAPI();
    const user = useUserAPI();
    const { addMessage } = useMessage();
    const [entity, setEntity] = useState(null);
    const [formValue, setFormValue] = useState({});
    const [aresFetched, setAresFetched] = useState(false);
    const [errors, setErrors] = useState({});
    const { login } = useAuth();

    useEffect(() => {
        console.log("Form value:", formValue);
    }, [formValue]);

    // handleARESCall, handleFormValues, handleFileChange - removing as they seem unused by the smart CompanyForm component
    // or if they are used, CompanyForm ignores them.
    // Let's keep them for now if I am wrong about CompanyForm usage, but based on file content, they are ignored.
    // Actually, I will remove them to clean up, as instructed.

    const handleRegistration = async (data) => {
        setErrors({});
        try {
            console.log("Sending registration data:", data);
            const res = await user.postRegister(data);
            console.log("Registration response:", res);
            res && setEntity(res);
            addMessage("Registrace úspěšná", "S");
            
            // po registraci zavolám login
            const logData = {
                "email": data.email,
                "password": data.password   
            };
            const loginRes = await login(logData);
            console.log("Login Res Organizace", loginRes);

        } catch (error) {
            console.error("Error registration fetch:", error);
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
            // throw error; // No need to throw if handled
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