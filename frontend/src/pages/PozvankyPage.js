import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import BackButton from "@core/Button/BackButton";
import Button from "@core/Button/Button";
import { useNabidkaAPI } from "src/api/nabidka/nabidkaAPI";
import { useNavigate, useSearchParams } from "react-router-dom";
import Paragraph from "@components/core/Text/Paragraph";
import { useUser } from "@hooks/UserProvider";
import NabidkaEntityInline from "@components/Nabidka/NabidkaEntityInline";
import PopUpCon from "@core/Container/PopUpCon";
import { useStudentPracticeAPI } from "src/api/student_practice/student_practiceAPI";
import { useMessage } from "@hooks/MessageContext";

export default function InvitationPage() {
    const [searchParams] = useSearchParams();
    const [nabidky, setNabidky] = useState([]);
    const [selectedNabidka, setSelectedNabidka] = useState(null);
    const [showConfirmPopup, setShowConfirmPopup] = useState(false);
    const { getOrganizationPractices } = useNabidkaAPI();
    const { createInvitation } = useStudentPracticeAPI();
    const { user } = useUser();
    const { addMessage } = useMessage();
    const navigate = useNavigate();

    useEffect(() => {
        const type = searchParams.get('type');
        const id = searchParams.get('id');
        console.log('Type:', type);
        console.log('ID:', id);

        if (type === 'create' && id) {
            const studentIds = id.split(',').map(id => parseInt(id.trim()));
            console.log('Vybraní studenti:', studentIds);

            // Načíst nabídky organizace
            if (user.isOrganizationUser()) {
                getOrganizationPractices().then(res => {
                    console.log('Načtené nabídky:', res);
                    setNabidky(res || []);
                }).catch(error => {
                    console.error('Chyba při načítání nabídek:', error);
                });
            }
        }
    }, [searchParams, user]);



    const type = searchParams.get('type');
    const id = searchParams.get('id');
    const names = searchParams.get('names');
    const studentIds = id ? id.split(',').map(id => parseInt(id.trim())) : [];
    const studentNames = names ? names.split(',') : [];

    const handleSelectNabidka = (nabidka) => {
        if (selectedNabidka?.practice_id === nabidka.practice_id) {
            // Odebrat ze seznamu
            setSelectedNabidka(null);
            console.log('Odebrána nabídka:', nabidka);
        } else {
            // Přidat do seznamu
            setSelectedNabidka(nabidka);
            console.log('Vybraná nabídka:', nabidka);
        }
    };

    const handleViewNabidka = (nabidka) => {
        console.log('Zobrazit nabídku:', nabidka);
        navigate(`/nabidka/${nabidka.practice_id}`);
    };

    const handleCreateInvitation = () => {
        setShowConfirmPopup(true);
    };

    const handleConfirmCreate = async () => {
        console.log('Vytvořit pozvánku pro:', selectedNabidka, 'a studenty:', studentIds);

        if (!selectedNabidka || studentIds.length === 0) return;

        try {
            const res = await createInvitation(selectedNabidka.practice_id, studentIds);
            if (res) {
                addMessage(`Pozvánka pro ${res.created} studentů vytvořena.`, "S");
                if (res.errors && res.errors.length > 0) {
                    addMessage(`Chyby: ${res.errors.join(", ")}`, "E");
                }
                setShowConfirmPopup(false);
                navigate('/pozvanky-list');
            }
        } catch (error) {
            console.error("Chyba při vytváření pozvánky:", error);
            addMessage("Chyba při vytváření pozvánky: " + (error.response?.data?.detail || error.message), "E");
            setShowConfirmPopup(false);
        }
    };

    const handleCancelCreate = () => {
        setShowConfirmPopup(false);
    };

    return(
        <>
            <BackButton/>
            <Container property={"flex items-center justify-between mb-6 mt-4"}>
                <Headings sizeTag={"h3"} property={"mt-2"}>
                    {type === 'create' ? 'Vytvořit pozvánku' : 'Pozvánka'}
                </Headings>
            </Container>
            <Container property={"mb-4"}>
                {type === 'create' && (
                    <Button
                        onClick={handleCreateInvitation}
                        icon={"user-plus"}
                        disabled={!selectedNabidka}
                    >
                        Vytvořit pozvánku
                    </Button>
                )}
            </Container>

            {type === 'create' && studentIds.length > 0 && (
                <Container property={"bg-facultyColLight mt-2 p-4 rounded-lg border border-black"}>
                    <Paragraph variant="baseBold" property="mb-2">
                        Vybraní studenti ({studentIds.length}):
                    </Paragraph>
                    <Container property="space-y-1">
                        {studentNames.length > 0 ? (
                            studentNames.map((name, index) => (
                                <Paragraph key={index} property="text-sm">
                                    • {name}
                                </Paragraph>
                            ))
                        ) : (
                            <Paragraph property="text-sm text-gray-600">
                                ID studentů: {studentIds.join(', ')}
                            </Paragraph>
                        )}
                    </Container>
                </Container>
            )}

            {type === 'create' && studentIds.length > 0 && (
                <Container property={"mt-4 p-6 rounded-lg border border-black"}>
                    <Headings sizeTag={"h4"} property={"mb-4"}>
                        Vyberte, na jakou stáž má být pozvánka vázána
                    </Headings>

                    {nabidky.length > 0 ? (
                        <Container property={"space-y-3"}>
                            {nabidky.map((nabidka) => (
                                <NabidkaEntityInline
                                    key={nabidka.practice_id}
                                    entity={nabidka}
                                    isSelected={selectedNabidka?.practice_id === nabidka.practice_id}
                                    onClick={() => handleSelectNabidka(nabidka)}
                                    onView={() => handleViewNabidka(nabidka)}
                                />
                            ))}
                        </Container>
                    ) : (
                        <Container property={"bg-gray-50 p-4 rounded-lg"}>
                            <Paragraph>Načítání nabídek...</Paragraph>
                        </Container>
                    )}
                </Container>
            )}

            {(!type || !id) && (
                <Container property={"bg-gray-50 mt-2 p-4 rounded-lg"}>
                    <Paragraph>Žádné parametry pro vytvoření pozvánky.</Paragraph>
                </Container>
            )}

            {showConfirmPopup && (
                <PopUpCon
                    title="Potvrzení vytvoření pozvánky"
                    text={`Opravdu chcete vytvořit pozvánku pro ${studentNames.length > 0 ? studentNames.length : studentIds.length} studentů na stáž ${selectedNabidka?.title}?`}
                    onSubmit={handleConfirmCreate}
                    onReject={handleCancelCreate}
                    onClose={handleCancelCreate}
                    onSubmitText="Vytvořit"
                    onRejectText="Zrušit"
                    variant="blue"
                />
            )}
        </>
    )
}
