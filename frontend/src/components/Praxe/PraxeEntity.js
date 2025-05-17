import React from "react";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Headings from "@core/Text/Headings";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import Button from "@core/Button/Button";

export default function PraxeEntity({entity, onClick, onView}) {

    const statusEntity = {
        "Probíhající stáž": "green",
        "Zrušená přihláška": "red",
        "Zaslaná přihláška": "gray",
        "Pozvánka": "yellow" 

    }

    return(
        <ContainerForEntity variant={entity.status ? statusEntity[entity.status] : ""} property={"pl-8 pt-2 pb-2 pr-4"}>
            <Container property={"grid grid-cols-5 gap-2 items-center"}>
                <Paragraph sizeTag="h4">{entity.logo}</Paragraph>
                <Paragraph variant={"baseBold"}>{entity.title}</Paragraph>
                <Paragraph>Datum podání: {entity.administration_date}</Paragraph>
                <Paragraph>Status: {entity.status}</Paragraph>
                {/* POKUD BUDE ZAMÍTNUTÁ, TAK NEBUDE MÍT IKONU */}

                <Container property={"flex flex-row gap-4 inline-block justify-end"}>
                    <Button noVariant={true} icon="eye" iconColor={"text-black"} iconSize={"24"} onClick={onView}></Button>
                    
                    {entity.status === "Pozvánka" && 
                        <Button noVariant={true} icon="gear" iconColor={"text-black"} iconSize={"24"} onClick={onClick}></Button>
                    }
                    </Container>

            </Container>
    </ContainerForEntity>
    )
}