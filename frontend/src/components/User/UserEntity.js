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

export default function UserEntity({entity, attributes, buttons, status="gray", onClick}) {

    const renderProgressStatus = (progress_status) => {
        if (progress_status == 0) {
            return { text: "Neproběhla", color: "text-red-600" }
        }
        if (progress_status == 1) {
            return { text: "Proběhla", color: "text-green-600" }
        }
        else {
            return { text: "------", color: "text-gray-500" }
        }
    }

    const renderApprovalStatus = (approval_status) => {
        if (approval_status == 0) {
            return { text: "Čeká na schválení", color: "text-yellow-600" }
        }
        if (approval_status == 1) {
            return { text: "Schváleno", color: "text-green-600" }
        }
        if (approval_status == 2) {
            return { text: "Zamítnuto", color: "text-red-600" }
        }
        else {
            return { text: "------", color: "text-gray-500" }
        }
    }

    return (
        <ContainerForEntity variant={status} property={"pl-8 pt-4 pb-4 pr-4 mt-2"} onClick={onClick}>
            <Container property="flex flex-row items-center gap-8 w-full">
                {/* Jméno */}
                <Container property="flex-shrink-0 min-w-[200px]">
                    <Paragraph variant={"baseBold"}>
                        {entity.student_full_name
                            ? entity.student_full_name
                            : (entity.titles || entity.surname
                                ? `${entity.titles?.before || ''} ${entity.name || ''} ${entity.surname || ''} ${entity.titles?.after || ''}`.trim()
                                : entity.name)
                        }
                    </Paragraph>
                </Container>
                {/* Atributy */}
                <Container property="flex-1 flex flex-row flex-wrap gap-x-12 gap-y-2 items-center">
                    {Object.entries(attributes).map(([key, value]) => {
                        // Speciální zpracování pro approval_status
                        if (value === "approval_status") {
                            const approvalStatus = renderApprovalStatus(entity[value]);
                            return (
                                <Container key={key} property="min-w-[120px]">
                                    <Paragraph>
                                        <span>{key}: </span>
                                        <span className={approvalStatus.color}>{approvalStatus.text}</span>
                                    </Paragraph>
                                </Container>
                            );
                        }
                        
                        return (
                            <Container key={key} property="min-w-[120px]">
                                {key !=="" ? <Paragraph>{key}: {entity[value]}</Paragraph> : <Paragraph>{entity[value]}</Paragraph>}                            
                            </Container>
                        );
                    })}

                    <Container property="min-w-[120px]">
                        {(() => {
                            const status = renderProgressStatus(entity?.student_practice?.progress_status ?? entity?.progress_status);
                            return (
                                <Paragraph>
                                    <span>Kontrola: </span>
                                    <span className={status.color}>{status.text}</span>
                                </Paragraph>
                            );
                        })()}                      
                    </Container>

                </Container>
                {/* Tlačítka */}
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