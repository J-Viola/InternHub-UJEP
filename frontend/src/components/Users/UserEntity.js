// zde bude entity pro jakéhokoliv uživatele v systému, které budou mít společné vlastnosti
// -> tlačítka a na ně akce
// -> parametr co vykreslit
// -> parametr na barvu pozadí (podle stavu entity)
import React from "react";
import Button from "@core/Button/Button";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Paragraph from "@components/core/Text/Paragraph";
import Headings from "@core/Text/Headings";

export default function UserEntity({entity, attributes, buttons, status="gray"}) {

    return (
        <ContainerForEntity variant={status} property={"pl-8 pt-2 pb-2 pr-4 mt-2"}>
            <Container property="flex flex-row gap-8 items-center">
                <Container property="w-64">
                    <Paragraph variant={"baseBold"}>
                        {entity.titles?.before} {entity.name} {entity.surname} {entity.titles?.after}
                    </Paragraph>
                </Container>
                
                <Container property="flex-1 flex flex-row gap-12 items-center">
                    {Object.entries(attributes).map(([key, value]) => (
                        <Container key={key} property="w-32">
                        {key !=="" ? <Paragraph>{key}: {entity[value]}</Paragraph> : <Paragraph>{entity[value]}</Paragraph>}                            
                        </Container>
                    ))}
                </Container>

                <Container property="flex flex-row gap-4 justify-end">
                    {buttons.map(btn => (
                        <Button 
                            key={btn.icon}
                            noVariant={true} 
                            icon={btn.icon} 
                            iconColor={"text-black"} 
                            iconSize={"24"} 
                            onClick={btn.btnfunction}
                        />
                    ))}
                </Container>
            </Container>
        </ContainerForEntity>
    )
}