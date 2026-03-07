import React, { useState } from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Headings from "@core/Text/Headings";
import Paragraph from "@core/Text/Paragraph";
import TextField from "@core/Form/TextField";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import { useUserAPI } from "@api/user/userAPI";
import { useMessage } from "@hooks/MessageContext";
import { useTranslation } from "react-i18next";

export default function PasswordResetRequestPage() {
    const { t } = useTranslation();
    const { requestPasswordReset } = useUserAPI();
    const { addMessage } = useMessage();
    const [email, setEmail] = useState("");
    const [loading, setLoading] = useState(false);
    const [submitted, setSubmitted] = useState(false);

    const handleSubmit = async () => {
        if (!email) {
            addMessage(t('password_reset.enter_email'), "E");
            return;
        }

        setLoading(true);
        try {
            await requestPasswordReset(email);
            setSubmitted(true);
            addMessage(t('password_reset.email_sent_success'), "S");
        } catch (error) {
            console.error(error);
            const errorCode = error.code || "UNKNOWN_ERROR";
            addMessage(t(`api_errors.${errorCode}`, { defaultValue: t('password_reset.request_error') }), "E");
        } finally {
            setLoading(true); // Keep loading state until navigation if needed or just false
            setLoading(false);
        }
    };

    return (
        <Container property="flex items-center justify-center">
            <ContainerForEntity property="w-full max-w-md p-8">
                <BackButton />
                <Headings sizeTag="h2" property="mb-4 mt-4 text-center">{t('password_reset.request_title')}</Headings>

                {!submitted ? (
                    <>
                        <Paragraph property="mb-6 text-center text-gray-600">
                            {t('password_reset.request_instruction')}
                        </Paragraph>

                        <TextField
                            id="email"
                            type="email"
                            label={t('login.email')}
                            placeholder={t('profile.email_placeholder')}
                            value={email}
                            onChange={(value) => setEmail(value.email)}
                            required
                        />

                        <Container property="flex justify-center mt-6">
                            <Button
                                onClick={handleSubmit}
                                property="w-full"
                                disabled={loading}
                            >
                                {loading ? t('common.sending') : t('password_reset.send_link')}
                            </Button>
                        </Container>
                    </>
                ) : (
                    <Container property="text-center">
                        <Paragraph property="mb-6 text-green-600 font-medium">
                            {t('password_reset.check_mailbox')}
                        </Paragraph>
                        <Button onClick={() => window.location.href = "/"} variant="secondary">
                            {t('password_reset.back_to_login')}
                        </Button>
                    </Container>
                )}
            </ContainerForEntity>
        </Container>
    );
}
