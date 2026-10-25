import { useMemo, useCallback } from "react";
import { useApi } from "@hooks/useApi";
//import { createParams } from "@api/createParams";

export const useCodeListAPI = () => {
    const api = useApi();

    const getSubjects = useCallback(async () => {
        try {
            const response = await api.get('/subjects/');

            if (response?.data) {
                if (response.data.results !== undefined) {
                    return response.data.results;
                }
                return response.data;
            }
            return [];
        } catch (error) {
            console.error("Chyba při získávání předmětů:", error);
            throw error;
        }
    }, [api]);

    const getUniqueLocations = useCallback(async () => {
        try {
            const response = await api.get('/code-lists/locations/');
            if (response?.data) {
                return response.data;
            }
            return [];
        } catch (error) {
            console.error("Chyba při získávání unikátních lokací:", error);
            throw error;
        }
    }, [api]);

    const getUniqueSubjects = useCallback(async () => {
        try {
            const subjects = await getSubjects();

            // Transformujeme data do formátu pro dropdown
            const subjectOptions = subjects.map(subject => ({
                label: `${subject.subject_code} - ${subject.subject_name}`,
                value: subject.subject_id
            }));

            return subjectOptions;
        } catch (error) {
            console.error("Chyba při získávání unikátních předmětů:", error);
            throw error;
        }
    }, [api]);

    return useMemo(() => ({
        getSubjects,
        getUniqueLocations,
        getUniqueSubjects,
    }), [getSubjects, getUniqueLocations, getUniqueSubjects]);
};
