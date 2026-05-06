import React from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Paragraph from "@core/Text/Paragraph";
import Button from "@core/Button/Button";
import { useTranslation } from "react-i18next";

const ErrorState = ({ title, description, onRetry, property = "" }) => {
    const { t } = useTranslation();

    return (
        <Container property={`flex flex-col items-center justify-center py-16 px-4 text-center ${property}`}>
            <Container property="bg-red-50 p-6 rounded-full mb-6">
                <Button icon="triangle-exclamation" noVariant={true} iconSize="48" pointer={false} hover={false} iconColor="text-red-400" />
            </Container>

            <Headings sizeTag="h4" property="text-gray-900 font-bold mb-2">
                {title || t('common.error')}
            </Headings>

            <Paragraph property="text-gray-500 max-w-md mb-6">
                {description || t('common.unexpected_error')}
            </Paragraph>

            {onRetry && (
                <Button variant="primary" onClick={onRetry} property="px-8" icon="refresh">
                    {t('common.retry')}
                </Button>
            )}
        </Container>
    );
};

export default ErrorState;
