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
            property="hover:shadow-lg transition-shadow duration-200 border border-gray-200"
            onClick={() => navigate(`/nabidka/${entity.practice_id}`)}
        >
            <Container property="grid grid-cols-[auto,1fr] gap-4 items-center p-4">
                {/* LOGO */}
                <Container property="w-16 h-16 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
                    <Image
                        src={entity.company_logo}
                        alt={entity.practice_title}
                        className="w-full h-full"
                        objectFit="cover"
                        fallbackSrc="https://via.placeholder.com/64x64?text=LOGO"
                    />
                </Container>

                <Container property="flex flex-col gap-1">
                    <Headings sizeTag="h5-bold">{entity.practice_title}</Headings>
                    <Paragraph variant="small" property="text-gray-500">
                        {t('internships.applied_on')}: {entity.application_date}
                    </Paragraph>
                </Container>

                <Container property="justify-self-end">
                     <Button
                        variant={handleVariant(entity.workflow_status)}
                        pointer={false}
                        hover={false}
                    >
                        {entity.workflow_status_label}
                    </Button>
                </Container>
            </Container>
        </ContainerForEntity>
    );
}
