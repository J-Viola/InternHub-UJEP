import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import BackButton from "@core/Button/BackButton";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import { useParams } from "react-router-dom";
import Button from "@core/Button/Button";
import DocsPanel from "@components/Nabidka/DocsPanel";
import PopUpCon from "@core/Container/PopUpCon";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI"
import { useUser } from "@hooks/UserProvider";
import { Image } from "@components/core/Image"
import { useMessage } from "@hooks/MessageContext";
import ProgressPanel from "@components/Nabidka/ProgressBar";
import { useDocumentsAPI } from "@api/documents/documentsAPI";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function NabidkaDetailPage() {
    const { t } = useTranslation();
    const { id } = useParams();
    const [ popUp, setPopUp ] = useState(false);
    const [ entity, setEntity ] = useState(null);
    const nabidkaAPI = useNabidkaAPI();
    const documentAPI = useDocumentsAPI();
    const { user } = useUser();
    const { addMessage } = useMessage();
    const navigate = useNavigate();

    const [docs, setDocs] = useState([]);

    const fetchData = async () => {
        try {
            const result = await nabidkaAPI.getNabidkaById(id);
            setEntity(result);
            setDocs(result.student_practice_documents || []);
        } catch (error) {
            addMessage(t('common.error'), "E");
        }
    };

    useEffect(() => {
        if (id) {
            fetchData();
        }
    }, [id]);

    const handleDownload = async (documentId) => {
        try {
            const blob = await documentAPI.downloadDocument(documentId);
            const url = window.URL.createObjectURL(new Blob([blob]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `dokument_${documentId}.docx`);
            document.body.appendChild(link);
            link.click();
            link.parentNode.removeChild(link);
        } catch (error) {
            addMessage(t('common.error'), "E");
        }
    };

    const handleUpload = async (documentId) => {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.doc,.docx';
        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const formData = new FormData();
            formData.append('document', file);
            try {
                await documentAPI.uploadDocument(documentId, formData);
                addMessage(t('common.save'), "S");
                fetchData();
            } catch (error) {
                addMessage(t('common.error'), "E");
            }
        };
        input.click();
    };

    const handlePopUp = () => {
        setPopUp(!popUp);
    }

    const handleApprove = async () => {
        try {
            await nabidkaAPI.changeStatus(id, { "approval_status": 1 });
            addMessage(t('common.save'), "S");
            setPopUp(false);
            fetchData();
        } catch (error) {
            addMessage(t('common.error'), "E");
        }
    };

    const handleReject = async () => {
        try {
            await nabidkaAPI.changeStatus(id, { "approval_status": 2 });
            addMessage(t('common.save'), "S");
            setPopUp(false);
            fetchData();
        } catch (error) {
            addMessage(t('common.error'), "E");
        }
    };

    const onSubmit = async() => {
        try {
            const res = await nabidkaAPI.applyNabidka({
                "practice" : id
            })
            if (res) {
                addMessage(t('offers.apply'), "S")
                handlePopUp(!popUp)
                navigate(`/praxe`)
            }
        } catch (error) {
            console.error(error);
            const errorCode = error.code || "UNKNOWN_ERROR";
            addMessage(t(`api_errors.${errorCode}`, { defaultValue: t('common.error') }), "E");
        }
    }

    const onReject = () => {
        setPopUp(false);
    }

    const renderContactInfo = () => {
        return (
            <Container property={"editor-content mt-2"}>
                <Container property="flex justify-between items-center mb-4">
                    <Headings sizeTag="h3">{t('offers.contact_person')}</Headings>
                    {entity.student_practice_status && (
                        <Button
                            variant={
                                entity.student_practice_status.workflow_status === "PENDING" ? "yellowSmall" :
                                ["REJECTED", "CANCELLED"].includes(entity.student_practice_status.workflow_status) ? "redSmall" :
                                "greenSmall"
                            }
                            pointer={false}
                            hover={false}
                        >
                            {t('status.label')}: {entity.student_practice_status.workflow_status_label}
                        </Button>
                    )}
                </Container>
                {(entity.contact_user_info.first_name || entity.contact_user_info.last_name) && (
                    <Paragraph property="mb-2">
                        {t('form.contact_user')}: {`${entity.contact_user_info.first_name || ''} ${entity.contact_user_info.last_name || ''}`.trim()}
                    </Paragraph>
                )}
                {entity.contact_user_info.email && (
                    <Paragraph property="mb-2">
                        {t('profile.email')}: {entity.contact_user_info.email}
                    </Paragraph>
                )}
                {entity.contact_user_info.phone && (
                    <Paragraph property="mb-2">
                        {t('profile.phone')}: {entity.contact_user_info.phone}
                    </Paragraph>
                )}
            </Container>
        )
    }

    return(
        <>
            <BackButton/>
            {/* DOCS PANEL */}
            {entity?.student_practice_status?.workflow_status &&
                !["PENDING", "REJECTED"].includes(entity.student_practice_status.workflow_status) && (
                <DocsPanel entity={entity} docData={docs} handleDownload={handleDownload} handleUpload={handleUpload}/>
            )}
            <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
                <Container property="grid grid-cols-[auto,1fr] gap-4 mt-2 mb-4">

                    {/* LOGO */}
                    <Container property="w-32 h-32 rounded-lg p-4 flex items-center justify-center">
                        <Headings sizeTag="h4" property="text-white">
                            <Image
                                src={entity?.image_base64}
                                alt={entity?.title}
                                objectFit="cover"
                            />
                        </Headings>
                    </Container>

                    {/* TITLE */}
                    <Container>
                        <Headings sizeTag={"h4"} property={""}>{entity?.title}</Headings>
                        <Container property={"flex flex-row gap-2 mt-2"}>
                            <Button variant="blueSmallNoHover" pointer={false} property="w-fit">{t('offers.location')}: {entity?.employer?.address || t('common.not_specified')}</Button>
                            <Button variant="blueSmallNoHover" pointer={false} property="w-fit">{entity?.start_date} - {entity?.end_date}</Button>
                        </Container>
                    </Container>

                </Container>
                {/* DESCRIPTION */}
                <Container property={"editor-content mt-2"}>
                    <Headings sizeTag="h3" property="mb-2">{t('offers.responsibilities')}</Headings>
                    <Paragraph>{entity?.description}</Paragraph>
                </Container>

                {/* RESPONSIBILITY */}
                <Container property={"editor-content mt-4"}>
                    <Headings sizeTag="h3" property="mb-2">{t('offers.requirements')}</Headings>
                    <Paragraph>{entity?.responsibilities}</Paragraph>
                </Container>

                {/* RENDER - STUDENTS */}
                {entity && entity.contact_user_info && user.isStudent() && entity.student_practice_status && (
                    renderContactInfo()
                )}

                {/* RENDER - DEPARTMENT */}
                {entity && entity.contact_user_info && user.isProfessor() && (
                    renderContactInfo()
                )}

                <Container property={"flex flex-row  justify-end gap-8 mt-4"}>
                    {/* TLAČÍTKO PRO PODÁNÍ PŘIHLÁŠKY */}
                    {user && user.isStudent() && (!entity?.student_practice_status) && (
                        <Button property="col-start-1 justify-self-end w-full" onClick={handlePopUp}>{t('offers.apply')}</Button>
                    )}


                    {user && user.isProfessor() && entity?.approval_status === 1 && (
                        <>
                            <Button
                                variant={"primary"}
                                icon={"users"}
                                property={"px-8"}
                                onClick={() => navigate(`/students/${entity.practice_id}`)}
                            >
                                {t('offers.view_applicants')}
                            </Button>

                            <Button
                                variant={"primary"}
                                icon={"gear"}
                                property={"px-8"}
                                onClick={handlePopUp}
                            >
                                {t('common.manage')}
                            </Button>
                        </>
                    )}

                    {user && user.isProfessor() && entity?.approval_status === 0 && (
                        <>
                            <Button
                                variant={"primary"}
                                icon={"gear"}
                                property={"px-8"}
                                onClick={handlePopUp}
                            >
                                {t('common.manage')}
                            </Button>

                            <Button
                                variant={"primary"}
                                icon={"edit"}
                                property={"px-8"}
                                onClick={() => navigate(`/formular?type=nabidka_form&action=edit&id=${entity.practice_id}`)}
                            >
                                {t('offers.edit_offer')}
                            </Button>
                        </>
                    )}


                    {user && (user.isOrganizationUser() || user.isAdmin()) && entity?.employer?.employer_id && (
                        <>
                            <Button
                                variant={"primary"}
                                icon={"users"}
                                property={"px-8"}
                                onClick={() => navigate(`/students/${entity.practice_id}?view=true`)}
                            >
                                {t('offers.view_applicants')}
                            </Button>

                            <Button
                                variant={"primary"}
                                icon={"edit"}
                                property={"px-8"}
                                onClick={() => navigate(`/formular?type=nabidka_form&action=edit&id=${entity.practice_id}`)}
                            >
                                {t('offers.edit_offer')}
                            </Button>
                        </>
                    )}

                </Container>
            </ContainerForEntity>

            {entity?.student_practice_status?.workflow_status &&
                !["PENDING", "REJECTED"].includes(entity.student_practice_status.workflow_status) && (
                <Container property={"mt-2"}>
                    <ProgressPanel
                        subject={entity.subject?.subject_code}
                        goalValueSingle={entity.subject?.hours_required}
                        currentValueSingle={entity.student_practice_status?.hours_completed}
                    />
                </Container>
            )}

            {popUp && user.isStudent() && (
                <PopUpCon
                    onClose={handlePopUp}
                    title={t('nav.applications')}
                    text={t('internships.start_practice_confirm')}
                    onSubmit={onSubmit}
                    onReject={onReject}
                />
            )}

            {popUp && user.isProfessor() && (
                <PopUpCon
                    onClose={handlePopUp}
                    title={t('common.manage')}
                    text={t('internships.change_status_text', { title: entity?.title })}
                    onSubmit={handleApprove}
                    onReject={handleReject}
                    submitText={t('common.approve')}
                    rejectText={t('common.reject')}
                />
            )}
        </>
    )
}
