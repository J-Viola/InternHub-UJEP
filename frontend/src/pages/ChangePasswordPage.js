import React, { useState } from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Headings from "@core/Text/Headings";
import TextField from "@core/Form/TextField";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import { useUserAPI } from "@api/user/userAPI";
import { useMessage } from "@hooks/MessageContext";
import { useNavigate } from "react-router-dom";

export default function ChangePasswordPage() {
    const { changePassword } = useUserAPI();
    const { addMessage } = useMessage();
    const navigate = useNavigate();
    
    const [formData, setFormData] = useState({
        old_password: "",
        new_password: "",
        new_password_confirm: ""
    });
    
    const [errors, setErrors] = useState({});

    const handleInputChange = (fieldData) => {
        setFormData(prev => ({ ...prev, ...fieldData }));
        // Clear error for the field when user types
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
            setErrors({ new_password_confirm: "Nová hesla se neshodují." });
            return;
        }

        try {
            await changePassword(formData);
            addMessage("Heslo bylo úspěšně změněno", "S");
            navigate("/profil");
        } catch (error) {
            if (error.response && error.response.data) {
                setErrors(error.response.data);
            } else {
                addMessage("Chyba při změně hesla", "E");
            }
        }
    };

    return (
        <Container property="max-w-md mx-auto">
            <ContainerForEntity property="p-8">
                <BackButton />
                <Headings sizeTag="h2" property="mb-6 mt-4">Změna hesla</Headings>
                
                <Container property="space-y-4">
                    <TextField 
                        id="old_password"
                        type="password"
                        label="Staré heslo"
                        placeholder="Zadejte staré heslo"
                        value={formData.old_password}
                        onChange={handleInputChange}
                        error={errors.old_password?.[0]}
                        required
                    />
                    
                    <TextField 
                        id="new_password"
                        type="password"
                        label="Nové heslo"
                        placeholder="Zadejte nové heslo"
                        value={formData.new_password}
                        onChange={handleInputChange}
                        error={errors.new_password?.[0]}
                        required
                    />
                    
                    <TextField 
                        id="new_password_confirm"
                        type="password"
                        label="Potvrzení nového hesla"
                        placeholder="Zadejte nové heslo znovu"
                        value={formData.new_password_confirm}
                        onChange={handleInputChange}
                        error={errors.new_password_confirm || errors.non_field_errors?.[0]}
                        required
                    />

                    <Container property="flex justify-end mt-8">
                        <Button onClick={handleSubmit} icon="save">
                            Uložit změny
                        </Button>
                    </Container>
                </Container>
            </ContainerForEntity>
        </Container>
    );
}
