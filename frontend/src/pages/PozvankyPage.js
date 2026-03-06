import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import BackButton from "@core/Button/BackButton";
import Button from "@core/Button/Button";
import { useNabidkaAPI } from "src/api/nabidka/nabidkaAPI";
import { useNavigate, useSearchParams } from "react-router-dom";
import Paragraph from "@components/core/Text/Paragraph";
import { useUser } from "@hooks/UserProvider";
import NabidkaEntityInline from "@components/Nabidka/NabidkaEntityInline";
import PopUpCon from "@core/Container/PopUpCon";
import { useStudentPracticeAPI } from "src/api/student_practice/student_practiceAPI";
import { useMessage } from "@hooks/MessageContext";
import { useTranslation } from "react-i18next";

export default function InvitationPage() {
    const { t } = useTranslation();
    const [searchParams] = useSearchParams();
    const [nabidky, setNabidky] = useState([]);
    const [selectedNabidka, setSelectedNabidka] = useState(null);
    const [showConfirmPopup, setShowConfirmPopup] = useState(false);
    const { getOrganizationPractices } = useNabidkaAPI();
    const { createInvitation } = useStudentPracticeAPI();
    const { user } = useUser();
    const { addMessage } = useMessage();
    const navigate = useNavigate();

    useEffect(() => {
        const type = searchParams.get('type');
        const id = searchParams.get('id');

        if (type === 'create' && id) {
            if (user.isOrganizationUser()) {
                getOrganizationPractices().then(res => {
                    setNabidky(res || []);
                }).catch(error => {
                    console.error(t('offers.loading'), error);
                });
            }
        }
    }, [searchParams, user, getOrganizationPractices, t]);



    const type = searchParams.get('type');
    const id = searchParams.get('id');
    const names = searchParams.get('names');
    const studentIds = id ? id.split(',').map(id => parseInt(id.trim())) : [];
    const studentNames = names ? names.split(',') : [];

    const handleSelectNabidka = (nabidka) => {
        if (selectedNabidka?.practice_id === nabidka.practice_id) {
            setSelectedNabidka(null);
        } else {
            setSelectedNabidka(nabidka);
        }
    };

    const handleViewNabidka = (nabidka) => {
        navigate(`/nabidka/${nabidka.practice_id}`);
    };

    const handleCreateInvitation = () => {
        setShowConfirmPopup(true);
    };

    const handleConfirmCreate = async () => {
        if (!selectedNabidka || studentIds.length === 0) return;

        try {
            const res = await createInvitation(selectedNabidka.practice_id, studentIds);
            if (res) {
                addMessage(t('invitations.create_success', { count: res.created }), "S");
                if (res.errors && res.errors.length > 0) {
                    addMessage(`${t('invitations.errors_label')}: ${res.errors.join(", ")}`, "E");
                }
                setShowConfirmPopup(false);
                navigate('/pozvanky-list');
            }
        } catch (error) {
            console.error(t('invitations.create_error'), error);
            addMessage(`${t('invitations.create_error')}: ${error.response?.data?.detail || error.message}`, "E");
            setShowConfirmPopup(false);
        }
    };

    const handleCancelCreate = () => {
        setShowConfirmPopup(false);
    };

    return(
        <>
            <BackButton/>
            <Container property={"flex items-center justify-between mb-6 mt-4"}>
                <Headings sizeTag={"h3"} property={"mt-2"}>
                    {type === 'create' ? t('invitations.create_title') : t('invitations.single_title')}
                </Headings>
            </Container>
            <Container property={"mb-4"}>
                {type === 'create' && (
                    <Button
                        onClick={handleCreateInvitation}
                        icon={"user-plus"}
                        disabled={!selectedNabidka}
                    >
                        {t('invitations.create_title')}
                    </Button>
                )}
            </Container>

            {type === 'create' && studentIds.length > 0 && (
                <Container property={"bg-facultyColLight mt-2 p-4 rounded-lg border border-black"}>
                    <Paragraph variant="baseBold" property="mb-2">
                        {t('invitations.selected_students')} ({studentIds.length}):
                    </Paragraph>
                    <Container property="space-y-1">
                        {studentNames.length > 0 ? (
                            studentNames.map((name, index) => (
                                <Paragraph key={index} property="text-sm">
                                    • {name}
                                </Paragraph>
                            ))
                        ) : (
                            <Paragraph property="text-sm text-gray-600">
                                {t('students.personal_number')}: {studentIds.join(', ')}
                            </Paragraph>
                        )}
                    </Container>
                </Container>
            )}

            {type === 'create' && studentIds.length > 0 && (
                <Container property={"mt-4 p-6 rounded-lg border border-black"}>
                    <Headings sizeTag={"h4"} property={"mb-4"}>
                        {t('invitations.select_practice')}
                    </Headings>

                    {nabidky.length > 0 ? (
                        <Container property={"space-y-3"}>
                            {nabidky.map((nabidka) => (
                                <NabidkaEntityInline
                                    key={nabidka.practice_id}
                                    entity={nabidka}
                                    isSelected={selectedNabidka?.practice_id === nabidka.practice_id}
                                    onClick={() => handleSelectNabidka(nabidka)}
                                    onView={() => handleViewNabidka(nabidka)}
                                />
                            ))}
                        </Container>
                    ) : (
                        <Container property={"bg-gray-50 p-4 rounded-lg"}>
                            <Paragraph>{t('offers.loading')}</Paragraph>
                        </Container>
                    )}
                </Container>
            )}

            {(!type || !id) && (
                <Container property={"bg-gray-50 mt-2 p-4 rounded-lg"}>
                    <Paragraph>{t('invitations.no_params')}</Paragraph>
                </Container>
            )}

            {showConfirmPopup && (
                <PopUpCon
                    title={t('invitations.confirm_create_title')}
                    text={t('invitations.confirm_create_text', {
                        count: studentNames.length > 0 ? studentNames.length : studentIds.length,
                        title: selectedNabidka?.title
                    })}
                    onSubmit={handleConfirmCreate}
                    onReject={handleCancelCreate}
                    onClose={handleCancelCreate}
                    onSubmitText={t('common.confirm')}
                    onRejectText={t('common.cancel')}
                    variant="blue"
                />
            )}
        </>
    )
}
