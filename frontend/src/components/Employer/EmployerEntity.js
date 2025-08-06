import React from "react";
import Button from "@core/Button/Button";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Paragraph from "@components/core/Text/Paragraph";

export default function EmployerEntity({entity, buttons, onClick}) {
    return (
        <ContainerForEntity variant="gray" property={"pl-8 pt-4 pb-4 pr-4 mt-2"} onClick={onClick}>
            <Container property="flex flex-row items-center gap-8 w-full">
                <Container property="flex-shrink-0 min-w-[250px]">
                    <Paragraph variant={"baseBold"}>
                        {entity.employer_name}
                    </Paragraph>
                </Container>
                <Container property="min-w-[100px]">
                    <Paragraph>
                        IČO: {entity.ico}
                    </Paragraph>
                </Container>
                <Container property="flex-1">
                    <Paragraph>
                        {entity.address}
                    </Paragraph>
                </Container>
                <Container property="flex flex-row gap-4 justify-end flex-shrink-0">
                    {buttons.map(btn => (
                        <Button 
                            key={btn.icon}
                            noVariant={true} 
                            icon={btn.icon} 
                            iconColor={"text-black"} 
                            iconSize={"24"} 
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