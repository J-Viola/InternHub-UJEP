import { useState, useCallback } from 'react';
import { useMessage } from './MessageContext';
import { useTranslation } from 'react-i18next';

export const useFormErrorHandling = () => {
    const { addMessage } = useMessage();
    const { t } = useTranslation();
    const [formErrors, setFormErrors] = useState({});

    const handleError = useCallback((error) => {
        setFormErrors({}); // Clear previous errors

        // 1. Normalizovaná chyba z apiClient (má code, responseData)
        if (error.code && error.responseData) {
            const apiErrors = error.responseData;
            // Set field-specific errors (DRF returns {fieldName: [errorMessages]})
            setFormErrors(apiErrors);

            if (apiErrors.detail) {
                addMessage(`${t('common.error_label')}: ${apiErrors.detail}`, "E");
            } else if (typeof apiErrors === 'string') {
                addMessage(`${t('common.error_label')}: ${apiErrors}`, "E");
            } else {
                // Generické hlášení chyby — field errors už jsou nastaveny
                addMessage(`${t('registration.check_form')} ${error.details || ""}`, "E");
            }
        }
        // 2. Raw Axios error (fallback — např. když se nepoužívá apiClient)
        else if (error.response?.data) {
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
        }
        // 3. Normalizovaná chyba bez responseData
        else if (error.details) {
            const details = typeof error.details === 'string'
                ? error.details
                : (error.details.detail || JSON.stringify(error.details));
            addMessage(`${t('common.error_label')}: ${details}`, "E");
        }
        // 4. Úplně neznámá chyba
        else {
            addMessage(`${t('common.unexpected_error')}: ${error.message || ""}`, "E");
        }
    }, [addMessage, t]);

    return { formErrors, handleError, setFormErrors };
};
