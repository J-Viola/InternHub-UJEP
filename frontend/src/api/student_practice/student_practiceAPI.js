import { useMemo } from "react";
import { useApi } from "@hooks/useApi";

export const useStudentPracticeAPI = () => {
    const api = useApi();

    // POST /api/student-practices/employer-invitation/create/ - Vytvoření pozvánky
    const createInvitation = async (practiceId, studentIds) => {
        try {
            const response = await api.post('/student-practices/employer-invitation/create/', {
                practice_id: practiceId,
                student_ids: studentIds
            });
            return response.data;
        } catch (error) {
            console.error('Chyba při vytváření pozvánky:', error);
            throw error;
        }
    };

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

    // FE-002: dřívější PATCH /student-practices/{id}/status/ neexistuje
    // (404) a reject mapoval vše na CONTENT_REJECTED. Nově se každá akce
    // překládá na explicitní state-machine transition (target + reason)
    // podle aktuální fáze — viz audit FE-002 / BL-04.
    const APPROVE_TARGETS = {
        APPLIED: 1, // PRELIMINARY_APPROVED — katedra schválí studenta
        PRELIMINARY_APPROVED: 7, // AWAITING_CONTRACT — organizace souhlasí
        AWAITING_CONTENT_APPROVAL: 12, // CONTENT_APPROVED — externí praxe
    };
    const REJECT_TARGETS = {
        APPLIED: 2, // REJECTED
        PRELIMINARY_APPROVED: 2,
        AWAITING_CONTRACT: 2,
        DOCUMENTS_REJECTED: 2,
        DOCUMENTS_RESUBMITTED: 2,
        CONTRACTED: 2,
        ENDED: 2,
        AWAITING_CONTENT_APPROVAL: 11, // CONTENT_REJECTED — externí obsah
        CONTENT_REJECTED: 2,
        CONTENT_APPROVED: 2,
    };
    const WORKFLOW_STATES = new Set([
        "APPLIED", "PRELIMINARY_APPROVED", "REJECTED", "CONTRACTED", "STARTED", "ENDED",
        "COMPLETED", "AWAITING_CONTRACT", "AWAITING_DOCUMENTS", "DOCUMENTS_REJECTED",
        "AWAITING_CONTENT_APPROVAL", "CONTENT_REJECTED", "CONTENT_APPROVED", "DOCUMENTS_RESUBMITTED",
    ]);

    // action: "approve" | "reject" | "resubmit"
    // options: { reason?: string, workflowStatus?: string }
    //   workflowStatus = aktuální workflow_status přihlášky (fáze), z něhož
    //   se vybere explicitní cílový stav; bez něj platí výchozí mapa pro
    //   běžnou (standardní) větev schvalování.
    const updateStudentPracticeStatus = async (studentPracticeId, action, options = {}) => {
        const { reason = "", workflowStatus } = options;

        if (action === "approve") {
            if (!workflowStatus || !WORKFLOW_STATES.has(workflowStatus)) {
                throw new Error("Unknown or missing student practice workflow status");
            }
            const target = APPROVE_TARGETS[workflowStatus];
            if (!target) throw new Error("Approval is not allowed from this workflow status");
            return transitionStudentPractice(studentPracticeId, target, reason);
        }
        if (action === "reject") {
            if (!workflowStatus || !WORKFLOW_STATES.has(workflowStatus)) {
                throw new Error("Unknown or missing student practice workflow status");
            }
            const target = REJECT_TARGETS[workflowStatus];
            if (!target) throw new Error("Rejection is not allowed from this workflow status");
            return transitionStudentPractice(studentPracticeId, target, reason);
        }
        if (action === "resubmit") {
            if (workflowStatus !== "CONTENT_REJECTED") {
                throw new Error("Resubmit is only allowed from CONTENT_REJECTED");
            }
            return transitionStudentPractice(studentPracticeId, 10, reason); // AWAITING_CONTENT_APPROVAL
        }
        throw new Error("Invalid action");
    };

    // POST /api/student-practices/<id>/transition/ - State machine přechod
    const transitionStudentPractice = async (studentPracticeId, targetState, reason = "") => {
        try {
            const response = await api.post(`/student-practices/${studentPracticeId}/transition/`, {
                target_state: targetState,
                reason
            });
            return response.data;
        } catch (error) {
            console.error('Chyba při přechodu stavu přihlášky:', error);
            throw error;
        }
    };

    // POST /api/student-practices/<id>/withdraw/ - Stažení žádosti studentem
    const withdrawApplication = async (studentPracticeId) => {
        try {
            const response = await api.post(`/student-practices/${studentPracticeId}/withdraw/`);
            return response.data;
        } catch (error) {
            console.error('Chyba při stahování žádosti:', error);
            throw error;
        }
    };

    // POST /api/student-practices/<id>/confirm-contract/ - Potvrzení přijetí smlouvy
    const confirmContract = async (studentPracticeId) => {
        try {
            const response = await api.post(`/student-practices/${studentPracticeId}/confirm-contract/`);
            return response.data;
        } catch (error) {
            console.error('Chyba při potvrzování smlouvy:', error);
            throw error;
        }
    };

    // GET /api/student-practices/professor-applications/ - Získání přihlášek pro profesora
    const getProfessorApplications = async () => {
        try {
            const response = await api.get('/student-practices/professor-applications/');
            if (response && response.data) {
                return response.data.results !== undefined ? response.data.results : response.data;
            }
            return [];
        } catch (error) {
            console.error('Chyba při získávání přihlášek pro profesora:', error);
            throw error;
        }
    };

    // GET /api/student-practices/organization-applications/ - Získání všech přihlášek na nabídky organizace
    const getOrganizationApplications = async () => {
        try {
            const response = await api.get('/student-practices/organization-applications/');
            if (response && response.data) {
                return response.data.results !== undefined ? response.data.results : response.data;
            }
            return [];
        } catch (error) {
            console.error('Chyba při získávání přihlášek organizace:', error);
            throw error;
        }
    };

    // GET /api/student-practices/admin-view/pending-practices/ - Získání všech pending přihlášek z pohledu admina
    const getAdminPendingApplications = async () => {
        try {
            const response = await api.get('/student-practices/admin-view/pending-practices/');
            if (response && response.data) {
                return response.data.results !== undefined ? response.data.results : response.data;
            }
            return [];
        } catch (error) {
            console.error('Chyba při získávání pending přihlášek z pohledu admina:', error);
            throw error;
        }
    };

    // GET /api/student-practices/<practice_id> - Získání všech studentů přihlášených na konkrétní praxi
    const getStudentsByPracticeId = async (practiceId) => {
        try {
            const response = await api.get(`/student-practices/by-practice/${practiceId}`);
            if (response && response.data) {
                return response.data.results !== undefined ? response.data.results : response.data;
            }
            return [];
        } catch (error) {
            console.error('Chyba při získávání studentů pro praxi:', error);
            throw error;
        }
    };

    const getStudentPracticeCard = async (student_practiceId) => {
        try {
            const response = await api.get(`/student-practices/${student_practiceId}`);
            const data = response.data;
            const status = data?.student_practice_status?.workflow_status;
            if (!status || !WORKFLOW_STATES.has(status)) {
                return {
                    ...data,
                    student_practice_status: {
                        ...data?.student_practice_status,
                        workflow_status: "UNKNOWN",
                    },
                };
            }
            return data;
        } catch (error) {
            console.error('Chyba při získávání studentů pro praxi:', error);
            throw error;
        }
    };

    // POST /api/student-practices/<id>/cancel/ — C02-A: student podává
    // ŽÁDOST o storno (stav se nemění), rozhodne garant/admin přes
    // resolve-cancellation. Non-student aktéři dělají legacy okamžité storno.
    const requestCancellation = async (studentPracticeId, reason) => {
        try {
            const response = await api.post(`/student-practices/${studentPracticeId}/cancel/`, {
                reason,
            });
            return response.data;
        } catch (error) {
            console.error('Chyba při podávání žádosti o storno:', error);
            throw error;
        }
    };

    // POST /api/student-practices/<id>/resolve-cancellation/ — T2d:
    // decision: "approve" (nevratné storno) | "reject" (žádost zamítnuta,
    // praxe zůstává aktivní). Povinné pro pending žádost o storno.
    const resolveCancellation = async (studentPracticeId, decision, reason = "") => {
        try {
            const response = await api.post(
                `/student-practices/${studentPracticeId}/resolve-cancellation/`,
                { decision, reason }
            );
            return response.data;
        } catch (error) {
            console.error('Chyba při vyřizování žádosti o storno:', error);
            throw error;
        }
    };

    // POST /api/student-practices/reapply/<practiceId>/
    const reapplyToPractice = async (practiceId) => {
        try {
            const response = await api.post(`/student-practices/reapply/${practiceId}/`);
            if (response && response.data) {
                return response.data;
            }
            return null;
        } catch (error) {
            console.error("Error reapplying to practice:", error);
            throw error;
        }
    };

    // Document generation (stahování vygenerovaných .docx šablon)
    const downloadGeneratedDocument = async (studentPracticeId, docType) => {
        try {
            const res = await api.get(
                `/student-practices/${studentPracticeId}/${docType}/`,
                { responseType: "blob" }
            );
            return res.data;
        } catch (error) {
            console.error(`Chyba při generování dokumentu (${docType}):`, error);
            throw error;
        }
    };

    // FE-014: stabilní identita návratového objektu — bez useMemo vzniká
    // nový objekt při každém renderu a effecty závislé na API hooku
    // (EvaluationForm aj.) znovu fetchují (render-triggered reload).
    return useMemo(
        () => ({
            manageEmployerInvitation,
            getOrganizationApplications,
            getProfessorApplications,
            updateStudentPracticeStatus,
            transitionStudentPractice,
            getStudentsByPracticeId,
            getStudentPracticeCard,
            getAdminPendingApplications,
            createInvitation,
            downloadGeneratedDocument,
            reapplyToPractice,
            confirmContract,
            withdrawApplication,
            requestCancellation,
            resolveCancellation,
        }),
        // Funkce se přetváří jen při změně api clienta (Auth provider).
        // eslint-disable-next-line react-hooks/exhaustive-deps
        [api]
    );
};
