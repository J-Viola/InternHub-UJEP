import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import BackButton from "@core/Button/BackButton";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import { useParams } from "react-router-dom";
import Button from "@core/Button/Button";
import StateBadge from "@core/StateBadge";
import DocsPanel from "@components/Nabidka/DocsPanel";
import PopUpCon from "@core/Container/PopUpCon";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI"
import { useStudentPracticeAPI } from "@api/student_practice/student_practiceAPI";
import { useUser } from "@hooks/UserProvider";
import { Image } from "@components/core/Image"
import { useMessage } from "@hooks/MessageContext";
import ProgressPanel from "@components/Nabidka/ProgressBar";
import { useDocumentsAPI } from "@api/documents/documentsAPI";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { buildFormData } from "@utils/formDataUtils";
import Icon from "@components/core/Icon/Icon";
import LoadingState from "@components/core/Feedback/LoadingState";
import ErrorState from "@components/core/Feedback/ErrorState";
import getApiErrorMessage from "@utils/apiErrorUtils";

export default function NabidkaDetailPage() {
    const { t } = useTranslation();
    const { id } = useParams();
    const [ popUp, setPopUp ] = useState(false);
    // BL-07/PBUG-BL07-07: stornování aktivní nabídky (oprávněné roly)
    const [ cancelPopUp, setCancelPopUp ] = useState(false);
    const [ cancelReason, setCancelReason ] = useState("");
    const [ entity, setEntity ] = useState(null);
    const nabidkaAPI = useNabidkaAPI();
    const studentPracticeAPI = useStudentPracticeAPI();
    const documentAPI = useDocumentsAPI();
    const { user } = useUser();
    const { addMessage } = useMessage();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);

    const [docs, setDocs] = useState([]);

    const fetchData = async () => {
        setLoading(true);
        setLoadError(false);
        try {
            const result = await nabidkaAPI.getNabidkaById(id);
            setEntity(result);
            setDocs(result.student_practice_documents || []);
        } catch (error) {
            addMessage(t('common.error'), "E");
            setLoadError(true);
        } finally {
            setLoading(false);
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
            setTimeout(() => window.URL.revokeObjectURL(url), 100);
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
            const formData = buildFormData({ document: file });
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

    // BL-07/PBUG-BL07-07: stornování AKTIVNÍ nabídky reálnou UI akcí.
    // Backend: POST /api/practices/{id}/cancel/ (CanCancelPractice: admin /
    // vedoucí katedry / garant); důvod je povinný. Chyby řeší existující
    // error resolver (getApiErrorMessage).
    const handleCancelOffer = async () => {
        if (cancelReason.trim().length < 5) {
            addMessage(t('offers.cancel_reason_required'), "E");
            return;
        }
        try {
            await nabidkaAPI.cancelPractice(id, cancelReason.trim());
            addMessage(t('offers.cancel_offer_success'), "S");
            setCancelPopUp(false);
            setCancelReason("");
            fetchData();
        } catch (error) {
            addMessage(getApiErrorMessage(error, t, 'offers.cancel_offer_error'), "E");
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

    const handleReapply = async () => {
        try {
            await studentPracticeAPI.reapplyToPractice(entity.practice_id);
            addMessage(t('practice_detail.reapply_success'), "S");
            navigate('/praxe');
        } catch (error) {
            const detail = error?.response?.data?.detail || error?.details || t('practice_detail.reapply_error');
            addMessage(detail, "E");
        }
    }

    const renderContactInfo = () => {
        return (
            <Container property={"editor-content mt-2"}>
                <Container property="flex justify-between items-center mb-4">
                    <Headings sizeTag="h3">{t('offers.contact_person')}</Headings>
                    {entity.student_practice_status && (
                        <StateBadge status={entity.student_practice_status.workflow_status} />
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

            {loading && (
                <LoadingState message={t('common.loading')} />
            )}

            {!loading && loadError && (
                <ErrorState
                    description={t('common.error')}
                    onRetry={fetchData}
                />
            )}

            {!loading && !loadError && entity && (
            <>
            {/* DOCS PANEL */}
            {entity?.student_practice_status?.workflow_status &&
                !["PENDING", "REJECTED"].includes(entity.student_practice_status.workflow_status) && (
                <DocsPanel entity={entity} docData={docs} handleDownload={handleDownload} handleUpload={handleUpload}/>
            )}
            <ContainerForEntity property="p-8 mb-8 mt-4 border border-black rounded-[10px] shadow-none bg-white">
                <Container property="grid grid-cols-[auto,1fr] gap-8 items-start mb-8 pb-8 border-b border-gray-100">

                    {/* LOGO */}
                    <Container property="w-40 h-40 rounded-[10px] bg-gray-50 border border-gray-200 overflow-hidden flex items-center justify-center p-2">
                        <Image
                            src={entity?.image_base64}
                            alt={entity?.title}
                            className="w-full h-full"
                            objectFit="contain"
                        />
                    </Container>

                    {/* TITLE */}
                    <Container property="flex flex-col gap-4">
                        <Headings sizeTag="h2" property="text-black font-black uppercase tracking-tight">
                            {entity?.title}
                        </Headings>
                        <Container property="flex flex-wrap gap-3 mt-2">
                            <Container property="bg-[#93c5fd] text-white px-5 py-1.5 rounded-full font-medium text-sm shadow-sm whitespace-nowrap flex items-center gap-2">
                                <Icon name="location-dot" size={14} color="text-white" />
                                {t('offers.location')}: {entity?.employer?.address || t('common.not_specified')}
                            </Container>
                            <Container property="bg-[#93c5fd] text-white px-5 py-1.5 rounded-full font-medium text-sm shadow-sm whitespace-nowrap flex items-center gap-2">
                                <Icon name="calendar" size={14} color="text-white" />
                                {entity?.start_date} - {entity?.end_date}
                            </Container>
                            {entity?.skills?.map((skill, index) => (
                                <Container key={index} property="bg-[#93c5fd] text-white px-5 py-1.5 rounded-full font-medium text-sm shadow-sm whitespace-nowrap">
                                    #{skill}
                                </Container>
                            ))}
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

                    {user && user.isStudent() && entity?.student_practice_status &&
                        (entity.student_practice_status.workflow_status === "REJECTED" || entity.student_practice_status.workflow_status === "CANCELLED") && (
                        <Button variant="green" onClick={handleReapply}>
                            {t('practice_detail.reapply_button')}
                        </Button>
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

                    {/* BL-07/PBUG-BL07-07: storno aktivní nabídky — jen pro
                        oprávněné roly dle backend CanCancelPractice
                        (admin / vedoucí katedry / garant); chyby řeší
                        error resolver v handleCancelOffer. */}
                    {entity && (user.isAdmin() || user.isDepartmentMg()) && entity?.approval_status === 1 && (
                        <Button
                            variant={"red"}
                            property={"px-8"}
                            onClick={() => { setCancelReason(""); setCancelPopUp(true); }}
                        >
                            {t('offers.cancel_offer')}
                        </Button>
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
                                onClick={() => navigate(`/upravit-nabidku/${entity.practice_id}`)}
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
                                onClick={() => navigate(`/upravit-nabidku/${entity.practice_id}`)}
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
                    onSubmitText={t('common.approve')}
                    onRejectText={t('common.reject')}
                />
            )}

            {/* BL-07/PBUG-BL07-07: popup storna nabídky s povinným důvodem */}
            {cancelPopUp && (
                <PopUpCon
                    onClose={() => { setCancelPopUp(false); setCancelReason(""); }}
                    title={t('offers.cancel_offer')}
                    text={t('offers.cancel_offer_text')}
                    onSubmit={handleCancelOffer}
                    onSubmitText={t('offers.cancel_offer')}
                    onReject={() => { setCancelPopUp(false); setCancelReason(""); }}
                >
                    <Container property={"mb-4"}>
                        <label htmlFor="cancel-reason" className="block text-sm font-medium text-gray-700 mb-1">
                            {t('offers.cancel_reason')}
                        </label>
                        <textarea
                            id="cancel-reason"
                            value={cancelReason}
                            onChange={(e) => setCancelReason(e.target.value)}
                            rows={3}
                            className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                            placeholder={t('offers.cancel_reason_placeholder')}
                        />
                    </Container>
                </PopUpCon>
            )}
            </>
            )}
        </>
    )
}
