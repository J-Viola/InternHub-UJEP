import React, { useEffect, useState } from "react";
import Container from "@core/Container/Container";
import SubjectEntity from "@components/Subjects/SubjectEntity";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import BackButton from "@core/Button/BackButton";
import { useSubjectAPI } from "@api/subject/subjectAPI";
import { useNavigate } from "react-router-dom";
import Button from "@components/core/Button/Button";

export default function SubjectPage() {
    const [entities, setEntities] = useState([]);
    const [loading, setLoading] = useState(true);
    const { getDepartmentSubjects } = useSubjectAPI();
    const navigate = useNavigate();

    useEffect(() => {
        loadSubjects();
    }, []);

    const loadSubjects = async () => {
        try {
            setLoading(true);
            const subjects = await getDepartmentSubjects();
            setEntities(subjects);
        } catch (error) {
            console.error("Chyba při načítání předmětů:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleEditSubject = (subjectId) => {
        navigate(`/formular?type=subject&action=edit&id=${subjectId}`)
    };

    const handleCreateSubject = () => {
        navigate("/formular?type=subject&action=create")
    };

    // Bezpečné získání názvu katedry
    const getDepartmentName = () => {
        if (entities && entities.length > 0 && entities[0].department) {
            return entities[0].department.department_name;
        }
        return "";
    };

    return(
        <>
            <BackButton/>
            <Container property={"flex items-center justify-between mb-6 mt-4"}>
                <Headings sizeTag={"h3"} property={"mt-2"}>
                    Předměty {getDepartmentName() && `- ${getDepartmentName()}`}
                </Headings>
            </Container>

            <Container property={"flex items-center justify-between mb-6"}>
                <Button
                    variant={"primarySmall"}
                    icon={"plus"}
                    onClick={handleCreateSubject}
                    text={"Založit předmět"}
                />
            </Container>

            {/* PŘEDMĚTY */}
            <Container property={"mt-4"}>
                {loading ? (
                    <Container property="flex justify-center items-center py-8">
                        <Paragraph>Načítání předmětů...</Paragraph>
                    </Container>
                ) : entities.length === 0 ? (
                    <Container property="flex justify-center items-center py-8">
                        <Paragraph>Žádné předměty nebyly nalezeny</Paragraph>
                    </Container>
                ) : (
                    entities.map((entity) => (
                        <SubjectEntity
                            key={entity.subject_id}
                            entity={entity}
                            attributes={{
                                "Počet hodin": "hours_required"
                            }}
                            buttons={[
                                {
                                    icon: "edit",
                                    btnfunction: () => handleEditSubject(entity.subject_id)
                                }
                            ]}
                            onClick={() => handleEditSubject(entity.subject_id)}
                        />
                    ))
                )}
            </Container>
        </>
    )
}
