import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import Nav from "@components/core/Nav";
import PopUpCon from "@core/Container/PopUpCon";
import { useCompanyAPI } from "@api/company/companyAPI";
import { useNavigate } from "react-router-dom";
import { useMessage } from "@hooks/MessageContext";
import CompanyEntity from "@components/Company/CompanyEntity";

export default function CompaniesPage() {
    const [companies, setCompanies] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showDeletePop, setShowDeletePop] = useState(false);
    const [selectedCompany, setSelectedCompany] = useState(null);
    
    const companyAPI = useCompanyAPI();
    const navigate = useNavigate();
    const { showMessage } = useMessage();

    const fetchCompanies = async () => {
        try {
            setLoading(true);
            const data = await companyAPI.getAllCompanies();
            setCompanies(data || []);
        } catch (error) {
            console.error("Chyba při načítání společností:", error);
            showMessage('Chyba při načítání společností', 'error');
            setCompanies([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchCompanies();
    }, []);

    const handleCreateCompany = () => {
        navigate('/formular?type=company&action=create');
    };

    const handleEditCompany = (company) => {
        navigate(`/formular?type=company&action=edit&id=${company.company_id}`);
    };

    const handleDeleteClick = (company) => {
        setSelectedCompany(company);
        setShowDeletePop(true);
    };

    const handleDeleteConfirm = async () => {
        if (!selectedCompany) return;
        
        try {
            await companyAPI.deleteCompany(selectedCompany.company_id);
            showMessage('Společnost byla úspěšně smazána', 'success');
            setShowDeletePop(false);
            setSelectedCompany(null);
            fetchCompanies();
        } catch (error) {
            showMessage('Chyba při mazání společnosti', 'error');
        }
    };

    const handleDeleteCancel = () => {
        setShowDeletePop(false);
        setSelectedCompany(null);
    };

    return (
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <BackButton/>
                
                <Container property={"flex items-center justify-between mb-6 mt-4"}>
                    <Headings sizeTag={"h3"} property={"mt-2"}>
                        Správa společností
                    </Headings>
                </Container>

                <Container>
                    <Button 
                        onClick={handleCreateCompany}
                        icon={"plus"}
                    >
                        Přidat společnost
                    </Button>
                </Container>

                <Container property={"mt-4 rounded-lg"}>
                    {loading ? (
                        <Paragraph>Načítání...</Paragraph>
                    ) : companies.length === 0 ? (
                        <Paragraph property="text-center text-gray-500 py-8">
                            Zatím nejsou žádné společnosti k zobrazení.
                        </Paragraph>
                    ) : (
                        <Container property={"grid grid-cols-1 gap-4"}>
                            {companies.map(company => (
                                <CompanyEntity
                                    key={company.company_id}
                                    entity={company}
                                    onClick={() => handleEditCompany(company)}
                                    buttons={[
                                        {
                                            icon: "edit",
                                            btnfunction: () => handleEditCompany(company)
                                        },
                                        {
                                            icon: "cross",
                                            btnfunction: () => handleDeleteClick(company)
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
                    text={`Opravdu chcete smazat společnost "${selectedCompany?.company_name}"? Tato akce je nevratná.`}
                    onSubmit={handleDeleteConfirm}
                    onReject={handleDeleteCancel}
                    onSubmitText="Smazat"
                    onRejectText="Zrušit"
                />
            )}
        </Container>
    );
} 