import { useApi } from "@hooks/useApi";
//import { createParams } from "@api/createParams";

export const useCodeListAPI = () => {
    const api = useApi();
    const practices = api.dummyDB.practices;
    const subjects = api.dummyDB.subjects;

    const getUniqueLocations = async () => {
        try {

            const uniqueAddresses = [...new Set(practices.map(practice => practice.address))];
            const locations = uniqueAddresses.map((address, index) => ({
                //id: index + 1,
                label: address,
                value: address
            }));

            return locations;
        } catch (error) {
            console.error("Chyba při získávání unikátních lokací:", error);
            return [];
        }
    };

    const getUniqueSubjects = async () => {
        try {
            const uniqueSubjectIds = [...new Set(practices.map(practice => practice.subject))];
            
            const subjectOptions = uniqueSubjectIds.map(subjectId => {
                const subject = subjects.find(s => s.subject_id === subjectId);
                return {
                    label: subject ? `${subject.subject_code} - ${subject.subject_name}` : `Subject ${subjectId}`,
                    value: subjectId
                };
            });

            return subjectOptions;
        } catch (error) {
            console.error("Chyba při získávání unikátních předmětů:", error);
            return [];
        }
    };

    return {
        getUniqueLocations,
        getUniqueSubjects,
    };
};