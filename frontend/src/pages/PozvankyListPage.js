import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import Nav from "@components/core/Nav";
import { useParams, useNavigate } from "react-router-dom";
import PozvankyEntity from "@components/Pozvanky/PozvankyEntity";
import PopUpCon from "@core/Container/PopUpCon";
import { usePozvankyAPI } from "@api/pozvanky/pozvankyAPI";

export default function PozvankyListPage() {
    const navigate = useNavigate();
    const { getPozvankyList } = usePozvankyAPI();
    const [showPopup, setShowPopup] = useState(false);
    const [selectedEntity, setSelectedEntity] = useState(null);
    const [data, setData] = useState([]);
    const [loading, setLoading] = useState(true);


    const handleCancelInvitation = (entity) => {
        setSelectedEntity(entity);
        setShowPopup(true);
    }

    const handleConfirmCancel = async () => {
        if (!selectedEntity) return;
        try {
            // TODO: Implementovat API volání pro zrušení pozvánky
            console.log('Zrušit pozvánku:', selectedEntity);
            
            // Odebrat z listu
            setData(prevData => prevData.filter(item => item.id !== selectedEntity.id));
            
            setShowPopup(false);
            setSelectedEntity(null);
        } catch (error) {
            console.error('Chyba při zrušení pozvánky:', error);
        }
    }

    const handleClosePopup = () => {
        setShowPopup(false);
        setSelectedEntity(null);
    }

    const handleViewProfile = (userId) => {
        console.log('Zobrazit profil uživatele:', userId);
        navigate(`/profil/${userId}`);
    }

    useEffect(() => {
        const initFetch = async () => {
            try {
                setLoading(true);
                const pozvankyData = await getPozvankyList();
                setData(pozvankyData);
            } catch (error) {
                console.error('Chyba při načítání pozvánek:', error);
            } finally {
                setLoading(false);
            }
        };

        initFetch();
    }, []);

    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <BackButton/>
                <Container property={"flex items-center justify-between mb-6 mt-4"}>
                    <Headings sizeTag={"h3"} property={"mt-2"}>
                        Zaslané pozvánky
                    </Headings>
                </Container>
                <Paragraph>Tato stránka obsahuje pouze dummy data.</Paragraph>

                <Container property={"mt-4 rounded-lg"}>
                    {loading ? (
                        <Paragraph>Načítání...</Paragraph>
                    ) : data.length === 0 ? (
                        <Paragraph property="text-center text-gray-500 py-8">
                            Zatím nemáte žádné zaslané pozvánky.
                        </Paragraph>
                    ) : (
                        <Container property={"grid grid-cols-1 gap-4"}>
                            {data.map((entity) => (
                                <PozvankyEntity
                                    key={entity.id}
                                    entity={entity}
                                    onCancel={handleCancelInvitation}
                                    onView={handleViewProfile}
                                />
                            ))}
                        </Container>
                    )}
                </Container>
            </Container>

            {/* Popup pro potvrzení zrušení pozvánky */}
            {showPopup && (
                <PopUpCon
                    title="Potvrzení zrušení pozvánky"
                    text={`Opravdu chcete zrušit pozvánku pro ${selectedEntity?.recipient_name} na projekt "${selectedEntity?.project_title}"?`}
                    onSubmit={handleConfirmCancel}
                    onReject={handleClosePopup}
                    onClose={handleClosePopup}
                    onSubmitText="Ano"
                    onRejectText="Ne"
                />
            )}
        </Container>
    )
}
