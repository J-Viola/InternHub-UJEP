export const usePozvankyAPI = () => {
    const getPozvankyList = async () => {
        // Mock data pro demonstraci
        return [
            {
                id: 2,
                recipient_name: "Adam Nový",
                department: "Katedra informatiky",
                project_title: "Návrhu a implementace AI asistentů pro zákaznickou podporu",
                recipient_id: 101
            },
            {
                id: 3,
                recipient_name: "Vladislav Zinek",
                department: "Katedra informatiky", 
                project_title: "Návrhu a implementace AI asistentů pro zákaznickou podporu",
                recipient_id: 102
            }
        ];
    };

    return {
        getPozvankyList
    };
}; 