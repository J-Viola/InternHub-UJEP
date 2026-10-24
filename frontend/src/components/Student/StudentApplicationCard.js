import React from "react";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import Headings from "@components/core/Text/Headings";
import { Image } from "@components/core/Image";
import Button from "@components/core/Button/Button";
import StateBadge from "@core/StateBadge";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function StudentApplicationCard({ entity }) {
    const navigate = useNavigate();
    const { t } = useTranslation();

    // Vlastní přihláška má jít na kartu praxes (SP detail), ne na katalog
    // nabídek — uzavřené/čekající/vlastní SP by jinak skončily 404 (FE-003).
    const handleOpen = () => {
        if (entity.student_practice_id) {
            navigate(`/karta-praxe/${entity.student_practice_id}`);
        } else {
            navigate(`/nabidka/${entity.practice_id}`);
        }
    };

    return (
        <ContainerForEntity
            variant={"white"}
            property="pl-8 pr-8 py-4 mt-2 border border-black rounded-[10px] shadow-none hover:shadow-sm transition-shadow duration-200"
            onClick={handleOpen}
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
                <Container property="flex items-center gap-2 justify-end">
                    {/* workflow_status dodává až backend (hlášeno v BL-04) —
                        bez něj se badge nezobrazuje místo chybného "Neznámý" */}
                    {entity.workflow_status && (
                        <StateBadge status={entity.workflow_status} />
                    )}
                </Container>
            </Container>
        </ContainerForEntity>
    );
}
