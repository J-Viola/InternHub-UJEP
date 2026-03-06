import React from "react";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import Button from "@core/Button/Button";
import { Image } from "@components/core/Image";
import { useTranslation } from "react-i18next";

export default function PraxeEntity({type, entity, onClick, onView, onStudentsView}) {
    const { t } = useTranslation();

    //dopladit podle type
    const statusToText = (status) => {
        if (status === "Pozvánka" || status === t('internships.invitation_label')) return t('status.PENDING');

        // Mapování podle enumů z backendu
        switch (status) {
            case 0: return t('status.PENDING');
            case 1: return t('status.APPROVED');
            case 2: return t('status.REJECTED');
            case 3: return t('status.CANCELLED');
            default: return t('common.not_specified');
        }
    }

    const getStatusColor = (status, type) => {
        if (status === "Pozvánka" || status === t('internships.invitation_label')) return "yellow"; // Speciální barva pro pozvánky

        // Mapování podle enumů z backendu
        switch (status) {
            case 0: return "gray";  // PENDING - čeká na schválení
            case 1: return "green";   // APPROVED - schváleno
            case 2: return "red";     // REJECTED - zamítnuto
            case 3: return "gray";    // CANCELLED - zrušeno
            default: return "gray";
        }
    }

    // Render pro organizační praxe
    if (type === "organization_practices") {
        return (
            <ContainerForEntity property={"pl-8 pt-4 pb-4 pr-4"}>
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
                                {t('common.status')}
                            </Paragraph>
                            <Paragraph property={"font-medium"}>
                                {statusToText(entity.approval_status)}
                            </Paragraph>
                        </Container>
                        <Container property={"min-w-[150px]"}>
                            <Paragraph property={"text-sm text-gray-500 mb-1"}>
                                {t('internships.creation_date')}
                            </Paragraph>
                            <Paragraph property={"font-medium"}>
                                {entity.created_at}
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
                                    onClick={onView}
                                    title={t('internships.view_applications')}
                                    icon={"users"}
                                    iconColor={"gray"}
                                    iconSize={"24"}
                                />
                                <Button
                                    noVariant={true}
                                    onClick={onClick}
                                    title={t('internships.edit_internship')}
                                    icon={"edit"}
                                    iconColor={"gray"}
                                    iconSize={"24"}
                                />
                            </>
                        ) : (
                                // PAK DOLADIT VIEW
                            <>
                                <Button
                                    noVariant={true}
                                    onClick={onView}
                                    title={t('internships.view_applications')}
                                    icon={"eye"}
                                    iconColor={"gray"}
                                    iconSize={"24"}
                                />

                                <Button
                                    noVariant={true}
                                    onClick={onClick}
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
        );
    }

    // Původní render pro studenty a pozvánky
    return(
        <ContainerForEntity
            variant={getStatusColor(entity.status, type)}
            property={"pl-8 pt-4 pb-4 pr-4"}
            onClick={(entity.status === "Pozvánka" || entity.status === t('internships.invitation_label')) ? onClick : onView}
        >
            <Container property={"flex items-center justify-between"}>
                <Container property={"flex items-center gap-6 flex-1"}>
                    <Container property={"min-w-[60px]"}>
                        <Image width={"50px"} height={"50px"} src={entity.company_logo}/>
                    </Container>
                    <Container property={"flex-1 min-w-0"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            {t('form.title')}
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {entity.practice_title || "-"}
                        </Paragraph>
                    </Container>
                    <Container property={"min-w-[150px]"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            {t('internships.applied_on')}
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {entity.application_date}
                        </Paragraph>
                    </Container>
                    <Container property={"min-w-[120px]"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            {t('common.status')}
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {statusToText(entity.status)}
                        </Paragraph>
                    </Container>
                                    </Container>
                <Container property={"flex items-center gap-4 ml-16"}>
                    <Button
                        noVariant={true}
                        icon="eye"
                        iconColor={"gray"}
                        iconSize={"24"}
                        onClick={onView}
                        title={t('internships.view_detail')}
                    />

                    {(entity.status === "Pozvánka" || entity.status === t('internships.invitation_label')) &&
                        <Button
                            noVariant={true}
                            icon="manage"
                            iconColor={"gray"}
                            iconSize={"24"}
                            onClick={onClick}
                            title={t('internships.manage_invitation')}
                        />
                    }
                </Container>
            </Container>
        </ContainerForEntity>
    )
}
