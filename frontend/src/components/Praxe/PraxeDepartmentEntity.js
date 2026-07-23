import React from "react";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import Button from "@core/Button/Button";
import { useTranslation } from "react-i18next";
import { daysSinceCzechDate, isOlderThan } from "@utils/dateUtils";

export default function PraxeDepartmentEntity({ type, entity, onClick, onView }) {
    const { t } = useTranslation();

    const getContactName = (info) => {
        if (!info) return t('common.not_specified');
        if (info.username) return info.username;
        if (info.first_name && info.last_name) return `${info.first_name} ${info.last_name}`
        return t('common.not_specified');
    };

    const bg = type === "to_approve" ? "yellow" : "gray";
    const approved = entity.approved_applications ?? 0;
    const pending = entity.pending_applications ?? 0;
    const available = entity.available_positions ?? 0;
    const created = entity.created_at || entity.application_date || "-";
    const subjectCode = entity.subject?.subject_code || entity.subject_code || "-";

    // Contract pending escalation logic
    const isContractPending = type === "approved" &&
        entity.workflow_state === "PRELIMINARY_APPROVED" &&
        !entity.contract_received_date;

    let contractPendingDays = 0;
    let isEscalated = false;
    if (isContractPending && entity.updated_at) {
        contractPendingDays = daysSinceCzechDate(entity.updated_at);
        isEscalated = isOlderThan(entity.updated_at, 7);
    }

    return (
        <ContainerForEntity id={`practice-offer-${entity.practice_id}`} variant={bg} property={`pl-8 pt-4 pb-4 pr-4 cursor-default relative`}>
            {/* Escalation warning stripe for contract pending > 7 days */}
            {isEscalated && (
                <div className="absolute left-0 top-0 bottom-0 w-1.5 bg-orange-500 rounded-l" />
            )}
            <Container property={"flex items-center justify-between"}>

                <Container property={"flex items-center gap-6 flex-1"}>
                    {/* STUDENT / CONTACT PERSON */}
                    <Container property={"min-w-[200px]"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            {type === "approved" ? t('practice_detail.student_title') : t('form.contact_user')}
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {type === "approved" ? (entity.student_full_name || "-") : getContactName(entity.contact_user_info)}
                        </Paragraph>
                    </Container>

                    {/* TITLE */}
                    <Container property={"flex-1"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            {t('form.title')}
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {entity.title || entity.practice_title || "-"}
                        </Paragraph>
                    </Container>

                    {/* SUBJECT */}
                    <Container property={"min-w-[100px] text-center"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            {t('subjects.code')}
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {subjectCode}
                        </Paragraph>
                    </Container>

                    {/* DATE */}
                    <Container property={"min-w-[180px] text-center"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            {type === "approved" ? t('students.applied_on') : t('internships.creation_date')}
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {created}
                        </Paragraph>
                    </Container>

                    {/* STATUS / STATS */}
                    <Container property={"min-w-[180px] text-center"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            {type === "approved" ? t('common.status') : t('internships.submitted_applications')}
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {type === "approved" ? (entity.workflow_status_label || "-") : (`${approved}/${pending}/${available}`)}
                        </Paragraph>
                        {isContractPending && (
                            <div className={`mt-1 inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-semibold ${isEscalated ? 'bg-orange-100 text-orange-700 border border-orange-200' : 'bg-amber-50 text-amber-700 border border-amber-200'}`}>
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.206 16.5c-.77.833.192 2.5 1.732 2.5z" /></svg>
                                {t('internships.contract_pending_badge', { days: contractPendingDays })}
                            </div>
                        )}
                    </Container>
                </Container>

                {/* ACTIONS */}
                <Container property={"flex items-center gap-4 ml-4"}>
                    {type === "approved" && (
                        <>
                            <Button
                                noVariant={true}
                                onClick={(e) => { e.stopPropagation(); onClick(); }}
                                title={t('internships.view_applications')}
                                icon="users"
                                iconColor={"gray"}
                                iconSize={"24"}
                            />
                            <Button
                                noVariant={true}
                                onClick={(e) => { e.stopPropagation(); onView(); }}
                                title={t('practice_detail.view_card')}
                                icon="eye"
                                iconColor={"gray"}
                                iconSize={"24"}
                            />
                        </>
                    )}
                    {type === "to_approve" && (
                        <>
                            <Button
                                noVariant={true}
                                onClick={(e) => { e.stopPropagation(); onClick(); }}
                                title={t('internships.change_status')}
                                icon="gear"
                                iconColor={"gray"}
                                iconSize={"24"}
                            />
                            <Button
                                noVariant={true}
                                onClick={(e) => { e.stopPropagation(); onView(); }}
                                title={t('internships.view_detail')}
                                icon="eye"
                                iconColor={"gray"}
                                iconSize={"24"}
                            />
                        </>
                    )}
                </Container>
            </Container>
        </ContainerForEntity>
    );
}
