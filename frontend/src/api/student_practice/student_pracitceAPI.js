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

    // PATCH /api/student-practices/<id>/status/ - Změna stavu přihlášky
    // action: "approve" | "reject"
    const updateStudentPracticeStatus = async (studentPracticeId, action) => {
        let approval_status = null;
        if (action === "approve") approval_status = 1; // APPROVED
        if (action === "reject") approval_status = 2; // REJECTED
        if (approval_status === null) throw new Error("Neplatná akce");
        try {
            const response = await api.patch(`/student-practices/student-practices/${studentPracticeId}/status/`, {
                approval_status
            });
            return response.data;
        } catch (error) {
            console.error('Chyba při změně stavu přihlášky:', error);
            throw error;
        }
    };

    // GET /api/student-practices/organization-applications/ - Získání všech přihlášek na nabídky organizace
    const getOrganizationApplications = async () => {
        try {
            const response = await api.get('/student-practices/organization-applications/');
            return response.data;
        } catch (error) {
            console.error('Chyba při získávání přihlášek organizace:', error);
            throw error;
        }
    };

    // GET /api/student-practices/<practice_id> - Získání všech studentů přihlášených na konkrétní praxi
    const getStudentsByPracticeId = async (practiceId) => {
        try {
            const response = await api.get(`/student-practices/student-practices/by-practice/${practiceId}`);
            return response.data;
        } catch (error) {
            console.error('Chyba při získávání studentů pro praxi:', error);
            throw error;
        }
    };

    const getStudentPracticeCard = async (student_practiceId) => {
        try {
            const response = await api.get(`/student-practices/student-practices/${student_practiceId}`);
            return response.data;
        } catch (error) {
            console.error('Chyba při získávání studentů pro praxi:', error);
            throw error;
        }
    };

    return {
        manageEmployerInvitation,
        getOrganizationApplications,
        updateStudentPracticeStatus,
        getStudentsByPracticeId,
        getStudentPracticeCard
    };
};
