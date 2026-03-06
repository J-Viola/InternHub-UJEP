import { useApi } from "@hooks/useApi";

export const usePozvankyAPI = () => {
    const api = useApi();

    const getPozvankyList = async () => {
        try {
            const response = await api.get('/student-practices/invitations/');
            return response.data;
        } catch (error) {
            console.error("Chyba při získávání pozvánek:", error);
            throw error;
        }
    };

    const getPozvankyAdminList = async () => {
        try {
            const response = await api.get('/student-practices/invitations/');
            return response.data;
        } catch (error) {
            console.error("Chyba při získávání pozvánek (admin):", error);
            throw error;
        }
    };

    const deleteInvitation = async (id) => {
        try {
            await api.delete(`/student-practices/invitations/${id}/`);
            return true;
        } catch (error) {
            console.error("Chyba při mazání pozvánky:", error);
            throw error;
        }
    };

    return {
        getPozvankyList,
        getPozvankyAdminList,
        deleteInvitation
    };
};
