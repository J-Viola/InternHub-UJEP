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

export default function UserEntity({entity, attributes, buttons, status="gray", onClick, statusView = true}) {

    const getStatusColor = (status) => {
        switch (status) {
            case "PENDING":
                return "text-yellow-600";
            case "APPROVED":
                return "text-green-600";
            case "REJECTED":
                return "text-red-600";
            case "IN_PROGRESS":
                return "text-blue-600";
            case "COMPLETED":
                return "text-green-600";
            case "CANCELLED":
                return "text-red-600";
            default:
                return "text-gray-500";
        }
    }

    // projdi mi seznamy z attributes
    const getNestedValue = (obj, path) => {
        if (!path) return obj;
        try {
            const normalized = path.replace(/\[(\w+)\]/g, ".$1").replace(/^\./, "");
            const parts = normalized.split(".");
            let current = obj;
            for (const part of parts) {
                if (current == null) return undefined;
                current = current[part];
            }
            return current;
        } catch (e) {
            return undefined;
        }
    };

    return (
        <ContainerForEntity id={`user-entity-${entity.user_id}`} variant={status} property={"pl-8 pt-4 pb-4 pr-4 mt-2"} onClick={onClick}>
            <Container property="flex flex-row items-center gap-8 w-full">
                {/* Jméno */}
                <Container property="flex-shrink-0 min-w-[200px]">
                    <Paragraph variant={"baseBold"}>
                        {entity.student_full_name
                            ? entity.student_full_name
                            : (entity.first_name && entity.last_name
                                ? `${entity.first_name} ${entity.last_name}`
                                : (entity.titles || entity.surname
                                    ? `${entity.titles?.before || ''} ${entity.name || ''} ${entity.surname || ''} ${entity.titles?.after || ''}`.trim()
                                    : entity.name))
                        }
                    </Paragraph>
                </Container>
                {/* Atributy */}
                <Container property="flex-1 flex flex-row flex-wrap gap-x-12 gap-y-2 items-center">
                    {Object.entries(attributes).map(([key, value]) => {
                        // Speciální zpracování pro workflow_status
                        if (statusView && value === "workflow_status") {
                            const workflowStatus = entity.workflow_status || (entity.student_practice && entity.student_practice.workflow_status);
                            const workflowLabel = entity.workflow_status_label || (entity.student_practice && entity.student_practice.workflow_status_label);

                            return (
                                <Container key={key} property="min-w-[120px]">
                                    <Paragraph>
                                        <span>{key}: </span>
                                        <span className={getStatusColor(workflowStatus)}>{workflowLabel || "------"}</span>
                                    </Paragraph>
                                </Container>
                            );
                        }

                        const renderedValue = getNestedValue(entity, value);
                        return (
                            <Container key={key} property="min-w-[120px]">
                                {key !=="" ? <Paragraph>{key}: {renderedValue ?? ""}</Paragraph> : <Paragraph>{renderedValue ?? ""}</Paragraph>}
                            </Container>
                        );
                    })}

                </Container>
                {/* Tlačítka */}
                <Container property="flex flex-row gap-4 justify-end flex-shrink-0">
                    {buttons.map((btn, index) => (
                        <Button
                            key={index}
                            icon={btn.icon}
                            title={btn.title}
                            noVariant={true}
                            iconColor={btn.iconColor || "text-black"}
                            iconSize={btn.iconSize || "28"}
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
