import React from "react"
import Container from "@core/Container/Container"
import ContainerForEntity from "@core/Container/ContainerForEntity"
import Paragraph from "@components/core/Text/Paragraph"
import Headings from "@components/core/Text/Headings"
import { Image } from "@components/core/Image"
import { useNavigate } from "react-router-dom"
import Button from "@components/core/Button/Button"
import { useUser } from "@hooks/UserProvider"

export default function NabidkaEntity({ entity }) {
    const navigate = useNavigate();
    const { user } = useUser();

    const handleVariant = (approval_status, buttonType=false) => {
        switch (approval_status) {
            case 0: // PENDING
                return buttonType ? "yellowSmall" : "yellow";
            case 1: // APPROVED
                return buttonType ? "green" : "green";
            case 2: // REJECTED
                return buttonType ? "redSmall" : "red";
            default:
                return buttonType ? "gray" : "gray";
        }
    }

    const approvalTag = (approval_status) => {
        switch (approval_status) {
            case 0: // PENDING
                return "Čeká ke schválení";
            case 1: // APPROVED
                return "Probíhající stáž";
            case 2: // REJECTED
                return "Zrušená stáž";
            default:
                return;
        }
    }

    const handleClick = () => {
        navigate(`/nabidka/${entity.practice_id}`);
    }

    return(
        <ContainerForEntity id={entity.practice_id} variant={user.isDepartmentMg() ? handleVariant(entity.approval_status) : "gray"} onClick={handleClick} property="hover:shadow-lg transition-shadow duration-200">
            <Container property="grid grid-cols-[auto,1fr] gap-4">
                {/* OBRÁZEK PRAXE */}
                <Container property="w-24 h-24 rounded-lg overflow-hidden">
                    <Image
                        src={entity.image_base64}
                        alt={entity.title}
                        className="w-full h-full"
                        objectFit="cover"
                        fallbackSrc="https://via.placeholder.com/96x96/3B82F6/FFFFFF?text=P"
                    />
                </Container>

                <Container property="grid grid-cols-1">
                    {/* TITULEK */}
                    <Container property="flex inline-block p-1 space-y-1">
                        <Headings sizeTag="h5-bold" property="text-black">
                            {entity.title}
                        </Headings>

                        {user.isDepartmentMg() &&
                        (<Container property={"justify-end ml-auto"}>
                            <Button
                                variant={handleVariant(entity.approval_status, true)}
                                onClick={handleClick}
                                hover={false}
                            >
                                {approvalTag(entity.approval_status)}
                            </Button>
                        </Container>)
                        }
                        
                    </Container>

                    {/* ANOTACE */}
                    <Container property="p-1 space-y-1">
                        <Container property="space-y-1">
                            <Paragraph variant="base" property="text-gray-600 line-clamp-3">
                                {entity.description}
                            </Paragraph>
                        </Container>
                        
                        {/* MÍSTO KONÁNÍ */}
                        <Container property="flex justify-between items-center">
                            <Container property="bg-blue-400 px-2 p-1 rounded-lg">
                                <Paragraph variant="small" property="text-white">
                                    {entity.employer.address}
                                </Paragraph>
                            </Container>
                        </Container>
                    </Container>
                </Container>
            </Container>
        </ContainerForEntity>
    )
}