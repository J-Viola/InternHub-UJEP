import React from "react";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import Headings from "@components/core/Text/Headings";
import { Image } from "@components/core/Image";
import Button from "@components/core/Button/Button";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function StudentApplicationCard({ entity }) {
    const navigate = useNavigate();
    const { t } = useTranslation();

    const handleVariant = (status) => {
        switch (status) {
            case "PENDING":
                return "yellow";
            case "APPROVED":
                return "green";
            case "REJECTED":
                return "red";
            case "IN_PROGRESS":
                return "blue";
            case "COMPLETED":
                return "green";
            case "CANCELLED":
                return "red";
            default:
                return "gray";
        }
    };

    return (
        <ContainerForEntity
            variant={"white"}
            property="pl-8 pr-8 py-4 mt-2 border border-black rounded-[10px] shadow-none hover:shadow-sm transition-shadow duration-200"
            onClick={() => navigate(`/nabidka/${entity.practice_id}`)}
        >
            <Container property="grid grid-cols-[1.5fr,1.5fr,auto] gap-4 items-center w-full">
                {/* Column 1: Title */}
                <Container property="min-w-0">
                    <Headings sizeTag="h5-bold" property="truncate text-black">
                        {entity.practice_title}
                    </Headings>
                </Container>

                {/* Column 2: Date */}
                <Container property="text-center">
                    <Paragraph property="font-medium text-gray-500 text-sm">
                        {t('internships.applied_on')}: {entity.application_date}
                    </Paragraph>
                </Container>

                {/* Column 3: Status Badge */}
                <Container property="flex justify-end">
                     <Button
                        variant={handleVariant(entity.workflow_status)}
                        pointer={false}
                        hover={false}
                        property="px-4 py-1 text-xs"
                    >
                        {entity.workflow_status_label}
                    </Button>
                </Container>
            </Container>
        </ContainerForEntity>
    );
}
