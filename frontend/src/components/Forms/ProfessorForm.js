import React, {useState, useEffect} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import Button from "@components/core/Button/Button";
import Headings from "@core/Text/Headings";
import { useDepartmentAPI } from "src/api/department/departmentAPI";
import { useTranslation } from "react-i18next";

export default function ProfessorForm({ action, id, handleCreate, handleUpdate }) {
    const { t } = useTranslation();
    const [formData, setFormData] = useState({
        name: "",
        surname: "",
        titleBefore: "",
        titleAfter: "",
        email: "",
        phone: "",
        ucitIdno: ""
    });
    const [loading, setLoading] = useState(false);
    const departmentAPI = useDepartmentAPI();
    const isEditing = action === 'edit';

    useEffect(() => {
        if (isEditing && id) {
            loadUser();
        }
    }, [action, id]);

    const loadUser = async () => {
        try {
            setLoading(true);
            const user = await departmentAPI.getProfessorById(id);
            if (user) {
                setFormData({
                    name: user.first_name || "",
                    surname: user.last_name || "",
                    titleBefore: user.title_before || "",
                    titleAfter: user.title_after || "",
                    email: user.email || "",
                    phone: user.phone || "",
                    ucitIdno: user.ucit_idno || ""
                });
            }
        } catch (error) {
            console.error(t('professor.load_error'), error);
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

    const handleSubmit = () => {
        const userData = {
            first_name: formData.name,
            last_name: formData.surname,
            title_before: formData.titleBefore,
            title_after: formData.titleAfter,
            email: formData.email,
            phone: formData.phone,
            ucit_idno: formData.ucitIdno
        };

        if (isEditing) {
            handleUpdate(userData);
        } else {
            handleCreate(userData);
        }
    };

    if (loading) {
        return <Container property={"text-center py-4"}>{t('common.loading')}</Container>;
    }

    return(
        <>
        <Container property={"mb-6"}>
            <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                {isEditing ? t('professor.edit_title') : t('professor.data_title')}
            </Headings>
        </Container>
        {/* Osobní údaje sekce */}
        <Container property={"mb-6"}>
            <Container property={"grid gap-4 grid-cols-3"}>
                <TextField
                    id={"name"}
                    required={true}
                    label={t('profile.first_name')}
                    placeholder={t('profile.first_name')}
                    value={formData.name}
                    onChange={(value) => handleInputChange('name', value.name)}
                />
                <TextField
                    id={"surname"}
                    required={true}
                    label={t('profile.last_name')}
                    placeholder={t('profile.last_name')}
                    value={formData.surname}
                    onChange={(value) => handleInputChange('surname', value.surname)}
                />
                <DropDown
                    id={"titleBefore"}
                    required={false}
                    label={t('profile.title_before')}
                    placeholder={t('profile.title_before')}
                    value={formData.titleBefore}
                    options={[
                        { value: "Ing.", label: "Ing." },
                        { value: "Mgr.", label: "Mgr." },
                        { value: "Ph.D.", label: "Ph.D." },
                        { value: "Doc.", label: "Doc." },
                        { value: "Prof.", label: "Prof." }
                    ]}
                    onChange={(value) => handleInputChange('titleBefore', value.titleBefore)}
                />

                <DropDown
                    id={"titleAfter"}
                    required={false}
                    label={t('profile.title_after')}
                    placeholder={t('profile.title_after')}
                    value={formData.titleAfter}
                    options={[
                        { value: "MBA", label: "MBA" },
                        { value: "Ph.D.", label: "Ph.D." },
                        { value: "CSc.", label: "CSc." },
                        { value: "DrSc.", label: "DrSc." }
                    ]}
                    onChange={(value) => handleInputChange('titleAfter', value.titleAfter)}
                />

                <TextField
                    id={"email"}
                    required={true}
                    label={t('profile.email')}
                    placeholder={t('profile.email')}
                    value={formData.email}
                    onChange={(value) => handleInputChange('email', value.email)}
                />

                <TextField
                    id={"phone"}
                    required={true}
                    label={t('profile.phone')}
                    placeholder={t('profile.phone')}
                    value={formData.phone}
                    onChange={(value) => handleInputChange('phone', value.phone)}
                />

                <TextField
                    id={"ucitIdno"}
                    required={false}
                    label={t('professor.teacher_id')}
                    placeholder={t('professor.teacher_id_placeholder')}
                    value={formData.ucitIdno}
                    onChange={(value) => handleInputChange('ucitIdno', value.ucitIdno)}
                />

            </Container>
        </Container>

        <Container property={"flex w-full justify-end"}>
            <Button
                property={"px-16 py-2"}
                onClick={handleSubmit}
            >
                {isEditing ? t('form.save_changes') : t('form.create')}
            </Button>
        </Container>
        </>
    )
}
