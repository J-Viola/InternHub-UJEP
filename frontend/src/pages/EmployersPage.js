import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import Nav from "@components/core/Nav";
import PopUpCon from "@core/Container/PopUpCon";
import { useEmployerAPI } from "@api/employer/employerAPI";
import { useNavigate } from "react-router-dom";
import { useMessage } from "@hooks/MessageContext";
import EmployerEntity from "@components/Employer/EmployerEntity";

export default function EmployersPage() {
    const [employers, setEmployers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showDeletePop, setShowDeletePop] = useState(false);
    const [selectedEmployer, setSelectedEmployer] = useState(null);
    
    const employerAPI = useEmployerAPI();
    const navigate = useNavigate();
    const { showMessage } = useMessage();

    const fetchEmployers = async () => {
        try {
            setLoading(true);
            const data = await employerAPI.getAllEmployers();
            setEmployers(data || []);
        } catch (error) {
            console.error("Chyba při načítání zaměstnavatelů:", error);
            showMessage('Chyba při načítání zaměstnavatelů', 'error');
            setEmployers([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchEmployers();
    }, []);

    const handleCreateEmployer = () => {
        navigate('/formular?type=org_form&action=create');
    };

    const handleEditEmployer = (employer) => {
        navigate(`/formular?type=org_form&action=edit&id=${employer.employer_id}`);
    };

    const handleDeleteClick = (employer) => {
        setSelectedEmployer(employer);
        setShowDeletePop(true);
    };

    const handleDeleteConfirm = async () => {
        if (!selectedEmployer) return;
        
        try {
            await employerAPI.deleteEmployer(selectedEmployer.employer_id);
            showMessage('Zaměstnavatel byl úspěšně smazán', 'success');
            setShowDeletePop(false);
            setSelectedEmployer(null);
            fetchEmployers();
        } catch (error) {
            showMessage('Chyba při mazání zaměstnavatele', 'error');
        }
    };

    const handleDeleteCancel = () => {
        setShowDeletePop(false);
        setSelectedEmployer(null);
    };

    return (
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <BackButton/>
                
                <Container property={"flex items-center justify-between mb-6 mt-4"}>
                    <Headings sizeTag={"h3"} property={"mt-2"}>
                        Správa zaměstnavatelů
                    </Headings>
                </Container>

                <Container>
                    <Button 
                        onClick={handleCreateEmployer}
                        icon={"plus"}
                    >
                        Přidat zaměstnavatele
                    </Button>
                </Container>

                <Container property={"mt-4 rounded-lg"}>
                    {loading ? (
                        <Paragraph>Načítání...</Paragraph>
                    ) : employers.length === 0 ? (
                        <Paragraph property="text-center text-gray-500 py-8">
                            Zatím nejsou žádní zaměstnavatelé k zobrazení.
                        </Paragraph>
                    ) : (
                        <Container property={"grid grid-cols-1 gap-4"}>
                            {employers.map(employer => (
                                <EmployerEntity
                                    key={employer.employer_id}
                                    entity={employer}
                                    onClick={() => handleEditEmployer(employer)}
                                    buttons={[
                                        {
                                            icon: "edit",
                                            btnfunction: () => handleEditEmployer(employer)
                                        },
                                        {
                                            icon: "cross",
                                            btnfunction: () => handleDeleteClick(employer)
                                        }
                                    ]}
                                />
                            ))}
                        </Container>
                    )}
                </Container>
            </Container>

            {/* Popup pro potvrzení smazání */}
            {showDeletePop && (
                <PopUpCon 
                    onClose={handleDeleteCancel}
                    title="Potvrdit smazání"
                    text={`Opravdu chcete smazat zaměstnavatele "${selectedEmployer?.employer_name}"? Tato akce je nevratná.`}
                    onSubmit={handleDeleteConfirm}
                    onReject={handleDeleteCancel}
                    onSubmitText="Smazat"
                    onRejectText="Zrušit"
                />
            )}
        </Container>
    );
} 