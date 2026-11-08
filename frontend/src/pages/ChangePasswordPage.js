import React, { useState } from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Headings from "@core/Text/Headings";
import TextField from "@core/Form/TextField";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import { useUserAPI } from "@api/user/userAPI";
import { useAuth } from "@auth/Auth";
import { useMessage } from "@hooks/MessageContext";
import { useTranslation } from "react-i18next";

export default function ChangePasswordPage() {
    const { t } = useTranslation();
    const { changePassword } = useUserAPI();
    const { logout } = useAuth();
    const { addMessage } = useMessage();

    const [formData, setFormData] = useState({
        old_password: "",
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
            setErrors({ new_password_confirm: t('password_change.mismatch') });
            return;
        }

        try {
            await changePassword(formData);
        } catch (error) {
            console.error("Změna hesla selhala:", error?.response?.status || error?.code || "UNKNOWN_ERROR");
            if (error.details) {
                setErrors(error.details);
            }
            const errorCode = error.code || "UNKNOWN_ERROR";
            addMessage(t(`api_errors.${errorCode}`, { defaultValue: t('password_change.error') }), "E");
            return;
        }

        addMessage(t('password_change.success_relogin'), "S");
        // Backend zneplatnil všechny refresh tokeny i cookie; logout vyčistí lokální stav.
        try {
            await logout();
        } catch {
            // Cookie už je smazaná — logout v finally vyčistí stav a přesměruje na úvod.
        }
    };

    return (
        <Container property="max-w-md mx-auto">
            <ContainerForEntity property="p-8">
                <BackButton />
                <Headings sizeTag="h2" property="mb-6 mt-4 text-center">{t('password_change.title')}</Headings>

                <Container property="space-y-4">
                    <TextField
                        id="old_password"
                        type="password"
                        label={t('password_change.old_password')}
                        placeholder={t('password_change.old_password_placeholder')}
                        value={formData.old_password}
                        onChange={handleInputChange}
                        error={errors.old_password?.[0]}
                        required
                    />

                    <TextField
                        id="new_password"
                        type="password"
                        label={t('password_reset.new_password')}
                        placeholder={t('password_change.new_password_placeholder')}
                        value={formData.new_password}
                        onChange={handleInputChange}
                        error={errors.new_password?.[0]}
                        required
                    />

                    <TextField
                        id="new_password_confirm"
                        type="password"
                        label={t('password_reset.confirm_new_password')}
                        placeholder={t('password_change.confirm_new_placeholder')}
                        value={formData.new_password_confirm}
                        onChange={handleInputChange}
                        error={errors.new_password_confirm || errors.non_field_errors?.[0]}
                        required
                    />

                    <Container property="flex justify-end mt-8">
                        <Button onClick={handleSubmit} icon="save">
                            {t('form.save_changes')}
                        </Button>
                    </Container>
                </Container>
            </ContainerForEntity>
        </Container>
    );
}
