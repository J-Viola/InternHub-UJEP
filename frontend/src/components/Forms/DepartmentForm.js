import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";

import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import { useNavigate } from "react-router-dom";
import { useDepartmentAPI } from "@api/department/departmentAPI";
import { useUserAPI } from "@api/user/userAPI";
import { useMessage } from "@hooks/MessageContext";
import { useTranslation } from "react-i18next";

export default function DepartmentForm({ handleCreate, handleUpdate, action, id }) {
    const { t } = useTranslation();
    const isEditing = action === 'edit';

    const navigate = useNavigate();
    const departmentAPI = useDepartmentAPI();
    const { addMessage } = useMessage();

    const [formData, setFormData] = useState({
        department_name: '',
        head_of_department: ''
    });

    const [loading, setLoading] = useState(false);
    const [professors, setProfessors] = useState([]);
    const userAPI = useUserAPI();

    useEffect(() => {
        loadProfessors();
        if (action === 'edit' && id) {
            loadDepartment();
        }
    }, [action, id]);

    const loadProfessors = async () => {
        try {
            const data = await userAPI.getAllDepartmentProfessors();
            const options = data.map(prof => ({
                value: prof.user_id,
                label: `${prof.first_name} ${prof.last_name}`
            }));
            setProfessors(options);
        } catch (error) {
            console.error('Error loading professors:', error);
        }
    };

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
            addMessage(t('departments.load_error'), 'E');
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
            addMessage(t('departments.name_required'), 'E');
            return;
        }

        if (isEditing) {
            handleUpdate(formData);
        } else {
            handleCreate(formData);
        }
    };

    const getSubmitButtonText = () => {
        return isEditing ? t('form.save_changes') : t('form.create');
    };

    if (loading) {
        return <Container property={"text-center py-4"}>{t('common.loading')}</Container>;
    }

    return (
        <Container>
            <form onSubmit={handleSubmit}>
                <Container property={"space-y-6"}>
                    <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                        {isEditing ? t('departments.edit_title') : t('departments.data_title')}
                    </Headings>

                    <Container property={"grid gap-4 grid-cols-1 md:grid-cols-2"}>
                        <TextField
                            id="department_name"
                            label={t('departments.name_label')}
                            value={formData.department_name}
                            onChange={(value) => handleInputChange('department_name', value.department_name)}
                            placeholder={t('departments.name_placeholder')}
                            required = {true}
                        />

                        <DropDown
                            id="head_of_department"
                            label={t('departments.head_label')}
                            value={formData.head_of_department}
                            onChange={(value) => handleInputChange('head_of_department', value.head_of_department)}
                            placeholder={t('departments.head_placeholder')}
                            required={true}
                            options={professors}
                        />
                    </Container>

                    <Container property={"flex justify-end"}>
                        <Button
                            type="submit"
                            property={"px-16 py-2"}
                        >
                            {getSubmitButtonText()}
                        </Button>
                    </Container>
                </Container>
            </form>
        </Container>
    );
}
