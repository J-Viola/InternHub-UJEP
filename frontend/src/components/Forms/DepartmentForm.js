import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";

import TextField from "@core/Form/TextField";
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

    const getTitle = () => {
        return 'Údaje o katedře';
    };

    const getSubmitButtonText = () => {
        return isEditing ? 'Uložit' : 'Vytvořit';
    };

    return (
        <Container>
            <Headings sizeTag={"h2"} property={"mb-6"}>
                {getTitle()}
            </Headings>

            <form onSubmit={handleSubmit}>
                <Container property={"space-y-6"}>
                    <Container>
                        <TextField
                            id="department_name"
                            label="Název katedry"
                            value={formData.department_name}
                            onChange={(value) => handleInputChange('department_name', value.department_name)}
                            placeholder="Zadejte název katedry"
                            required
                        />
                    </Container>

                    <Container>
                        <TextField
                            id="head_of_department"
                            label="Vedoucí katedry"
                            value={formData.head_of_department}
                            onChange={(value) => handleInputChange('head_of_department', value.head_of_department)}
                            placeholder="Zadejte jméno vedoucího katedry"
                        />
                    </Container>



                    <Container property={"flex gap-4 pt-6"}>
                        <Button
                            type="submit"
                            disabled={loading}
                            icon={action === 'create' ? 'plus' : 'save'}
                        >
                            {loading ? 'Ukládám...' : getSubmitButtonText()}
                        </Button>
                        
                        <Button
                            type="button"
                            variant="gray"
                            onClick={() => navigate('/departments')}
                            disabled={loading}
                        >
                            Zrušit
                        </Button>
                    </Container>
                </Container>
            </form>
        </Container>
    );
} 