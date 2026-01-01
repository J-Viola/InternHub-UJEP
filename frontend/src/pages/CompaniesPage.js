import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import { useCompanyAPI } from "@api/company/companyAPI";
import { useNavigate } from "react-router-dom";
import { useMessage } from "@hooks/MessageContext";
import CompanyEntity from "@components/Company/CompanyEntity";
import { useTranslation } from "react-i18next";

export default function CompaniesPage() {
    const { t } = useTranslation();
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
            console.error(t('companies.load_error'), error);
            addMessage(t('companies.load_error'), 'error');
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
        navigate(`/nabidka?company_name=${encodeURIComponent(company.company_name)}`);
    };



    return (
        <>
            <BackButton/>

            <Container property={"flex items-center justify-between mb-6 mt-4"}>
                <Headings sizeTag={"h3"} property={"mt-2"}>
                    {t('companies.title')}
                </Headings>
            </Container>

            <Container>
                <Button
                    onClick={handleCreateCompany}
                    icon={"plus"}
                >
                    {t('companies.add_company')}
                </Button>
            </Container>

            <Container property={"mt-4 rounded-lg"}>
                {loading ? (
                    <Paragraph>{t('common.loading')}</Paragraph>
                ) : companies.length === 0 ? (
                    <Paragraph property="text-center text-gray-500 py-8">
                        {t('companies.no_companies')}
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
        </>
    );
}
