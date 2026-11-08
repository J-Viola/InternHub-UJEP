import React, { useState } from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Headings from "@core/Text/Headings";
import TextField from "@core/Form/TextField";
import Button from "@core/Button/Button";
import { useUserAPI } from "@api/user/userAPI";
import { useMessage } from "@hooks/MessageContext";
import { useParams, useNavigate } from "react-router-dom";

import getApiErrorMessage from "@utils/apiErrorUtils";
export default function PasswordResetConfirmPage() {
    const { confirmPasswordReset } = useUserAPI();
    const { addMessage } = useMessage();
    const { uid, token } = useParams();
    const navigate = useNavigate();

    const [formData, setFormData] = useState({
        new_password: "",
        new_password_confirm: ""
    });
    const [errors, setErrors] = useState({});

    const handleInputChange = (fieldData) => {
        setFormData(prev => ({ ...prev, ...fieldData }));
        const fieldName = Object.keys(fieldData)[0];
        if (errors[fieldName]) {
            setErrors(prev => {
                const newErrors = { ...prev };
                delete newErrors[fieldName];
                return newErrors;
            });
        }
    };

    const handleSubmit = async () => {
        if (formData.new_password !== formData.new_password_confirm) {
            setErrors({ new_password_confirm: ["Hesla se neshodují"] });
            return;
        }

        try {
            await confirmPasswordReset({
                uidb64: uid,
                token: token,
                new_password: formData.new_password,
                new_password_confirm: formData.new_password_confirm
            });
            addMessage("Heslo bylo úspěšně změněno. Nyní se můžete přihlásit.", "S");
            navigate("/");
        } catch (error) {
            console.error("Reset hesla selhal:", error?.response?.status || error?.code || "UNKNOWN_ERROR");
            if (error.details) {
                setErrors(error.details);
            }
            addMessage(getApiErrorMessage(error, "Chyba při změně hesla. Odkaz může být neplatný nebo vypršel."), "E");
        }
    };

    return (
        <Container property="flex items-center justify-center">
            <ContainerForEntity property="w-full max-w-md p-8">
                <Headings sizeTag="h2" property="mb-6 text-center">{"Nastavení nového hesla"}</Headings>

                <Container property="space-y-4">
                    <TextField
                        id="new_password"
                        type="password"
                        label={"Nové heslo"}
                        placeholder={"Zadejte nové heslo"}
                        value={formData.new_password}
                        onChange={handleInputChange}
                        error={errors.new_password?.[0]}
                        required
                    />

                    <TextField
                        id="new_password_confirm"
                        type="password"
                        label={"Potvrzení nového hesla"}
                        placeholder={"Zadejte heslo znovu"}
                        value={formData.new_password_confirm}
                        onChange={handleInputChange}
                        error={errors.new_password_confirm?.[0]}
                        required
                    />

                    <Container property="flex justify-center mt-6">
                        <Button onClick={handleSubmit} property="w-full">
                            {"Změnit heslo"}
                        </Button>
                    </Container>
                </Container>
            </ContainerForEntity>
        </Container>
    );
}
