import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";

import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useDepartmentAPI } from "@api/department/departmentAPI";
import { useMessage } from "@hooks/MessageContext";

export default function DepartmentForm({ handleCreate, handleUpdate, action, id }) {
    const isEditing = action === 'edit';
    
    const navigate = useNavigate();
    const departmentAPI = useDepartmentAPI();
    const { showMessage } = useMessage();

    const [formData, setFormData] = useState({
        department_name: '',
        head_of_department: ''
    });

    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (action === 'edit' && id) {
            loadDepartment();
        }
    }, [action, id]);

    const loadDepartment = async () => {
        try {
            setLoading(true);
            const department = await departmentAPI.getDepartmentById(id);
            if (department) {
                setFormData({
                    department_name: department.department_name || '',
                    head_of_department: department.head_of_department || ''
                });
            }
        } catch (error) {
            showMessage('Chyba při načítání katedry', 'error');
        } finally {
            setLoading(false);
        }
    };

    const handleInputChange = (field, value) => {
        setFormData(prev => ({
            ...prev,
            [field]: value
        }));
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        
        if (!formData.department_name.trim()) {
            showMessage('Název katedry je povinný', 'error');
            return;
        }

        if (isEditing) {
            handleUpdate(formData);
        } else {
            handleCreate(formData);
        }
    };

    const getSubmitButtonText = () => {
        return isEditing ? 'Uložit změny' : 'Vytvořit';
    };

    if (loading) {
        return <Container property={"text-center py-4"}>Načítání...</Container>;
    }

    return (
        <Container>
            <form onSubmit={handleSubmit}>
                <Container property={"space-y-6"}>
                    <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                        {isEditing ? 'Upravit katedru' : 'Údaje katedry'}
                    </Headings>

                    <Container property={"grid gap-4 grid-cols-1 md:grid-cols-2"}>
                        <TextField
                            id="department_name"
                            label="Název katedry"
                            value={formData.department_name}
                            onChange={(value) => handleInputChange('department_name', value.department_name)}
                            placeholder="Zadejte název katedry"
                            required = {true}
                        />

                        <DropDown
                            id="head_of_department"
                            label="Vedoucí katedry"
                            value={formData.head_of_department}
                            onChange={(value) => handleInputChange('head_of_department', value.head_of_department)}
                            placeholder="Vyberte vedoucího katedry"
                            required={true}
                            options={[
                                { value: "jan_novak", label: "Doc. Jan Novák" },
                                { value: "petr_svoboda", label: "Prof. Petr Svoboda" },
                                { value: "eva_hruba", label: "Mgr. Eva Hrubá" }
                            ]}
                        />
                    </Container>

                    <Container property={"flex justify-end"}>
                        <Button
                            type="submit"
                            property={"px-16 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"}
                        >
                            {getSubmitButtonText()}
                        </Button>
                    </Container>
                </Container>
            </form>
        </Container>
    );
}
