import React from "react";
import Button from "@core/Button/Button";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Paragraph from "@components/core/Text/Paragraph";
import { useTranslation } from "react-i18next";

export default function DepartmentEntity({entity, buttons, onClick}) {
    const { t } = useTranslation();
    return (
        <ContainerForEntity variant="gray" property={"pl-8 pt-4 pb-4 pr-4 mt-2"} onClick={onClick}>
            <Container property="flex flex-row items-center gap-8 w-full">
                <Container property="flex-shrink-0 min-w-[300px]">
                    <Paragraph>
                        {t('departments.head_label')}: {entity.head_of_department_name || entity.head_of_department || t('common.not_specified')}
                    </Paragraph>
                </Container>
                <Container property="flex-1">
                    <Paragraph variant={"baseBold"}>
                        {entity.department_name}
                    </Paragraph>
                </Container>
                <Container property="flex flex-row gap-4 justify-end flex-shrink-0">
                    {buttons.map(btn => (
                        <Button
                            key={btn.icon}
                            noVariant={true}
                            icon={btn.icon}
                            iconColor={"text-black"}
                            iconSize={"24"}
                            onClick={(e) => {
                                e.stopPropagation();
                                btn.btnfunction();
                            }}
                        />
                    ))}
                </Container>
            </Container>
        </ContainerForEntity>
    )
}
