import { useState, useCallback } from 'react';
import { useMessage } from './MessageContext';

export const useFormErrorHandling = () => {
    const { addMessage } = useMessage();
    const [formErrors, setFormErrors] = useState({});

    const handleError = useCallback((error) => {
        setFormErrors({}); // Clear previous errors

        if (error.response?.data) {
            const apiErrors = error.response.data;
            setFormErrors(apiErrors); // Set field-specific errors

            if (apiErrors.detail) {
                addMessage("Chyba: " + apiErrors.detail, "E");
            } else if (typeof apiErrors === 'string') {
                addMessage("Chyba: " + apiErrors, "E");
            } else {
                // Generické hlášení chyby, pokud nejsou specifické detaily
                addMessage("Zkontrolujte prosím formulář. " + (error.message || ""), "E");
            }
        } else {
            addMessage("Došlo k neočekávané chybě: " + (error.message || ""), "E");
        }
    }, [addMessage]);

    return { formErrors, handleError, setFormErrors };
};
