import React from "react";
import Button from "@core/Button/Button";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Paragraph from "@components/core/Text/Paragraph";
import Headings from "@core/Text/Headings";

export default function PozvankyEntity({entity, onCancel, onView}) {
    return (
        <ContainerForEntity variant="gray" property={"pl-8 pt-4 pb-4 pr-4 mt-2"}>
            <Container property="flex flex-row items-center gap-8 w-full">
                {/* Adresát */}
                <Container property="flex-shrink-0 min-w-[200px]">
                    <Paragraph variant={"baseBold"}>
                        {entity.recipient_name || `${entity.recipient_first_name || ''} ${entity.recipient_last_name || ''}`.trim()}
                    </Paragraph>
                </Container>
                
                {/* Atributy */}
                <Container property="flex-1 flex flex-row items-center gap-8">
                    <Container property="min-w-[120px]">
                        <Paragraph>
                            {entity.department || entity.recipient_department || 'Neznámá'}
                        </Paragraph>
                    </Container>
                    
                    <Container property="min-w-[120px]">
                        <Paragraph>
                            {entity.project_title || entity.practice_title || 'Neznámá'}
                        </Paragraph>
                    </Container>
                </Container>
                
                {/* Tlačítka */}
                <Container property="flex flex-row gap-4 justify-end flex-shrink-0">
                    <Button
                        variant="red"
                        onClick={(e) => {
                            e.stopPropagation();
                            if (onCancel) {
                                onCancel(entity);
                            }
                        }}
                        property="px-4 py-2"
                    >
                        Zrušit zaslání
                    </Button>
                    
                    <Button
                        noVariant={true}
                        icon="user"
                        iconColor="text-black"
                        iconSize="24"
                        onClick={(e) => {
                            e.stopPropagation();
                            if (onView) {
                                onView(entity.id);
                            }
                        }}
                    />
                </Container>
            </Container>
        </ContainerForEntity>
    )
}
