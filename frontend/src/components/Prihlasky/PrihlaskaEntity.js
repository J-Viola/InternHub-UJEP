import React from "react";
import Button from "@core/Button/Button";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";

export default function ApplicationEntity({ entity, onSettings, onProfile, onClick }) {
    return (
        <ContainerForEntity
            variant="yellow"
            property="flex flex-row items-center gap-4 w-full bg-yellow-50 border rounded-xl px-6 py-3 mt-2"
            onClick={(e) => {
                e.stopPropagation();
                onClick && onClick(entity);
            }}
        >
            {/* Jméno studenta */}
            <Container property="flex-shrink-0 min-w-[180px]">
                {entity.student_full_name}
            </Container>
            {/* Katedra */}
            <Container property="flex-shrink-0 min-w-[200px] text-center">
                {entity.department_name}
            </Container>
            {/* Název praxe */}
            <Container property="flex-1 truncate">
                {entity.practice_title}
            </Container>
            {/* Akční tlačítka */}
            <Container property="flex flex-row gap-2 ml-4">
                <Button
                    icon="manage"
                    noVariant={true}
                    iconColor="text-black"
                    iconSize="28"
                    onClick={(e) => {
                        e.stopPropagation();
                        onSettings && onSettings(entity);
                    }}
                />
                <Button
                    icon="user"
                    noVariant={true}
                    iconColor="text-black"
                    iconSize="28"
                    onClick={(e) => {
                        e.stopPropagation();
                        onProfile && onProfile(entity);
                    }}
                />
            </Container>
        </ContainerForEntity>
    );
}
