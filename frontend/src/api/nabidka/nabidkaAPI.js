import { useApi } from "@hooks/useApi";
//import { createParams } from "@api/createParams";

export const useNabidkaAPI = () => {
    const api = useApi();
    const practices = api.dummyDB.practices;

    // případně vytvořt zvlášť na id..
    const getNabidky = async (params = {}) => {
        try {
            
            let filteredData = practices;
            
            if (Object.keys(params).length > 0) {
                filteredData = practices.filter(practice => {
                    return Object.entries(params).every(([key, value]) => {
                        if (practice.hasOwnProperty(key)) {

                            if (typeof practice[key] === 'number') {
                                return practice[key] === parseInt(value);
                            }

                            if (typeof value === 'string' && typeof practice[key] === 'string') {
                                return practice[key].toLowerCase().includes(value.toLowerCase());
                            }

                            return practice[key] === value;
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
            console.error("Chyba při získávání nabídek:", error);
            throw error;
        }
    };

    {/** FUNKCE NA GET PRO ID NABIDKY
    const getNabidkaById = async (id) => {
            try {
                const practice = practices.find(practice => practice.practice_id === parseInt(id));
                return practice || null;
            } catch (error) {
                console.error("Chyba při získávání nabídky podle ID:", error);
                throw error;
            }
        }    
        */}

    return {
        getNabidky,
    }
};