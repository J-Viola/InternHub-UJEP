import { useApi } from "@hooks/useApi";

export const useStudentPracticeAPI = () => {
    const api = useApi();

    // POST /api/student-practices/employer-invitation/approve/ - Schválení/zamítnutí pozvánky
    const manageEmployerInvitation = async (invitationId, action) => {
        try {
            const response = await api.post('/student-practices/employer-invitation/approve/', {
                invitation_id: invitationId,
                action: action // 'accept' nebo 'reject'
            });
            return response.data;
        } catch (error) {
            console.error('Chyba při schvalování pozvánky:', error);
            throw error;
        }
    };

 

    return {
        manageEmployerInvitation,
    };
};
