import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import PopUpCon from "@core/Container/PopUpCon";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI";
import { useNavigate } from "react-router-dom";
import PraxeDepartmentEntity from "@components/Praxe/PraxeDepartmentEntity";
import { useUser } from "@hooks/UserProvider";

export default function SpravaStaziPage() {
    const [approved, setApproved] = useState([]);
    const [toApprove, setToApprove] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const nabidkaAPI = useNabidkaAPI();
    const navigate = useNavigate();
    const [showPop, setPop] = useState(false);
    const [selectedEntity, setSelectedEntity] = useState(null);
    const { user } = useUser();

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = user.isAdmin()
                ? await nabidkaAPI.getAdminPractices()
                : await nabidkaAPI.getNabidkyByUserDepartment();
            setApproved(res.approved_practices || []);
            setToApprove(res.to_approve_practices || []);
        } catch {
            setError("Nepodařilo se načíst stáže.");
            setApproved([]);
            setToApprove([]);
        } finally {
            setLoading(false);
        }
    };

    const handleApprove = async () => {
        if (!selectedEntity) return;

        const newStatus = {
            "approval_status": 1
        }

        await nabidkaAPI.changeStatus(selectedEntity.practice_id, newStatus);
        setPop(false);
        setSelectedEntity(null);
        fetchData();
    };


    const handleReject = async () => {
        if (!selectedEntity) return;
        const newStatus = {
            "approval_status": 2
        }
        await nabidkaAPI.changeStatus(selectedEntity.practice_id, newStatus);
        setPop(false);
        setSelectedEntity(null);
        fetchData();
    };


    const handleClosePop = () => {
        setPop(false);
        setSelectedEntity(null);
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleView = (type, entity) => {
        if (type === "approved_practices") {
            navigate(`/nabidka/${entity.practice_id}`)
        }
        if (type === "to_approve_practices") {
            navigate(`/nabidka/${entity.practice_id}`)
        }

    }

    const handleClick = (type, entity = null) => {
        if (type === "to_approve_practices") {
            setSelectedEntity(entity);
            setPop(true);
        }
        if (type === "approved_practices") {
            navigate(`/students/${entity?.practice_id}`);
        }
    };

    return(
        <>
            <BackButton/>

            <Container property={"flex items-center justify-between mb-6 mt-4"}>
                <Headings sizeTag={"h3"} property={"mt-2"}>
                    Probíhající stáže
                </Headings>
            </Container>

            {loading && (
                <Paragraph property="text-center text-gray-500 py-8">Načítání stáží...</Paragraph>
            )}

            {!loading && error && (
                <Paragraph property="text-center text-red-500 py-8">{error}</Paragraph>
            )}

            {!loading && !error && (
                <>
                    <Container property={"mb-8 space-y-4"}>
                        {approved.length === 0 ? (
                            <Paragraph property="text-center text-gray-500 py-8">
                                Žádné schválené stáže.
                            </Paragraph>
                        ) : (
                            approved.map((entity) => (
                                <PraxeDepartmentEntity
                                    key={entity.practice_id}
                                    entity={entity}
                                    type="approved"
                                    onView={() => handleView("approved_practices", entity)}
                                    onClick={() => handleClick("approved_practices", entity)}
                                />
                            ))
                        )}
                    </Container>

                    <Container property={"flex items-center justify-between mb-6 mt-4"}>
                        <Headings sizeTag={"h3"} property={"mt-2"}>
                            Schvalovací kolečko
                        </Headings>
                    </Container>

                    <Container property={"mt-4 mb-8 space-y-4"}>
                        {toApprove.length === 0 ? (
                            <Paragraph property="text-center text-gray-500 py-8">
                                Žádné stáže čekající na schválení.
                            </Paragraph>
                        ) : (
                            toApprove.map((entity) => (
                                <PraxeDepartmentEntity
                                    key={entity.practice_id}
                                    entity={entity}
                                    onView={() => handleView("to_approve_practices", entity)}
                                    onClick={() => handleClick("to_approve_practices", entity)}
                                    type="to_approve"
                                />
                            ))
                        )}
                    </Container>
                </>
            )}
            {showPop &&
                <PopUpCon
                    onClose={handleClosePop}
                    onSubmit={handleApprove}
                    onSubmitText={"Schválit"}
                    onReject={handleReject}
                    onRejectText={"Zamítnout"}
                    title="Opravdu chcete změnit stav nabídky?"
                    text={`Chcete změnit stav nabídky: ${selectedEntity?.title || ""}?`}
                />
            }
        </>
    )
}
