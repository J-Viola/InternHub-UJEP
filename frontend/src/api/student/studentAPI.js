import { useApi } from "@hooks/useApi";
//import { createParams } from "@api/createParams";

export const useStudentAPI = () => {
    const api = useApi();
    const students = api.dummyDB.students;


    const getStudents = async (params = {}) => {
        try {
            let filteredData = students;
            
            if (Object.keys(params).length > 0) {
                filteredData = students.filter(student => {
                    return Object.entries(params).every(([key, value]) => {
                        if (student.hasOwnProperty(key)) {

                            if (typeof student[key] === 'number') {
                                return student[key] === parseInt(value);
                            }

                            if (typeof value === 'string' && typeof student[key] === 'string') {
                                return student[key].toLowerCase().includes(value.toLowerCase());
                            }

                            return student[key] === value;
                        }
                        return false;
                    });
                });
            }

            const response = {
                data: filteredData
            };

            return response.data;
        } catch (error) {
            console.error("Chyba při získávání studentů:", error);
            throw error;
        }
    };

    // Funkce pro získání studenta podle ID
    const getStudentById = async (id) => {
        try {
            const student = students.find(student => student.id === parseInt(id));
            return student || null;
        } catch (error) {
            console.error("Chyba při získávání studenta podle ID:", error);
            throw error;
        }
    };

    return {
        getStudents,
        getStudentById,
    }
};