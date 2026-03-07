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
import { useDocumentsAPI } from "src/api/documents/documentsAPI";
import { useStudentPracticeAPI } from "src/api/student_practice/student_practiceAPI";
import { useTranslation } from "react-i18next";


export default function PraxeDetailPage() {
    const { t } = useTranslation();
    const { id } = useParams();
    const [ popUp, setPopUp ] = useState(false);
    const [ docsPopUp, setDocsPopUp ] = useState(false);
    const [ entity, setEntity ] = useState(null);
    const nabidkaAPI = useNabidkaAPI();
    const studentpraticeAPI = useStudentPracticeAPI();
    const documentAPI = useDocumentsAPI();
    const { user } = useUser();
    const { addMessage } = useMessage();

    const [docs, setDocs] = useState([]);

    const fetchData = async () => {
        try {
            const result = await studentpraticeAPI.getStudentPracticeCard(id);
            setEntity(result);
            setDocs(result.student_practice_documents || []);
        } catch (error) {
            addMessage(t('practice_detail.card_load_error'), "E");
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
            addMessage(t('practice_detail.download_error'), "E");
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
                addMessage(t('practice_detail.upload_success'), "S");
                fetchData();
            } catch (error) {
                addMessage(t('practice_detail.upload_error'), "E");
            }
        };
        input.click();
    };

    const handlePopUp = () => {
        setPopUp(!popUp);
    }

    const handleDocsPopUp = () => {
        setDocsPopUp(!docsPopUp);
    }

    const handleApply = async() => {
        try {
            const res = await nabidkaAPI.applyNabidka({
                "practice" : id
            })
            if (res) {
                addMessage(t('practice_detail.apply_success'), "S")
                handlePopUp()
                fetchData();
            }
        } catch (error) {
            console.error(error);
            const errorCode = error.code || "UNKNOWN_ERROR";
            addMessage(t(`api_errors.${errorCode}`, { defaultValue: t('practice_detail.apply_error') }), "E");
        }
    }

    const handleApprove = async () => {
        try {
            await studentpraticeAPI.updateStudentPracticeStatus(id, "approve");
            addMessage(t('practice_detail.approve_success'), "S");
            fetchData();
            setPopUp(false);
        } catch (error) {
            addMessage(t('practice_detail.approve_error'), "E");
        }
    }

    const handleReject = async () => {
        try {
            await studentpraticeAPI.updateStudentPracticeStatus(id, "reject");
            addMessage(t('practice_detail.reject_success'), "S");
            fetchData();
            setPopUp(false);
        } catch (error) {
            addMessage(t('practice_detail.reject_error'), "E");
        }
    }

    return(
        <>
            <BackButton/>

            {/* INFORMACE O STUDENTOVI */}
            <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8 mb-2 mt-4"}>
                <Container property="flex justify-between items-start">
                    <Container>
                        <Headings sizeTag={"h3"} property={""}>{t('practice_detail.student_title')}</Headings>
                        <Paragraph property={"mt-2"}>
                            {entity?.student_practice_status?.student_info?.full_name}
                        </Paragraph>
                        <Paragraph>
                            {`${t('students.personal_number')}: ${entity?.student_practice_status?.student_info?.os_cislo}`}
                        </Paragraph>
                        <Paragraph>
                            {`${t('profile.email')}: ${entity?.student_practice_status?.student_info?.email}`}
                        </Paragraph>
                    </Container>

                    {/* DUAL APPROVAL STATUS FOR PROFESSORS */}
                    {user && user.isProfessor() && entity?.student_practice_status && (
                        <Container property="flex flex-col gap-2 items-end">
                            <Container property="flex items-center gap-2">
                                <Paragraph property="text-sm font-medium">{t('practice_detail.school_approval')}:</Paragraph>
                                <Button
                                    variant={entity.student_practice_status.school_approved ? "greenSmall" : "yellowSmall"}
                                    pointer={false}
                                >
                                    {entity.student_practice_status.school_approved ? t('practice_detail.approved') : t('practice_detail.pending')}
                                </Button>
                            </Container>
                            <Container property="flex items-center gap-2">
                                <Paragraph property="text-sm font-medium">{t('practice_detail.employer_approval')}:</Paragraph>
                                <Button
                                    variant={entity.student_practice_status.employer_approved ? "greenSmall" : "yellowSmall"}
                                    pointer={false}
                                >
                                    {entity.student_practice_status.employer_approved ? t('practice_detail.approved') : t('practice_detail.pending')}
                                </Button>
                            </Container>
                        </Container>
                    )}
                </Container>
            </ContainerForEntity>

            {/* DOCS PANEL - show for anyone except REJECTED, or show always for professors */}
            {entity?.student_practice_status?.workflow_status && (
                (user.isProfessor() && entity.student_practice_status.workflow_status !== "REJECTED") ||
                !["PENDING", "REJECTED"].includes(entity.student_practice_status.workflow_status)
            ) && (
                <DocsPanel entity={entity} docData={docs} handleDownload={handleDownload} handleUpload={handleUpload} handleManage={handleDocsPopUp}/>
            )}


            <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
                <Container property="grid grid-cols-[auto,1fr] gap-4 mt-2 mb-4">

                    {/* LOGO */}
                    <Container property="w-32 h-32 rounded-lg p-4 flex items-center justify-center">
                        <Image
                            src={entity?.image_base64}
                            alt={entity?.title}
                            objectFit="cover"
                        />
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

                {/* CONTACT USER INFO */}
                {entity && entity.contact_user_info && (
                    <Container property={"editor-content mt-2"}>
                        <Headings sizeTag="h3" property="mb-4">{t('offers.contact_person')}</Headings>
                        {entity.contact_user_info.username && (
                            <Paragraph property="mb-2">
                                {t('practice_detail.username_label')}: {entity.contact_user_info.username}
                            </Paragraph>
                        )}
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
                )}
                <Container property={"grid grid-cols-1 gap-8 mt-4"}>
                    {/* TLAČÍTKO PRO PODÁNÍ PŘIHLÁŠKY */}
                    {user && user.isStudent() && (!entity?.student_practice_status) && (
                        <Button property="col-start-1 justify-self-end w-full" onClick={handlePopUp}>{t('offers.apply')}</Button>
                    )}

                    {/* TLAČÍTKA PRO SPRÁVU */}
                    {user && entity?.can_approve && (
                        <Container property="flex gap-4 justify-end">
                            <Button variant={"primary"} icon={"gear"} onClick={handlePopUp}>{t('common.manage')}</Button>
                        </Container>
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

            {/* PODÁNÍ PŘIHLÁŠKY - STUDENT */}
            {popUp && user && user.isStudent() && (
                <PopUpCon
                    useCustomContainer={true}
                    onClose={handlePopUp}
                    title={t('nav.applications')}
                    text={t('internships.start_practice_confirm')}
                    onSubmit={handleApply}
                    onSubmitText={t('practice_detail.apply_button')}
                    onReject={handlePopUp}
                    onRejectText={t('common.cancel')}
                />
            )}

            {/* SCHVALOVÁNÍ PŘIHLÁŠKY - UČITEL/ORGANIZACE */}
            {popUp && user && (user.isDepartmentUser() || user.isOrganizationUser()) && (
                <PopUpCon
                    onClose={handlePopUp}
                    title={t('practice_detail.manage_app')}
                    text={t('practice_detail.confirm_app_text', { name: entity?.student_practice_status?.student_info?.full_name })}
                    onSubmit={handleApprove}
                    onSubmitText={t('common.approve')}
                    onReject={handleReject}
                    onRejectText={t('common.reject')}
                />
            )}

            {/* KONTROLA DOKUMENTŮ */}
            {docsPopUp && (
                <PopUpCon
                    useCustomContainer={true}
                    onClose={handleDocsPopUp}
                    title={t('practice_detail.docs_check_title')}
                    text={t('practice_detail.docs_check_not_defined')}
                />
            )}
        </>
    )
}
