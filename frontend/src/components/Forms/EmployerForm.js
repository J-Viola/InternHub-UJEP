import React, {useEffect, useState} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import Button from "@components/core/Button/Button";
import { useAresAPI } from "@api/ARES/aresJusticeAPI";
import UploadFile from "@core/Form/UploadFile";
import { useMessage } from "@hooks/MessageContext";
import Headings from "@core/Text/Headings";
import { useEmployerAPI } from "src/api/employer/employerAPI";
import { useTranslation } from "react-i18next";

export default function EmployerForm({ handleCreate, handleUpdate, action, id }) {
    const { t } = useTranslation();
    const ares = useAresAPI();
    const { addMessage } = useMessage();
    const employerAPI = useEmployerAPI();

    const [ico, setICO] = useState('');
    const [entity, setEntity] = useState(null);
    const [aresFetched, setAresFetched] = useState(false);
    const [loading, setLoading] = useState(false);

    const [formData, setFormData] = useState({
        employerName: '',
        address: '',
        ico: '',
        dic: '',
        titleBefore: '',
        executiveName: '',
        executiveSurname: '',
        titleAfter: '',
        executiveEmail: '',
        executivePhone: '',
        executivePassword1: '',
        executivePassword2: '',
        logo: null
    });

    const isEditing = action === 'edit';

    useEffect(() => {
        if (isEditing && id) {
            loadEmployer();
        }
    }, [action, id]);

    const loadEmployer = async () => {
        try {
            setLoading(true);
            const employer = await employerAPI.getEmployerById(id);
            if (employer) {
                setFormData({
                    employerName: employer.employer_name || '',
                    address: employer.address || '',
                    ico: employer.ico || '',
                    dic: employer.dic || '',
                    titleBefore: '',
                    executiveName: '',
                    executiveSurname: '',
                    titleAfter: '',
                    executiveEmail: '',
                    executivePhone: '',
                    executivePassword1: '',
                    executivePassword2: '',
                    logo: null
                });
                setEntity({
                    obchodniJmeno: employer.employer_name,
                    sidlo: { textovaAdresa: employer.address }
                });
                setAresFetched(true);
            }
        } catch (error) {
            console.error('Error loading employer:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleARESCall = async (icoValue) => {
        if (!icoValue) {
            addMessage(t('employer.ares_fill'), "E");
            return;
        }

        try {
            setLoading(true);
            const response = await ares.getEntityByICO(icoValue);
            if (response) {
                setEntity(response);
                setFormData(prev => ({
                    ...prev,
                    employerName: response.obchodniJmeno || '',
                    address: response.sidlo?.textovaAdresa || '',
                    ico: icoValue,
                    dic: response.dic || ''
                }));
                setAresFetched(true);
                addMessage(t('employer.ares_success'), "S");
            }
        } catch (error) {
            addMessage(t('employer.ares_error'), "E");
        } finally {
            setLoading(false);
        }
    };

    const validateForm = () => {
        const requiredFields = {
            'executiveName': t('employer.executive_name'),
            'executiveSurname': t('employer.executive_surname'),
            'executiveEmail': t('employer.executive_email'),
            'executivePhone': t('employer.executive_phone')
        };

        if (!isEditing) {
            requiredFields['executivePassword1'] = t('login.password');
            requiredFields['executivePassword2'] = t('login.password'); // Wiederholung
        }

        const missingFields = [];

        if (!aresFetched && !isEditing) {
            addMessage(t('employer.ares_needed'), "E");
            return false;
        }

        for (const [fieldId, fieldName] of Object.entries(requiredFields)) {
            if (!formData[fieldId] || formData[fieldId].trim() === '') {
                missingFields.push(fieldName);
            }
        }

        if (!isEditing && formData.executivePassword1 && formData.executivePassword2 &&
            formData.executivePassword1 !== formData.executivePassword2) {
            addMessage(t('employer.password_mismatch'), "E");
            return false;
        }

        if (missingFields.length > 0) {
            addMessage(t('employer.missing_fields', { fields: missingFields.join(', ') }), "E");
            return false;
        }

        return true;
    };

    const handleFormChange = (value) => {
        setFormData(prev => ({
            ...prev,
            ...value
        }));
    };

    const handleFileChange = (file) => {
        setFormData(prev => ({
            ...prev,
            logo: file
        }));
    };

    const handleSubmit = () => {
        if (validateForm()) {
            const employerData = {
                employer_name: formData.employerName,
                ico: formData.ico,
                dic: formData.dic,
                address: formData.address,
                employer_profile: '',
                first_name: formData.executiveName,
                last_name: formData.executiveSurname,
                title_before: formData.titleBefore,
                title_after: formData.titleAfter,
                email: formData.executiveEmail,
                phone: formData.executivePhone
            };

            if (!isEditing && formData.executivePassword1) {
                employerData.password = formData.executivePassword1;
                employerData.password2 = formData.executivePassword2;
            }

            if (formData.logo) {
                employerData.logo = formData.logo;
            }

            if (isEditing) {
                handleUpdate(employerData);
            } else {
                handleCreate(employerData);
            }
        }
    };

    if (loading) {
        return <Container property={"text-center py-4"}>{t('common.loading')}</Container>;
    }

    return(
            <>
                <Container>
                     <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                        {isEditing ? t('employer.edit_title') : t('employer.data_title')}
                    </Headings>
                </Container>
                {!isEditing && (
                    <Container property={"grid gap-2 grid-cols-2 mb-4"}>
                        <TextField
                            id={"ico"}
                            required={true}
                            label={t('employer.ares_fill')}
                            placeholder={t('profile.ico')}
                            value={ico}
                            onChange={(value) => setICO(value.ico)}
                            property={"w-full"}
                        />
                        <Button
                            property={"w-1/3 mt-6 px-4 justify-self-end"}
                            onClick={() => handleARESCall(ico)}
                            variant={"blueSmall"}
                        >
                            {t('common.search')}
                        </Button>
                    </Container>
                )}

                <Container property={"grid gap-4 grid-cols-1 md:grid-cols-2 mb-6"}>
                    <TextField
                        id={"employerName"}
                        required={true}
                        label={t('employer.name_label')}
                        value={formData.employerName}
                        placeholder={t('employer.name_placeholder')}
                        onChange={(value) => handleFormChange(value)}
                        disabled={!isEditing && aresFetched}
                    />

                    <TextField
                        id={"address"}
                        required={true}
                        label={t('profile.address')}
                        value={formData.address}
                        placeholder={t('profile.address')}
                        onChange={(value) => handleFormChange(value)}
                        disabled={!isEditing && aresFetched}
                    />

                    <TextField
                        id={"titleBefore"}
                        required={false}
                        label={t('profile.title_before')}
                        placeholder={t('profile.title_before_placeholder')}
                        value={formData.titleBefore}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField
                        id={"executiveName"}
                        required={true}
                        label={t('employer.executive_name')}
                        placeholder={t('profile.first_name_placeholder')}
                        value={formData.executiveName}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField
                        id={"executiveSurname"}
                        required={true}
                        label={t('employer.executive_surname')}
                        placeholder={t('profile.last_name_placeholder')}
                        value={formData.executiveSurname}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField
                        id={"titleAfter"}
                        required={false}
                        label={t('profile.title_after')}
                        placeholder={t('profile.title_after_placeholder')}
                        value={formData.titleAfter}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField
                        id={"executiveEmail"}
                        required={true}
                        label={t('employer.executive_email')}
                        placeholder={t('profile.email_placeholder')}
                        value={formData.executiveEmail}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField
                        id={"executivePhone"}
                        required={true}
                        label={t('employer.executive_phone')}
                        placeholder={t('profile.phone_placeholder')}
                        value={formData.executivePhone}
                        onChange={(value) => handleFormChange(value)}
                    />
                </Container>

                {!isEditing && (
                    <Container property={"grid grid-cols-1 md:grid-cols-2 gap-4 mb-4"}>
                        <TextField
                            id={"executivePassword1"}
                            required={true}
                            label={t('login.password')}
                            placeholder={"******"}
                            type={"password"}
                            value={formData.executivePassword1}
                            onChange={(value) => handleFormChange(value)}
                        />

                        <TextField
                            id={"executivePassword2"}
                            required={true}
                            label={t('login.password')}
                            placeholder={"******"}
                            type={"password"}
                            value={formData.executivePassword2}
                            onChange={(value) => handleFormChange(value)}
                        />
                    </Container>
                )}

                <UploadFile
                    id="employerLogo"
                    property={"mt-4"}
                    onChange={handleFileChange}
                    label={t('employer.upload_logo')}
                    accept="image/*"
                    previewOn={true}
                />

                <Container property={"flex w-full justify-end ml-auto mt-4"}>
                    <Button
                        property={"mt-2 px-16"}
                        onClick={handleSubmit}
                    >
                        {isEditing ? t('form.save_changes') : t('employer.create_button')}
                    </Button>
                </Container>
            </>
        )
}
