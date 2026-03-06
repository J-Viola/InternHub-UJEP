import React, {useState, useEffect} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import Button from "@components/core/Button/Button";
import Headings from "@core/Text/Headings";
import { useUserAPI } from "@api/user/userAPI";
import { useCompanyAPI } from "@api/company/companyAPI";
import { useTranslation } from "react-i18next";

export default function UserForm({ organizationUser = false, action, id, handleCreate, handleUpdate }) {
    const { t } = useTranslation();
    const [formData, setFormData] = useState({
        name: "",
        surname: "",
        titleBefore: "",
        titleAfter: "",
        email: "",
        phone: "",
        company: "",
        role: "",
        password: "",
        passwordConfirm: ""
    });
    const [loading, setLoading] = useState(false);
    const [companies, setCompanies] = useState([]);
    const userAPI = useUserAPI();
    const companyAPI = useCompanyAPI();
    const isEditing = action === 'edit';

    useEffect(() => {
        loadCompanies();
        if (isEditing && id) {
            loadUser();
        }
    }, [action, id]);

    const loadCompanies = async () => {
        try {
            const data = await companyAPI.getAllCompanies();
            const options = data.map(company => ({
                value: company.employer_id,
                label: company.company_name
            }));
            setCompanies(options);
        } catch (error) {
            console.error(t('companies.load_error'), error);
        }
    };

    const loadUser = async () => {
        try {
            setLoading(true);
            const user = await userAPI.getUserById(id);
            if (user) {
                setFormData({
                    name: user.first_name || "",
                    surname: user.last_name || "",
                    titleBefore: user.title_before || "",
                    titleAfter: user.title_after || "",
                    email: user.email || "",
                    phone: user.phone || "",
                    company: user.company || "",
                    role: user.role || "",
                    password: "",
                    passwordConfirm: ""
                });
            }
        } catch (error) {
            console.error(t('users.load_error'), error);
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
        // Validation for passwords
        if (!isEditing && formData.password !== formData.passwordConfirm) {
            console.error(t('password_change.mismatch'));
            return;
        }

        // Prepare data for API
        const userData = {
            first_name: formData.name,
            last_name: formData.surname,
            title_before: formData.titleBefore,
            title_after: formData.titleAfter,
            email: formData.email,
            phone: formData.phone,
            company: formData.company,
            role: formData.role
        };

        // Add password only for create or if password is provided for update
        if (!isEditing || formData.password) {
            userData.password = formData.password;
            userData.password2 = formData.passwordConfirm;
        }

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
                {isEditing ? t('users.edit_title') : t('users.data_title')}
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

                <DropDown
                    id={"company"}
                    required={true}
                    label={t('users.assign_to_company')}
                    placeholder={t('profile.organization')}
                    value={formData.company}
                    options={companies}
                    onChange={(value) => handleInputChange('company', value.company)}
                />

                <DropDown
                    id={"role"}
                    required={true}
                    label={t('users.role')}
                    placeholder={t('users.role')}
                    value={formData.role}
                    options={[
                        { value: "OWNER", label: t('profile.roles.OWNER') },
                        { value: "INSERTER", label: t('profile.roles.INSERTER') }
                    ]}
                    onChange={(value) => handleInputChange('role', value.role)}
                />
            </Container>
        </Container>

        {/* Heslo sekce */}
        <Container property={"mb-6"}>
            <Headings sizeTag={"h5"} property={"mb-4 font-bold"}>
                {isEditing ? t('users.password_change_optional') : t('users.password_section')}
            </Headings>

            <Container property={"grid gap-4 grid-cols-2"}>
                <TextField
                    id={"password"}
                    required={!isEditing}
                    placeholder={"*********"}
                    label={t('login.password')}
                    type={"password"}
                    value={formData.password}
                    onChange={(value) => handleInputChange('password', value.password)}
                />

                <TextField
                    id={"passwordConfirm"}
                    required={!isEditing}
                    placeholder={"*********"}
                    label={t('users.confirm_password')}
                    type={"password"}
                    value={formData.passwordConfirm}
                    onChange={(value) => handleInputChange('passwordConfirm', value.passwordConfirm)}
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
