import React from "react"
import Container from "@core/Container/Container"
import ContainerForEntity from "@core/Container/ContainerForEntity"
import Paragraph from "@components/core/Text/Paragraph"
import Headings from "@components/core/Text/Headings"
import { Image } from "@components/core/Image"
import { useNavigate } from "react-router-dom"
import Button from "@components/core/Button/Button"
import { useUser } from "@hooks/UserProvider"

export default function NabidkaEntityInline({ entity, onClick, onView, isSelected = false }) {
    const navigate = useNavigate();
    const { user } = useUser();

    const handleVariant = (approval_status, buttonType=false) => {

        if (isSelected) {
            return "green";
        }
        else {
            return "gray";
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
        if (onClick) {
            onClick(entity);
        } else {
            navigate(`/nabidka/${entity.practice_id}`);
        }
    }

    return(
        <ContainerForEntity 
            id={entity.practice_id} 
            variant={handleVariant(isSelected)} 
            onClick={handleClick} 
            property="hover:shadow-lg transition-shadow duration-200"
        >
            <Container property="flex items-center justify-between p-4">
                {/* LEVÁ STRANA - OBRÁZEK A NÁZEV */}
                <Container property="flex items-center space-x-4">
                    {/* OBRÁZEK PRAXE */}
                    <Container property="w-16 h-16 rounded-lg overflow-hidden flex-shrink-0">
                        <Image
                            src={entity.image_base64}
                            alt={entity.title}
                            className="w-full h-full"
                            objectFit="cover"
                            fallbackSrc="https://via.placeholder.com/64x64/3B82F6/FFFFFF?text=P"
                        />
                    </Container>

                    {/* NÁZEV A ADRESA */}
                    <Container property="flex flex-col">
                        <Headings sizeTag="h5-bold" property="text-black mb-1">
                            {entity.title}
                        </Headings>
                        <Paragraph variant="small" property="text-gray-600">
                            {entity.employer.address}
                        </Paragraph>
                    </Container>
                </Container>

                {/* PRAVÁ STRANA - STATUS A TLAČÍTKA */}
                <Container property="flex items-center space-x-3">
                                         {/* TLAČÍTKA */}
                     <Container property="flex flex-row gap-4 justify-end flex-shrink-0">
                         <Button 
                             noVariant={true} 
                             icon={"eye"} 
                             iconColor={"text-black"} 
                             iconSize={"24"} 
                             onClick={(e) => {
                                 e.stopPropagation();
                                 onView();
                             }}
                         />
                         <Button
                             icon={isSelected ? "check" : "plus"}
                             noVariant={true}
                             iconSize={"24"}
                             iconColor={"text-black"} 
                             onClick={(e) => {
                                 e.stopPropagation();
                                 if (onClick) {
                                     onClick(entity);
                                 }
                             }}
                             size="sm"
                         >
                         </Button>
                     </Container>
                </Container>
            </Container>
        </ContainerForEntity>
    )
}
