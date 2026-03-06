import React, {useState, useEffect} from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import PraxeEntity from "@components/Praxe/PraxeEntity";
import PopUpCon from "@core/Container/PopUpCon";
import Button from "@core/Button/Button";
import { useNabidkaAPI } from "src/api/nabidka/nabidkaAPI";
import { useNavigate } from "react-router-dom";
import { useStudentPracticeAPI } from "src/api/student_practice/student_practiceAPI";
import { useUser } from "@hooks/UserProvider";
import BackButton from "@components/core/Button/BackButton";
import { useTranslation } from "react-i18next";

export default function PraxePage() {
    const { t } = useTranslation();
    const [ selectedEntity, setSelectedEntity ] = useState({});
    const nabidkaAPI  = useNabidkaAPI();
    const studentPraciceAPI = useStudentPracticeAPI();
    const [ data, setData]  = useState(null);
    const [ popUp, setPopUp ] = useState(false);
    const [ loading, setLoading ] = useState(true);
    const [ error, setError ] = useState(null);
    const navigate = useNavigate();
    const { user } = useUser();

    useEffect(() => {
        const initFetch = async () => {
            setLoading(true);
            setError(null);
            try {
                if (user.isOrganizationUser() || user.isAdmin()) {
                    const res = await nabidkaAPI.getOrganizationPractices();
                    setData(res);
                } else if (user.isStudent()) {
                    const res = await nabidkaAPI.getPracticeUserRelations();
                    setData(res);
                }
            } catch {
                setError(t('internships.error'));
            } finally {
                setLoading(false);
            }
        };
        initFetch();
    }, [user]);

    const handlePopUp = () => {
        setPopUp(false);
        setSelectedEntity({});
    };

    const handleClick = (entity, type) => {
        if (type === "employer_invitations") {
            setSelectedEntity({
                ...entity,
                type: "invitation",
                title: entity.practice_title,
                action: "respond_to_invitation"
            });
            setPopUp(true);
        } else if (type === "organization_practices") {
            navigate(`/upravit-nabidku/${entity.practice_id}`);
        }
    };

    const handleView = (entity, type) => {
        if (type === "employer_invitations" || type === "student_practices") {
            navigate(`/nabidka/${entity.practice_id}`);
        }
    };

    const handleInvitation = async (action) => {
        if (action) {
            try {
                await studentPraciceAPI.manageEmployerInvitation(selectedEntity.invitation_id, action);
                handlePopUp();
                // Refresh data to show the new state
                const res = await nabidkaAPI.getPracticeUserRelations();
                setData(res);
            } catch (error) {
                console.error("Chyba při zpracování pozvánky:", error);
            }
        }
    };

    const renderPopUp = () => (
        <PopUpCon
            title={selectedEntity.title}
            onClose={handlePopUp}
            text={t('internships.start_practice_confirm')}
            onSubmit={() => handleInvitation("accept")}
            onReject={() => handleInvitation("reject")}
        />
    );

    const renderLoading = () => (
        <Paragraph property="text-center text-gray-500 py-8">{t('internships.loading')}</Paragraph>
    );

    const renderError = () => (
        <Paragraph property="text-center text-red-500 py-8">{error}</Paragraph>
    );

    return (
        <>
            {user.isOrganizationUser() || user.isAdmin() ? (
                <>
                    <BackButton/>
                    <Container property={"flex items-center justify-between mb-6 mt-4"}>
                        <Headings sizeTag={"h3"} property={"mt-2"}>
                            {t('internships.created_title')}
                        </Headings>
                    </Container>

                    <Container>
                        <Button
                            onClick={() => navigate('/vytvorit-nabidku')}
                            icon={"plus"}
                        >
                            {t('internships.create_new')}
                        </Button>
                    </Container>

                    <Container property={"mt-4 rounded-lg"}>
                        {loading && renderLoading()}
                        {!loading && error && renderError()}
                        {!loading && !error && (!data || data.length === 0) && (
                            <Paragraph property="text-center text-gray-500 py-8">
                                {t('internships.no_created')}
                            </Paragraph>
                        )}
                        {!loading && !error && data && data.length > 0 && (
                            <Container property={"grid grid-cols-1 gap-4"}>
                                {data.map(entity => (
                                    <PraxeEntity
                                        type={"organization_practices"}
                                        key={`practice-${entity.practice_id}`}
                                        entity={entity}
                                        onClick={() => handleClick(entity, "organization_practices")}
                                        onView={() =>
                                            entity.approval_status !== 0
                                                ? navigate(`/students/${entity.practice_id}?view=true`)
                                                : navigate(`/nabidka/${entity.practice_id}`)
                                        }
                                    />
                                ))}
                            </Container>
                        )}
                    </Container>
                </>
            ) : (
                <>
                    <BackButton/>
                    <Container property={"flex flex-col gap-2"}>
                        {loading && renderLoading()}
                        {!loading && error && renderError()}
                        {!loading && !error && data && (
                            <>
                                <Headings sizeTag={"h3"} property={"mt-2 mb-2"}>
                                    {t('internships.submitted_applications')}
                                    {data.student_practices ? ` (${data.student_practices.length})` : ""}
                                </Headings>
                                {data.student_practices?.length === 0 && (
                                    <Paragraph property="text-center text-gray-500 py-4">
                                        {t('internships.no_applications')}
                                    </Paragraph>
                                )}
                                {data.student_practices?.map(entity => (
                                    <PraxeEntity
                                        type={"student_practices"}
                                        key={`practice-${entity.practice_title}-${entity.application_date}`}
                                        entity={entity}
                                        onClick={() => handleClick(entity, "student_practices")}
                                        onView={() => handleView(entity, "student_practices")}
                                    />
                                ))}

                                <Headings sizeTag={"h3"} property={"mt-2 mb-2"}>
                                    {t('internships.company_invitations')}
                                    {data.employer_invitations ? ` (${data.employer_invitations.length})` : ""}
                                </Headings>
                                {data.employer_invitations?.length === 0 && (
                                    <Paragraph property="text-center text-gray-500 py-4">
                                        {t('internships.no_invitations')}
                                    </Paragraph>
                                )}
                                {data.employer_invitations?.map(entity => (
                                    <PraxeEntity
                                        type={"employer_invitations"}
                                        key={`invitation-${entity.practice_title}-${entity.submission_date}`}
                                        entity={{
                                            ...entity,
                                            application_date: entity.submission_date,
                                            status: t('internships.invitation_label')
                                        }}
                                        onClick={() => handleClick(entity, "employer_invitations")}
                                        onView={() => handleView(entity, "employer_invitations")}
                                    />
                                ))}
                            </>
                        )}
                    </Container>
                </>
            )}
            {popUp && renderPopUp()}
        </>
    );
}
