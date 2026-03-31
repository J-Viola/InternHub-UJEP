import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import Button from "@core/Button/Button";
import { Image } from "@components/core/Image";
import { useNabidkaAPI } from "src/api/nabidka/nabidkaAPI";
import { useStudentPracticeAPI } from "src/api/student_practice/student_practiceAPI";
import { useNavigate } from "react-router-dom";
import { useUser } from "@hooks/UserProvider";
import BackButton from "@components/core/Button/BackButton";
import { useTranslation } from "react-i18next";
import EmptyState from "@core/Feedback/EmptyState";
import { useMessage } from "@hooks/MessageContext";
import ContainerForEntity from "@core/Container/ContainerForEntity";

function ApplicationCard({ entity }) {
    const navigate = useNavigate();
    const { t } = useTranslation();

    const handleVariant = (status) => {
        switch (status) {
            case 0: return "yellow";
            case 1: return "green";
            case 2: return "red";
            case 3: return "gray";
            default: return "gray";
        }
    };

    const statusToText = (status) => {
        switch (status) {
            case 0: return t('status.PENDING');
            case 1: return t('status.APPROVED');
            case 2: return t('status.REJECTED');
            case 3: return t('status.CANCELLED');
            default: return t('common.not_specified');
        }
    };

    return (
        <ContainerForEntity
            variant={"white"}
            property="p-4 border border-black rounded-[10px] shadow-sm hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => navigate(`/nabidka/${entity.practice_id}`)}
        >
            <Container property="flex items-center gap-4">
                <Container property="w-12 h-12 shrink-0">
                    <Image
                        src={entity.company_logo}
                        alt={entity.practice_title}
                        className="w-full h-full"
                        objectFit="contain"
                    />
                </Container>
                <Container property="flex-1 min-w-0">
                    <Headings sizeTag="h5-bold" property="truncate text-black">
                        {entity.practice_title}
                    </Headings>
                    <Paragraph property="text-sm text-gray-500 mt-1">
                        {t('internships.applied_on')}: {entity.application_date}
                    </Paragraph>
                </Container>
                <Container property="shrink-0">
                    <Button
                        variant={handleVariant(entity.status)}
                        pointer={false}
                        hover={false}
                        property="px-4 py-1 text-xs"
                    >
                        {statusToText(entity.status)}
                    </Button>
                </Container>
            </Container>
        </ContainerForEntity>
    );
}

function InvitationCard({ entity, onResponse }) {
    const { t } = useTranslation();
    const navigate = useNavigate();
    const { manageEmployerInvitation } = useStudentPracticeAPI();
    const { addMessage } = useMessage();
    const [loading, setLoading] = useState(false);

    const handleResponse = async (action, e) => {
        e.stopPropagation();
        setLoading(true);
        try {
            await manageEmployerInvitation(entity.invitation_id, action);
            addMessage(action === "ACCEPT" ? t('internships.invitation_accepted') : t('internships.invitation_rejected'), "S");
            if (onResponse) onResponse();
        } catch (error) {
            addMessage(t('internships.invitation_error'), "E");
        } finally {
            setLoading(false);
        }
    };

    return (
        <ContainerForEntity
            variant={"yellow"}
            property="p-4 border border-black rounded-[10px] shadow-sm hover:shadow-md transition-shadow cursor-pointer"
            onClick={() => entity.practice_id && navigate(`/nabidka/${entity.practice_id}`)}
        >
            <Container property="flex items-center gap-4">
                <Container property="w-12 h-12 shrink-0">
                    <Image
                        src={entity.company_logo}
                        alt={entity.practice_title}
                        className="w-full h-full"
                        objectFit="contain"
                    />
                </Container>
                <Container property="flex-1 min-w-0">
                    <Headings sizeTag="h5-bold" property="truncate text-black">
                        {entity.practice_title || t('internships.unknown_practice')}
                    </Headings>
                    <Paragraph property="text-sm text-gray-500 mt-1">
                        {t('internships.received')}: {entity.submission_date}
                    </Paragraph>
                </Container>
                <Container property="shrink-0 flex gap-2">
                    <Button
                        variant="greenSmall"
                        onClick={(e) => handleResponse("ACCEPT", e)}
                        property={loading ? "opacity-50" : ""}
                    >
                        {t('internships.accept')}
                    </Button>
                    <Button
                        variant="redSmall"
                        onClick={(e) => handleResponse("REJECT", e)}
                        property={loading ? "opacity-50" : ""}
                    >
                        {t('internships.decline')}
                    </Button>
                </Container>
            </Container>
        </ContainerForEntity>
    );
}

export default function PraxePage() {
    const { t } = useTranslation();
    const { addMessage } = useMessage();
    const nabidkaAPI = useNabidkaAPI();
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const navigate = useNavigate();
    const { user } = useUser();

    const fetchData = async () => {
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

    useEffect(() => {
        fetchData();
    }, [user]);

    const renderLoading = () => (
        <Paragraph property="text-center text-gray-500 py-8">{t('internships.loading')}</Paragraph>
    );

    const renderError = () => (
        <Paragraph property="text-center text-red-500 py-8">{error}</Paragraph>
    );

    if (user.isOrganizationUser() || user.isAdmin()) {
        return (
            <>
                <BackButton />
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
                        <EmptyState
                            title={t('internships.no_created')}
                            description={t('internships.no_created_desc', { defaultValue: "" })}
                            icon="folder-open"
                            actionText={t('internships.create_new')}
                            onAction={() => navigate('/vytvorit-nabidku')}
                        />
                    )}
                    {!loading && !error && data && data.length > 0 && (
                        <Container property={"grid grid-cols-1 gap-4"}>
                            {data.map(entity => (
                                <ContainerForEntity
                                    key={`practice-${entity.practice_id}`}
                                    property="pl-8 pt-4 pb-4 pr-4 border border-black rounded-[10px]"
                                >
                                    <Container property={"flex items-center justify-between"}>
                                        <Container property={"flex items-center gap-6 flex-1"}>
                                            <Container property={"min-w-[200px]"}>
                                                <Paragraph property={"text-sm text-gray-500 mb-1"}>
                                                    {t('offers.contact_person')}
                                                </Paragraph>
                                                <Paragraph property={"font-medium"}>
                                                    {entity.contact_user_full_name || t('common.not_specified')}
                                                </Paragraph>
                                            </Container>
                                            <Container property={"flex-1"}>
                                                <Paragraph property={"text-sm text-gray-500 mb-1"}>
                                                    {t('form.title')}
                                                </Paragraph>
                                                <Paragraph property={"font-medium"}>
                                                    {entity.title}
                                                </Paragraph>
                                            </Container>
                                            <Container property={"min-w-[150px]"}>
                                                <Paragraph property={"text-sm text-gray-500 mb-1"}>
                                                    {t('internships.submitted_applications')}
                                                </Paragraph>
                                                <Paragraph property={"font-medium"}>
                                                    {entity.approved_applications}/{entity.pending_applications}/{entity.available_positions || 0}
                                                </Paragraph>
                                            </Container>
                                        </Container>
                                        <Container property={"flex items-center gap-4 ml-4"}>
                                            {entity.approval_status !== 0 ? (
                                                <>
                                                    <Button
                                                        noVariant={true}
                                                        onClick={() => navigate(`/students/${entity.practice_id}?view=true`)}
                                                        title={t('internships.view_applications')}
                                                        icon={"users"}
                                                        iconColor={"gray"}
                                                        iconSize={"24"}
                                                    />
                                                    <Button
                                                        noVariant={true}
                                                        onClick={() => navigate(`/upravit-nabidku/${entity.practice_id}`)}
                                                        title={t('internships.edit_internship')}
                                                        icon={"edit"}
                                                        iconColor={"gray"}
                                                        iconSize={"24"}
                                                    />
                                                </>
                                            ) : (
                                                <>
                                                    <Button
                                                        noVariant={true}
                                                        onClick={() => navigate(`/nabidka/${entity.practice_id}`)}
                                                        title={t('internships.view_detail')}
                                                        icon={"eye"}
                                                        iconColor={"gray"}
                                                        iconSize={"24"}
                                                    />
                                                    <Button
                                                        noVariant={true}
                                                        onClick={() => navigate(`/upravit-nabidku/${entity.practice_id}`)}
                                                        title={t('internships.edit_internship')}
                                                        icon={"edit"}
                                                        iconColor={"gray"}
                                                        iconSize={"24"}
                                                    />
                                                </>
                                            )}
                                        </Container>
                                    </Container>
                                </ContainerForEntity>
                            ))}
                        </Container>
                    )}
                </Container>
            </>
        );
    }

    return (
        <>
            <BackButton />
            <Container property={"flex flex-col gap-2"}>
                {loading && renderLoading()}
                {!loading && error && renderError()}
                {!loading && !error && data && (
                    <>
                        <Headings sizeTag={"h3"} property={"mt-2 mb-4"}>
                            {t('internships.company_invitations')}
                            {data.employer_invitations ? ` (${data.employer_invitations.length})` : ""}
                        </Headings>
                        {data.employer_invitations?.length === 0 ? (
                            <EmptyState
                                title={t('internships.no_invitations')}
                                description={t('internships.no_invitations_desc', { defaultValue: "" })}
                                icon="envelope-open"
                                property="mb-8"
                            />
                        ) : (
                            <Container property={"grid grid-cols-1 gap-4 mb-8"}>
                                {data.employer_invitations?.map(entity => (
                                    <InvitationCard
                                        key={`invitation-${entity.invitation_id}`}
                                        entity={entity}
                                        onResponse={fetchData}
                                    />
                                ))}
                            </Container>
                        )}

                        <Headings sizeTag={"h3"} property={"mt-2 mb-4"}>
                            {t('internships.submitted_applications')}
                            {data.student_practices ? ` (${data.student_practices.length})` : ""}
                        </Headings>
                        {data.student_practices?.length === 0 ? (
                            <EmptyState
                                title={t('internships.no_applications')}
                                description={t('internships.no_applications_desc', { defaultValue: "" })}
                                icon="file-signature"
                                actionText={t('offers.title')}
                                onAction={() => navigate('/nabidka')}
                            />
                        ) : (
                            <Container property={"grid grid-cols-1 gap-4"}>
                                {data.student_practices?.map(entity => (
                                    <ApplicationCard
                                        key={`app-${entity.practice_id}-${entity.application_date}`}
                                        entity={entity}
                                    />
                                ))}
                            </Container>
                        )}
                    </>
                )}
            </Container>
        </>
    );
}
