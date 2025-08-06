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
    
    const companyAPI = useCompanyAPI();
    const navigate = useNavigate();
    const { addMessage } = useMessage();

    const fetchCompanies = async () => {
        try {
            setLoading(true);
            const data = await companyAPI.getAllCompanies();
            setCompanies(data || []);
        } catch (error) {
            console.error("Chyba při načítání společností:", error);
            addMessage('Chyba při načítání společností', 'error');
            setCompanies([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchCompanies();
    }, []);

    const handleCreateCompany = () => {
        navigate('/formular?type=org_form&action=create');
    };

    const handleEditCompany = (company) => {
        navigate(`/formular?type=org_form&action=edit&id=${company.company_id}`);
    };

    const handleViewStages = (company) => {
        // Navigace na stránku se stážemi pro danou společnost
        navigate(`/praxe?company=${company.company_id}`);
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
                                    buttons={[
                                        {
                                            icon: "eye",
                                            btnfunction: () => handleViewStages(company)
                                        },
                                        {
                                            icon: "edit",
                                            btnfunction: () => handleEditCompany(company)
                                        }
                                    ]}
                                />
                            ))}
                        </Container>
                    )}
                </Container>
            </Container>


        </Container>
    );
} 