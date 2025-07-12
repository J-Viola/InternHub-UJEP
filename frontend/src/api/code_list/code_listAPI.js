import { useApi } from "@hooks/useApi";
//import { createParams } from "@api/createParams";

export const useCodeListAPI = () => {
    const api = useApi();

    const getSubjects = async () => {
        try {
            const response = await api.get('/subjects/subjects/');
            
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
            // Prozatím vracíme prázdné pole, dokud nemáme endpoint pro lokace
            // TODO: Implementovat API endpoint pro lokace
            return [];
        } catch (error) {
            console.error("Chyba při získávání unikátních lokací:", error);
            return [];
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