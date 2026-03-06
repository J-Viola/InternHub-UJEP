import React from "react";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import Button from "@core/Button/Button";
import { useTranslation } from "react-i18next";

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
    const created = entity.created_at || entity.start_date || "-";
    const subjectCode = entity.subject?.subject_code || "-";

    return (
        <ContainerForEntity id={`practice-offer-${entity.practice_id}`} variant={bg} property={`pl-8 pt-4 pb-4 pr-4`} onClick={onView}>
            <Container property={"flex items-center justify-between"}>

                <Container property={"flex items-center gap-6 flex-1"}>
                    <Container property={"min-w-[200px]"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            {t('form.contact_user')}
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {getContactName(entity.contact_user_info)}
                        </Paragraph>
                    </Container>
                    <Container property={"flex-1"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            {t('form.title')}
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {entity.title || "-"}
                        </Paragraph>
                    </Container>
                    <Container property={"min-w-[100px] text-center"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            {t('subjects.code')}
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {subjectCode}
                        </Paragraph>
                    </Container>
                    <Container property={"min-w-[180px] text-center"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            {t('internships.creation_date')}
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {created}
                        </Paragraph>
                    </Container>
                    <Container property={"min-w-[180px] text-center"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            {t('internships.submitted_applications')}
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {type === "approved" ? `${approved}/${pending}/${available}` : ("- / - / - ")}
                        </Paragraph>
                    </Container>
                </Container>
                    {type === "approved" && (
                        <Container property={"flex items-center gap-4 ml-4"}>
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
                                title={t('internships.view_detail')}
                                icon="eye"
                                iconColor={"gray"}
                                iconSize={"24"}
                            />
                        </Container>
                    )}
                    {type === "to_approve" && (
                        <Container property={"flex items-center gap-4 ml-4"}>
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
                        </Container>
                    )}
            </Container>
        </ContainerForEntity>
    );
}
