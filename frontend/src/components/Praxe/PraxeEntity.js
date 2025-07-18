import React from "react";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Headings from "@core/Text/Headings";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import Button from "@core/Button/Button";
import { Image } from "@components/core/Image";

export default function PraxeEntity({type, entity, onClick, onView}) {

    //dopladit podle type
    const statusToText = (status) => {
        if (status === "Pozvánka") return "Čeká na schválení";
        
        // Mapování podle enumů z backendu
        switch (status) {
            case 0: return "Čeká na schválení";
            case 1: return "Schváleno";
            case 2: return "Zamítnuto";
            case 3: return "Zrušeno";
            default: return "Neznámý";
        }
    }

    const getStatusColor = (status, type) => {
        if (status === "Pozvánka") return "yellow"; // Speciální barva pro pozvánky
        
        // Mapování podle enumů z backendu
        switch (status) {
            case 0: return "gray";  // PENDING - čeká na schválení
            case 1: return "green";   // APPROVED - schváleno
            case 2: return "red";     // REJECTED - zamítnuto
            case 3: return "gray";    // CANCELLED - zrušeno
            default: return "gray";
        }
    }

    return(
        <ContainerForEntity variant={getStatusColor(entity.status, type)} property={"pl-8 pt-2 pb-2 pr-4"}>
            <Container property={"grid grid-cols-5 gap-2 items-center"}>
                <Image width={"50px"} height={"50px"} src={entity.company_logo}/>
                <Paragraph variant={"baseBold"}>{entity.practice_title}</Paragraph>
                <Paragraph>Datum podání: {entity.application_date}</Paragraph>
                <Paragraph>Status: {statusToText(entity.status)}</Paragraph>
                {/* POKUD BUDE ZAMÍTNUTÁ, TAK NEBUDE MÍT IKONU */}

                <Container property={"flex flex-row gap-4 inline-block justify-end"}>
                    <Button noVariant={true} icon="eye" iconColor={"text-black"} iconSize={"24"} onClick={onView}></Button>
                    
                    {entity.status === "Pozvánka" && 
                        <Button noVariant={true} icon="manage" iconColor={"text-black"} iconSize={"24"} onClick={onClick}></Button>
                    }
                    </Container>

            </Container>
    </ContainerForEntity>
    )
}