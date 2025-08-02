import React from "react";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Headings from "@core/Text/Headings";
import Container from "@core/Container/Container";
import Paragraph from "@components/core/Text/Paragraph";
import Button from "@core/Button/Button";

export default function PraxeDepartmentEntity({ type, entity, onClick, onView }) {

    const getContactName = (info) => {
        if (!info) return "Není uveden";
        if (info.username) return info.username;
        if (info.first_name && info.last_name) return `${info.first_name} ${info.last_name}`
        return "Není uveden";
    };

    const bg = type === "to_approve" ? "yellow" : "gray";
    const approved = entity.approved_applications ?? 0;
    const pending = entity.pending_applications ?? 0;
    const available = entity.available_positions ?? 0;
    const created = entity.created_at || entity.start_date || "-";
    const subjectCode = entity.subject?.subject_code || "-";

    return (
        <ContainerForEntity variant={bg} property={`pl-8 pt-4 pb-4 pr-4`} onClick={onView}>
            <Container property={"flex items-center justify-between"}>
            
                <Container property={"flex items-center gap-6 flex-1"}>
                    <Container property={"min-w-[200px]"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            Správce inzerátu
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {getContactName(entity.contact_user_info)}
                        </Paragraph>
                    </Container>
                    <Container property={"flex-1"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            Název stáže
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {entity.title || "-"}
                        </Paragraph>
                    </Container>
                    <Container property={"min-w-[100px] text-center"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            Kód předmětu
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {subjectCode}
                        </Paragraph>
                    </Container>
                    <Container property={"min-w-[180px] text-center"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            Datum vytvoření
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {created}
                        </Paragraph>
                    </Container>
                    <Container property={"min-w-[180px] text-center"}>
                        <Paragraph property={"text-sm text-gray-500 mb-1"}>
                            Podané přihlášky
                        </Paragraph>
                        <Paragraph property={"font-medium"}>
                            {type === "approved" ? `${approved}/${pending}/${available}` : ("- / - / - ")}
                        </Paragraph>
                    </Container>
                </Container>
                    {type === "approved" && (
                        <Container property={"flex items-center gap-4 ml-4"}>
                            <Button
                                noVariant={true}
                                onClick={(e) => { e.stopPropagation(); onClick(); }}
                                title="Zobrazit přihlášky"
                                icon="users"
                                iconColor={"gray"}
                                iconSize={"24"}
                            />
                            <Button
                                noVariant={true}
                                onClick={(e) => { e.stopPropagation(); onView(); }}
                                title="Zobrazit detail"
                                icon="eye"
                                iconColor={"gray"}
                                iconSize={"24"}
                            />
                        </Container>
                    )}
                    {type === "to_approve" && (
                        <Container property={"flex items-center gap-4 ml-4"}>
                            <Button
                                noVariant={true}
                                onClick={(e) => { e.stopPropagation(); onClick(); }}
                                title="Změnit stav nabídky"
                                icon="gear"
                                iconColor={"gray"}
                                iconSize={"24"}
                            />

                            <Button
                                noVariant={true}
                                onClick={(e) => { e.stopPropagation(); onView(); }}
                                title="Zobrazit detail"
                                icon="eye"
                                iconColor={"gray"}
                                iconSize={"24"}
                            />
                        </Container>
                    )}
            </Container>
        </ContainerForEntity>
    );
}