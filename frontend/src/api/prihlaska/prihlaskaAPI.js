import { useApi } from "@hooks/useApi";
//import { createParams } from "@api/createParams";

export const usePrihlaskaAPI = () => {
    const api = useApi();

    const student = api.dummyDB.students
    const studentPractices = api.dummyDB.studentPractices;
    const practices = api.dummyDB.practices;
    const employerInvitations = api.dummyDB.employerInvitations;

    const createPrihlaska = async (studentId, practiceId) => {
        try {
            const myStudent = student.find(stud => stud.id === parseInt(studentId));
            const myPractice = practices.find(practice => practice.practice_id === parseInt(practiceId));

            if (myStudent && myPractice) {

                const existingPrihlaska = studentPractices.find(
                    sp => sp.user === parseInt(studentId) && sp.practice === parseInt(practiceId)
                );

                if (existingPrihlaska) {
                    throw new Error("Student už má přihlášku na tuto praxi");
                }

                const newStudentPractice = {
                    student_practice_id: studentPractices.length + 1,
                    user: parseInt(studentId),
                    practice: parseInt(practiceId),
                    application_date: new Date().toISOString().split('T')[0],
                    approval_status: 1, 
                    progress_status: 1,
                    hours_completed: 0,
                    cancellation_reason: null,
                    cancelled_by_user: null
                };

                studentPractices.push(newStudentPractice);

                return {
                    success: true,
                    message: "Přihláška byla úspěšně vytvořena",
                    data: newStudentPractice
                };
            } else {
                throw new Error("Student nebo praxe nebyla nalezena");
            }
            
        } catch (error) {
            console.error("Chyba při tvorbě přihlášky:", error);
            throw error;
        }
    };

    const getStudentPractices = async (studentId) => {
        try {
            const myStudent = student.find(stud => stud.id === parseInt(studentId));
            
            if (!myStudent) {
                throw new Error("Student nebyl nalezen");
            }

            const studentApplications = studentPractices.filter(
                sp => sp.user === parseInt(studentId)
            );

            const studentInvitations = employerInvitations.filter(
                inv => inv.user === parseInt(studentId)
            );

            const practicesWithDetails = [];

            studentApplications.forEach(application => {
                const practice = practices.find(p => p.practice_id === application.practice);
                if (practice) {
                    let status = "Čeká na schválení";
                    if (application.approval_status === 2) {
                        status = "Schváleno";
                    } else if (application.approval_status === 3) {
                        status = "Zamítnuto";
                    } else if (application.progress_status === 2) {
                        status = "Probíhající stáž";
                    } else if (application.progress_status === 3) {
                        status = "Ukončená stáž";
                    }

                    practicesWithDetails.push({
                        id: practice.practice_id,
                        title: practice.title,
                        logo: practice.image_base64 || "LOGO",
                        administration_date: application.application_date,
                        status: status,
                        application_type: "student_application",
                        application_data: application,
                        invitation_data: null
                    });
                }
            });

            studentInvitations.forEach(invitation => {
                const existingPractice = practicesWithDetails.find(
                    p => p.id === invitation.practice
                );
                
                if (!existingPractice) {
                    const practice = practices.find(p => p.practice_id === invitation.practice);
                    if (practice) {
                        practicesWithDetails.push({
                            id: practice.practice_id,
                            title: practice.title,
                            logo: practice.image_base64 || "LOGO",
                            administration_date: invitation.submission_date,
                            status: "Pozvánka",
                            application_type: "employer_invitation",
                            application_data: null,
                            invitation_data: invitation
                        });
                    }
                } else {
                    existingPractice.invitation_data = invitation;
                }
            });

            return {
                success: true,
                data: practicesWithDetails,
                summary: {
                    total_practices: practicesWithDetails.length,
                    applications: studentApplications.length,
                    invitations: studentInvitations.length
                }
            };

        } catch (error) {
            console.error("Chyba při získávání praxí studenta:", error);
            throw error;
        }
    };

    return {
        createPrihlaska,
        getStudentPractices
    };
};