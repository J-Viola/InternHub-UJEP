import { useState, useCallback } from 'react';
import { useMessage } from './MessageContext';
import { useTranslation } from 'react-i18next';

export const useFormErrorHandling = () => {
    const { addMessage } = useMessage();
    const { t } = useTranslation();
    const [formErrors, setFormErrors] = useState({});

    const handleError = useCallback((error) => {
        setFormErrors({}); // Clear previous errors

        if (error.response?.data) {
            const apiErrors = error.response.data;
            setFormErrors(apiErrors); // Set field-specific errors

            if (apiErrors.detail) {
                addMessage(`${t('common.error_label')}: ${apiErrors.detail}`, "E");
            } else if (typeof apiErrors === 'string') {
                addMessage(`${t('common.error_label')}: ${apiErrors}`, "E");
            } else {
                // Generické hlášení chyby, pokud nejsou specifické detaily
                addMessage(`${t('registration.check_form')} ${error.message || ""}`, "E");
            }
        } else {
            addMessage(`${t('common.unexpected_error')}: ${error.message || ""}`, "E");
        }
    }, [addMessage, t]);

    return { formErrors, handleError, setFormErrors };
};
