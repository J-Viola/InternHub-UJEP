import { useApi } from "@hooks/useApi";
//import { createParams } from "@api/createParams";

export const useCodeListAPI = () => {
    const api = useApi();

    const getSubjects = async () => {
        try {
            const response = await api.get('/subjects/');
            
            if (response?.data) {
                return response.data;
            }
            return [];
        } catch (error) {
            console.error("Chyba při získávání předmětů:", error);
            return [];
        }
    };

    const getUniqueLocations = async () => {
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
    };

    const getUniqueSubjects = async () => {
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
            return [];
        }
    };

    return {
        getSubjects,
        getUniqueLocations,
        getUniqueSubjects,
    };
};