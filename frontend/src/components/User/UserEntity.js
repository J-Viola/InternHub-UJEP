import React from "react";
import Button from "@core/Button/Button";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Paragraph from "@components/core/Text/Paragraph";
import { useTranslation } from "react-i18next";

export default function UserEntity({entity, attributes, buttons, status="gray", onClick, statusView = true}) {
    const { t } = useTranslation();

    const getStatusColor = (status) => {
        switch (status) {
            case "PENDING":
                return "text-yellow-600";
            case "APPROVED":
                return "text-[#10b981]";
            case "REJECTED":
                return "text-[#ef4444]";
            case "IN_PROGRESS":
                return "text-blue-600";
            case "COMPLETED":
                return "text-[#10b981]";
            case "CANCELLED":
                return "text-[#ef4444]";
            default:
                return "text-gray-500";
        }
    }

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

    const getFullName = () => {
        if (entity.student_full_name) return entity.student_full_name;
        if (entity.first_name && entity.last_name) return `${entity.first_name} ${entity.last_name}`;
        if (entity.name && entity.surname) return `${entity.titles?.before || ''} ${entity.name} ${entity.surname} ${entity.titles?.after || ''}`.trim();
        return entity.name || entity.username || "---";
    };

    return (
        <ContainerForEntity 
            id={`user-entity-${entity.user_id}`} 
            variant={status} 
            property={"pl-8 pr-8 py-4 mt-2 border border-black bg-[#f9fafb] rounded-[10px] shadow-none"} 
            onClick={onClick}
        >
            <Container property="grid grid-cols-4 gap-4 items-center w-full">
                {/* Column 1: Name (Regular) */}
                <Container property="text-left">
                    <Paragraph property="font-normal text-black text-base">
                        {getFullName()}
                    </Paragraph>
                </Container>

                {/* Column 2: Department (Bold) */}
                <Container property="text-center">
                    <Paragraph property="font-bold text-black text-base">
                        {entity.department || "Katedra informatiky"}
                    </Paragraph>
                </Container>

                {/* Column 3: Status (Bold colored) */}
                <Container property="text-center">
                    {statusView && (
                        <p className="font-bold text-base text-black">
                            <span>Kontrola: </span>
                            <span className={getStatusColor(entity.workflow_status || "PENDING")}>
                                {(entity.workflow_status === "APPROVED" || entity.workflow_status === "COMPLETED") ? "PROBĚHLA" : "NEPROBĚHLA"}
                            </span>
                        </p>
                    )}
                </Container>

                {/* Column 4: Icons (Right) */}
                <Container property="flex flex-row gap-4 justify-end items-center">
                    {buttons.map((btn, index) => (
                        <Button
                            key={index}
                            icon={btn.icon}
                            title={btn.title}
                            noVariant={true}
                            iconColor={btn.iconColor || "text-black"}
                            iconSize={btn.iconSize || "32"}
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
