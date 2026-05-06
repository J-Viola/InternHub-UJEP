import React from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Paragraph from "@core/Text/Paragraph";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function ForbiddenPage() {
    const { t } = useTranslation();
    const navigate = useNavigate();

    return (
        <Container property="min-h-[60vh] flex items-center justify-center bg-gray-50 px-4">
            <Container property="max-w-md mx-auto text-center">
                <BackButton />
                <Container property="mt-8 mb-6">
                    <Headings sizeTag="h1" property="text-red-300 text-8xl">403</Headings>
                </Container>
                <Headings sizeTag="h3" property="text-gray-700 mb-4">
                    {t('errors.forbidden')}
                </Headings>
                <Paragraph property="text-gray-500 mb-8">
                    {t('errors.forbidden_desc')}
                </Paragraph>
                <Button onClick={() => navigate('/')} variant="primary" property="px-8">
                    {t('common.back')}
                </Button>
            </Container>
        </Container>
    );
}
