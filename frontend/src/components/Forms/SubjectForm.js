import React, {useState, useEffect} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import Button from "@components/core/Button/Button";
import Headings from "@core/Text/Headings";
import { useSubjectAPI } from "src/api/subject/subjectAPI";
import { useUserAPI } from "src/api/user/userAPI";
import { useDepartmentAPI } from "src/api/department/departmentAPI";
import { useTranslation } from "react-i18next";

export default function SubjectForm({handleCreate, handleUpdate, action, id}) {
    const { t } = useTranslation();
    const [formData, setFormData] = useState({
        name: "",
        subjectCode: "",
        timeCriterion: "",
        subjectManager: "",
        department: ""
    });
    const [professorOptions, setProfessorOptions] = useState([]);
    const [departmentOptions, setDepartmentOptions] = useState([]);
    const [loading, setLoading] = useState(false);
    const subjectAPI = useSubjectAPI();
    const userAPI = useUserAPI();
    const departmentAPI = useDepartmentAPI();
    const isEditing = action === 'edit';

    useEffect(() => {
        if (isEditing && id) {
            loadSubject();
        }
        loadProfessors();
        loadDepartments();
    }, [action, id]);

    const loadSubject = async () => {
        try {
            setLoading(true);
            const subject = await subjectAPI.getSubjectById(id);
            if (subject) {
                setFormData({
                    name: subject.subject_name || "",
                    subjectCode: subject.subject_code || "",
                    timeCriterion: subject.hours_required || "",
                    subjectManager: subject.teacher?.user_id || "",
                    department: subject.department_id || subject.department?.department_id || ""
                });
            }
        } catch (error) {
            console.error('Chyba při načítání předmětu:', error);
        } finally {
            setLoading(false);
        }
    };

    const loadProfessors = async () => {
        try {
            const professors = await userAPI.getAllDepartmentProfessors();
            const options = professors.map(prof => ({
                label: prof.full_name || prof.name || `${prof.first_name} ${prof.last_name}`,
                value: prof.user_id || prof.id
            }));
            setProfessorOptions(options);
        } catch (error) {
            console.error('Chyba při načítání profesorů:', error);
        }
    };

    const loadDepartments = async () => {
        try {
            const departments = await departmentAPI.getAllDepartments();
            const options = departments.map(dept => ({
                label: dept.department_name,
                value: dept.department_id
            }));
            setDepartmentOptions(options);
        } catch (error) {
            console.error('Chyba při načítání kateder:', error);
        }
    };

    const handleChange = (field) => (valueObject) => {
        const value = valueObject[field];
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const handleSubmit = () => {
        // Prepare data for API submission
        const submitData = {
            subject_name: formData.name,
            subject_code: formData.subjectCode,
            hours_required: formData.timeCriterion,
            // Add teacher/manager ID if available
            ...(formData.subjectManager && { teacher_id: formData.subjectManager }),
        };

        if (isEditing) {
            handleUpdate(submitData);
        } else {
            handleCreate(submitData);
        }
    };

    const getButtonText = () => {
        return isEditing ? 'Uložit změny' : 'Vytvořit';
    };

    if (loading) {
        return <Container property={"text-center py-4"}>{t('common.loading')}</Container>;
    }

    return(
        <Container property={"space-y-6"}>
            {/* Údaje předmětu */}
            <Container property={"space-y-4"}>
                <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                    {isEditing ? t('subjects.edit_subject') : t('subjects.subject_data')}
                </Headings>

                <Container property={"grid gap-4 grid-cols-1 md:grid-cols-2"}>
                    <TextField
                        id={"name"}
                        required={true}
                        label={t('offers.filter.name')}
                        placeholder={t('offers.filter.name')}
                        value={formData.name}
                        onChange={handleChange("name")}
                    />

                    <TextField
                        id={"subjectCode"}
                        required={true}
                        label={t('subjects.code')}
                        placeholder={t('subjects.code')}
                        value={formData.subjectCode}
                        onChange={handleChange("subjectCode")}
                    />

                    <TextField
                        id={"timeCriterion"}
                        required={true}
                        label={t('subjects.time_criterion')}
                        placeholder={t('subjects.time_criterion')}
                        value={formData.timeCriterion}
                        onChange={handleChange("timeCriterion")}
                    />

                    <DropDown
                        id={"department"}
                        required={true}
                        label={t('subjects.department')}
                        placeholder={t('subjects.select_department')}
                        options={departmentOptions}
                        value={formData.department}
                        onChange={handleChange("department")}
                        disabled={true}
                    />

                    <DropDown
                        id={"subjectManager"}
                        required={true}
                        label={t('subjects.subject_manager')}
                        placeholder={t('subjects.subject_manager')}
                        options={professorOptions}
                        value={formData.subjectManager}
                        onChange={handleChange("subjectManager")}
                    />
                </Container>
            </Container>

            <Container property={"flex justify-end"}>
                <Button
                    property={"px-16 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"}
                    onClick={handleSubmit}
                >
                    {getButtonText()}
                </Button>
            </Container>
        </Container>
    )
}
