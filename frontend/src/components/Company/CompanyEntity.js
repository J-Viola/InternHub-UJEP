import React from "react";
import Button from "@core/Button/Button";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Paragraph from "@components/core/Text/Paragraph";
import { useTranslation } from "react-i18next";

export default function CompanyEntity({entity, buttons, onClick}) {
    const { t } = useTranslation();
    return (
        <ContainerForEntity 
            variant="gray" 
            property="pl-8 pr-8 py-4 mt-2 border border-black rounded-[10px] shadow-none hover:shadow-sm transition-shadow duration-200" 
            onClick={onClick}
        >
            <Container property="grid grid-cols-[1.5fr,1fr,2fr,auto] gap-4 items-center w-full">
                {/* Column 1: Name */}
                <Container property="min-w-0">
                    <Paragraph property="font-bold text-black truncate">
                        {entity.company_name}
                    </Paragraph>
                </Container>

                {/* Column 2: ICO */}
                <Container property="text-center">
                    <Paragraph property="text-gray-600 text-sm">
                        {t('profile.ico')}: {entity.ico}
                    </Paragraph>
                </Container>

                {/* Column 3: Address */}
                <Container property="text-center min-w-0">
                    <Paragraph property="text-gray-600 text-sm truncate">
                        {entity.address}
                    </Paragraph>
                </Container>

                {/* Column 4: Actions */}
                <Container property="flex flex-row gap-4 justify-end items-center">
                    {buttons.map(btn => (
                        <Button
                            key={btn.icon}
                            noVariant={true}
                            icon={btn.icon}
                            iconColor="text-black hover:text-facultyCol transition-colors"
                            iconSize="28"
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
