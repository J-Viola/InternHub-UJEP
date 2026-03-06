import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import PopUpCon from "@core/Container/PopUpCon";
import { useEmployerAPI } from "@api/employer/employerAPI";
import { useNavigate } from "react-router-dom";
import { useMessage } from "@hooks/MessageContext";
import EmployerEntity from "@components/Employer/EmployerEntity";
import { useTranslation } from "react-i18next";

export default function EmployersPage() {
    const { t } = useTranslation();
    const [employers, setEmployers] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showDeletePop, setShowDeletePop] = useState(false);
    const [selectedEmployer, setSelectedEmployer] = useState(null);

    const employerAPI = useEmployerAPI();
    const navigate = useNavigate();
    const { addMessage } = useMessage();

    const fetchEmployers = async () => {
        try {
            setLoading(true);
            const data = await employerAPI.getAllEmployers();
            setEmployers(data || []);
        } catch (error) {
            console.error(t('employers.load_error'), error);
            addMessage(t('employers.load_error'), 'E');
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
            addMessage(t('employers.delete_success'), 'S');
            setShowDeletePop(false);
            setSelectedEmployer(null);
            fetchEmployers();
        } catch (error) {
            addMessage(t('employers.delete_error'), 'E');
        }
    };

    const handleDeleteCancel = () => {
        setShowDeletePop(false);
        setSelectedEmployer(null);
    };

    return (
        <>
            <BackButton/>

            <Container property={"flex items-center justify-between mb-6 mt-4"}>
                <Headings sizeTag={"h3"} property={"mt-2"}>
                    {t('employers.title')}
                </Headings>
            </Container>

            <Container>
                <Button
                    onClick={handleCreateEmployer}
                    icon={"plus"}
                >
                    {t('employers.add_employer')}
                </Button>
            </Container>

            <Container property={"mt-4 rounded-lg"}>
                {loading ? (
                    <Paragraph>{t('common.loading')}</Paragraph>
                ) : employers.length === 0 ? (
                    <Paragraph property="text-center text-gray-500 py-8">
                        {t('employers.no_employers')}
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

            {/* Popup pro potvrzení smazání */}
            {showDeletePop && (
                <PopUpCon
                    onClose={handleDeleteCancel}
                    title={t('departments.delete_confirm_title')}
                    text={t('departments.delete_confirm_text', { name: selectedEmployer?.employer_name })}
                    onSubmit={handleDeleteConfirm}
                    onReject={handleDeleteCancel}
                    onSubmitText={t('common.delete')}
                    onRejectText={t('common.cancel')}
                />
            )}
        </>
    );
}
