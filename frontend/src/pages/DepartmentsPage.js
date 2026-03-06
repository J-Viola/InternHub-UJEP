import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import PopUpCon from "@core/Container/PopUpCon";
import { useDepartmentAPI } from "@api/department/departmentAPI";
import { useNavigate } from "react-router-dom";
import { useMessage } from "@hooks/MessageContext";
import DepartmentEntity from "@components/Department/DepartmentEntity";
import { useTranslation } from "react-i18next";

export default function DepartmentsPage() {
    const { t } = useTranslation();
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showDeletePop, setShowDeletePop] = useState(false);
    const [selectedDepartment, setSelectedDepartment] = useState(null);

    const departmentAPI = useDepartmentAPI();
    const navigate = useNavigate();
    const { addMessage } = useMessage();

    const fetchDepartments = async () => {
        try {
            setLoading(true);
            const data = await departmentAPI.getAllDepartments();
            setDepartments(data || []);
        } catch (error) {
            console.error(t('departments.load_error'), error);
            addMessage(t('departments.load_error'), 'error');
            setDepartments([]);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchDepartments();
    }, []);

    const handleCreateDepartment = () => {
        navigate('/formular?type=department&action=create');
    };

    const handleViewDepartment = (department) => {
        navigate(`/subjects?department_id=${department.department_id}`);
    };

    const handleEditDepartment = (department) => {
        navigate(`/formular?type=department&action=edit&id=${department.department_id}`);
    };

    const handleDeleteConfirm = async () => {
        if (!selectedDepartment) return;

        try {
            await departmentAPI.deleteDepartment(selectedDepartment.department_id);
            addMessage(t('departments.delete_success'), 'success');
            setShowDeletePop(false);
            setSelectedDepartment(null);
            fetchDepartments();
        } catch (error) {
            addMessage(t('departments.delete_error'), 'error');
        }
    };

    const handleDeleteCancel = () => {
        setShowDeletePop(false);
        setSelectedDepartment(null);
    };

    return (
        <>
            <BackButton/>

            <Container property={"flex items-center justify-between mb-6 mt-4"}>
                <Headings sizeTag={"h3"} property={"mt-2"}>
                    {t('departments.title')}
                </Headings>
            </Container>

            <Container>
                <Button
                    onClick={handleCreateDepartment}
                    icon={"plus"}
                >
                    {t('departments.create_new')}
                </Button>
            </Container>

            <Container property={"mt-4 rounded-lg"}>
                {loading ? (
                    <Paragraph>{t('common.loading')}</Paragraph>
                ) : departments.length === 0 ? (
                    <Paragraph property="text-center text-gray-500 py-8">
                        {t('departments.no_departments')}
                    </Paragraph>
                ) : (
                    <Container property={"grid grid-cols-1 gap-4"}>
                        {departments.map(department => (
                            <DepartmentEntity
                                key={department.department_id}
                                entity={department}
                                buttons={[
                                    {
                                        icon: "eye",
                                        btnfunction: () => handleViewDepartment(department)
                                    },
                                    {
                                        icon: "edit",
                                        btnfunction: () => handleEditDepartment(department)
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
                    text={t('departments.delete_confirm_text', { name: selectedDepartment?.department_name })}
                    onSubmit={handleDeleteConfirm}
                    onReject={handleDeleteCancel}
                    onSubmitText={t('common.delete')}
                    onRejectText={t('common.cancel')}
                />
            )}
        </>
    );
}
