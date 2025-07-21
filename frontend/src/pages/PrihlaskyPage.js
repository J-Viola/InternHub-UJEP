import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import Nav from "@components/core/Nav";
import { useParams } from "react-router-dom";
import { useStudentPracticeAPI } from "@api/student_practice/student_pracitceAPI";
import PrihlaskaEntity from "@components/Prihlasky/PrihlaskaEntity";
import PopUpCon from "@core/Container/PopUpCon";

export default function PrihlaskyPage() {
    const [data, setData] = useState([])
    const [showPopup, setShowPopup] = useState(false);
    const [selectedEntity, setSelectedEntity] = useState(null);
    const studentpracticeAPI = useStudentPracticeAPI();

    const onSettings = (en) => {
        setSelectedEntity(en);
        setShowPopup(true);
    }

    const onProfile = (en) => {
        console.log("Profil", en)
    }

    const handleClosePopup = () => {
        setShowPopup(false);
        setSelectedEntity(null);
    }

    const handleSubmit = async () => {
        if (!selectedEntity) return;
        try {
            await studentpracticeAPI.updateStudentPracticeStatus(selectedEntity.student_practice_id, "approve");
            setShowPopup(false);
            setSelectedEntity(null);
            // Refresh data
            const res = await studentpracticeAPI.getOrganizationApplications();
            setData(res);
        } catch (error) {
            // případně zobrazit error toast
        }
    }

    const handleReject = async () => {
        if (!selectedEntity) return;
        try {
            await studentpracticeAPI.updateStudentPracticeStatus(selectedEntity.student_practice_id, "reject");
            setShowPopup(false);
            setSelectedEntity(null);
            // Refresh data
            const res = await studentpracticeAPI.getOrganizationApplications();
            setData(res);
        } catch (error) {
            // případně zobrazit error toast
        }
    }

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await studentpracticeAPI.getOrganizationApplications();
                setData(res);
            } catch (error) {
                setData([]);
            }
        };
        fetchData();
    }, []);

    return(
    <Container property="min-h-screen">
        <Nav/>
        <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
            <BackButton/>
            <Container property={"flex items-center justify-between mb-6 mt-4"}>
                <Headings sizeTag={"h3"} property={"mt-2"}>
                    Nevyřízené přihlášky
                </Headings>
            </Container>

            <Container property={"mt-4 rounded-lg"}>
                {!data ? (
                    <Paragraph>Načítání...</Paragraph>
                ) : data.length === 0 ? (
                    <Paragraph property="text-center text-gray-500 py-8">
                        Zatím nemáte žádné data k zobrazení.
                    </Paragraph>
                ) : (
                    <Container property={"grid grid-cols-1 gap-4"}>
                        {data.map((entity) => (
                            <PrihlaskaEntity
                                key={entity.student_practice_id}
                                entity={entity}
                                onSettings={onSettings}
                                onProfile={onProfile}
                            />
                        ))}
                    </Container>
                )}
            </Container>
        </Container>
        {showPopup && selectedEntity && (
            <PopUpCon
                onClose={handleClosePopup}
                title={"Změnit stav přihlášky"}
                text={`Opravdu si přejete změnit stav přihlášky studenta ${selectedEntity.student_full_name}?`}
                onSubmit={handleSubmit}
                onReject={handleReject}
                variant="gray"
            />
        )}
    </Container>
    )
}