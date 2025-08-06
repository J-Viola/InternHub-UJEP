import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import Nav from "@components/core/Nav";
import PopUpCon from "@core/Container/PopUpCon";
import { useDepartmentAPI } from "@api/department/departmentAPI";
import { useNavigate } from "react-router-dom";
import { useMessage } from "@hooks/MessageContext";
import DepartmentEntity from "@components/Department/DepartmentEntity";

export default function DepartmentsPage() {
    const [departments, setDepartments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showDeletePop, setShowDeletePop] = useState(false);
    const [selectedDepartment, setSelectedDepartment] = useState(null);
    
    const departmentAPI = useDepartmentAPI();
    const navigate = useNavigate();
    const { showMessage } = useMessage();

    const fetchDepartments = async () => {
        try {
            setLoading(true);
            const data = await departmentAPI.getAllDepartments();
            setDepartments(data || []);
        } catch (error) {
            console.error("Chyba při načítání kateder:", error);
            showMessage('Chyba při načítání kateder', 'error');
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

    const handleDeleteClick = (department) => {
        setSelectedDepartment(department);
        setShowDeletePop(true);
    };

    const handleDeleteConfirm = async () => {
        if (!selectedDepartment) return;
        
        try {
            await departmentAPI.deleteDepartment(selectedDepartment.department_id);
            showMessage('Katedra byla úspěšně smazána', 'success');
            setShowDeletePop(false);
            setSelectedDepartment(null);
            fetchDepartments();
        } catch (error) {
            showMessage('Chyba při mazání katedry', 'error');
        }
    };

    const handleDeleteCancel = () => {
        setShowDeletePop(false);
        setSelectedDepartment(null);
    };

    return (
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <BackButton/>
                
                <Container property={"flex items-center justify-between mb-6 mt-4"}>
                    <Headings sizeTag={"h3"} property={"mt-2"}>
                        Správa kateder
                    </Headings>
                </Container>

                <Container>
                    <Button 
                        onClick={handleCreateDepartment}
                        icon={"plus"}
                    >
                        Založit katedru
                    </Button>
                </Container>

                <Container property={"mt-4 rounded-lg"}>
                    {loading ? (
                        <Paragraph>Načítání...</Paragraph>
                    ) : departments.length === 0 ? (
                        <Paragraph property="text-center text-gray-500 py-8">
                            Zatím nejsou žádné katedry k zobrazení.
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
            </Container>

            {/* Popup pro potvrzení smazání */}
            {showDeletePop && (
                <PopUpCon 
                    onClose={handleDeleteCancel}
                    title="Potvrdit smazání"
                    text={`Opravdu chcete smazat katedru "${selectedDepartment?.department_name}"? Tato akce je nevratná.`}
                    onSubmit={handleDeleteConfirm}
                    onReject={handleDeleteCancel}
                    onSubmitText="Smazat"
                    onRejectText="Zrušit"
                />
            )}
        </Container>
    );
} 