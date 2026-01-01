import React, { useState } from "react";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import Headings from "@components/core/Text/Headings";
import { Image } from "@components/core/Image";
import Button from "@components/core/Button/Button";
import { useNavigate } from "react-router-dom";
import { useStudentPracticeAPI } from "@api/student_practice/student_practiceAPI";
import { useMessage } from "@hooks/MessageContext";

export default function StudentInvitationCard({ entity, onResponse }) {
    const navigate = useNavigate();
    const { manageEmployerInvitation } = useStudentPracticeAPI();
    const { addMessage } = useMessage();
    const [loading, setLoading] = useState(false);

    const handleResponse = async (action, e) => {
        e.stopPropagation();
        setLoading(true);
        try {
            await manageEmployerInvitation(entity.invitation_id, action);
            addMessage(action === "ACCEPT" ? "Pozvánka přijata" : "Pozvánka odmítnuta", "S");
            if (onResponse) onResponse();
        } catch (error) {
            addMessage("Chyba při zpracování pozvánky", "E");
        } finally {
            setLoading(false);
        }
    };

    return (
        <ContainerForEntity 
            variant={"white"} 
            property="hover:shadow-lg transition-shadow duration-200 border border-gray-200"
            onClick={() => entity.practice_id && navigate(`/nabidka/${entity.practice_id}`)}
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
                    <Headings sizeTag="h5-bold">{entity.practice_title || "Neznámá praxe"}</Headings>
                    <Paragraph variant="small" property="text-gray-500">
                        Obdrženo: {entity.submission_date}
                    </Paragraph>
                </Container>

                <Container property="justify-self-end flex gap-2">
                     <Button
                        variant="green"
                        onClick={(e) => handleResponse("ACCEPT", e)}
                        loading={loading}
                    >
                        Přijmout
                    </Button>
                    <Button
                        variant="red"
                        onClick={(e) => handleResponse("REJECT", e)}
                        loading={loading}
                    >
                        Odmítnout
                    </Button>
                </Container>
            </Container>
        </ContainerForEntity>
    );
}
