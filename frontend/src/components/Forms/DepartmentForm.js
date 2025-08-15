import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";

import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useDepartmentAPI } from "@api/department/departmentAPI";
import { useMessage } from "@hooks/MessageContext";

export default function DepartmentForm() {
    const [searchParams] = useSearchParams();
    const action = searchParams.get('action');
    const id = searchParams.get('id');
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

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!formData.department_name.trim()) {
            showMessage('Název katedry je povinný', 'error');
            return;
        }

        try {
            setLoading(true);
            
            if (action === 'create') {
                await departmentAPI.createDepartment(formData);
                showMessage('Katedra byla úspěšně vytvořena', 'success');
            } else if (action === 'edit') {
                await departmentAPI.updateDepartment(id, formData);
                showMessage('Katedra byla úspěšně aktualizována', 'success');
            }
            
            navigate('/departments');
        } catch (error) {
            showMessage('Chyba při ukládání katedry', 'error');
        } finally {
            setLoading(false);
        }
    };

    const getSubmitButtonText = () => {
        return isEditing ? 'Uložit' : 'Vytvořit';
    };

    return (
        <Container>
            <form onSubmit={handleSubmit}>
                <Container property={"space-y-2"}>
                    <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                        Údaje katedry
                    </Headings>
                    <Container>
                        <TextField
                            id="department_name"
                            label="Název katedry"
                            value={formData.department_name}
                            onChange={(value) => handleInputChange('department_name', value.department_name)}
                            placeholder="Zadejte název katedry"
                            required = {true}
                        />
                    </Container>

                    <Container>
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



                    <Container property={"flex gap-4 pt-6 justify-end"}>
                        <Button
                            type="submit"
                            disabled={loading}
                            icon={action === 'create' ? 'plus' : 'save'}
                        >
                            {loading ? 'Ukládám...' : getSubmitButtonText()}
                        </Button>
                        
                    </Container>
                </Container>
            </form>
        </Container>
    );
} 