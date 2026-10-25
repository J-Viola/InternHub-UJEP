import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import BackButton from "@core/Button/BackButton";
import NabidkaForm from "@components/Forms/NabidkaForm";
import { useCodeListAPI } from "src/api/code_list/code_listAPI";
import { useUserAPI } from "src/api/user/userAPI";
import { useNabidkaAPI } from "src/api/nabidka/nabidkaAPI";
import { useNavigate, useParams } from "react-router-dom";
import Paragraph from "@components/core/Text/Paragraph";
import { useUser } from "@hooks/UserProvider";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import { useTranslation } from "react-i18next";
import { validateRequired } from "@utils/validationUtils";
import getApiErrorMessage from "@utils/apiErrorUtils";
import { useMessage } from "@hooks/MessageContext";


export default function UpravitNabidku() {
    const { t } = useTranslation();
    const [ formData, setFormData ] = useState({})
    const [ subjects, setSubjects ] = useState([])
    const [ organizationUsers, setOrganizationUsers ] = useState([]);
    const [ errors, setErrors ] = useState({});
    const [ loading, setLoading ] = useState(true);
    const [ isInitialized, setIsInitialized ] = useState(false);
    const codeList = useCodeListAPI();
    const userAPI = useUserAPI();
    const nabidkaAPI = useNabidkaAPI();
    const navigate = useNavigate();
    const { id } = useParams();
    const { user } = useUser();
    const { addMessage } = useMessage();

    useEffect(()=> {
        const initFetch = async() => {
            try {
                setLoading(true);

                const subjectsRes = await codeList.getUniqueSubjects();
                setSubjects(subjectsRes);

                const usersRes = await userAPI.getOrganizationUsers();
                setOrganizationUsers(usersRes);

                const practiceRes = await nabidkaAPI.getNabidkaById(id);

                if (practiceRes) {
                    let contactUserId = practiceRes.contact_user;

                    if (practiceRes.contact_user_info && !contactUserId) {
                        const fullName = `${practiceRes.contact_user_info.first_name} ${practiceRes.contact_user_info.last_name}`;
                        const contactUser = usersRes.find(user =>
                            user.label === fullName
                        );

                        if (contactUser) {
                            contactUserId = contactUser.value;
                        }
                    }

                    const transformedData = {
                        title: practiceRes.title,
                        description: practiceRes.description,
                        responsibilities: practiceRes.responsibilities,
                        available_positions: practiceRes.available_positions,
                        start_date: practiceRes.start_date,
                        semester: practiceRes.semester || "",
                        skills: practiceRes.skills,
                        end_date: practiceRes.end_date,
                        coefficient: practiceRes.coefficient,
                        subject_id: practiceRes.subject?.subject_id,
                        contact_user: contactUserId,
                        contact_user_info: practiceRes.contact_user_info,
                        image_base64: practiceRes.image_base64,
                        mentor_name: practiceRes.mentor_name,
                        contact_email: practiceRes.contact_email,
                        region: practiceRes.region,
                        city: practiceRes.city
                    };
                    setFormData(transformedData);
                }
            } catch (error) {
                console.error(t('form.load_error'), error);
                navigate(-1)
            } finally {
                setLoading(false);
                setIsInitialized(true);
            }
        }
        initFetch();
    },[id, codeList, userAPI, nabidkaAPI, navigate, t]);


    const validateForm = () => {
        const newErrors = {};
        // BL-07/PBUG-01: mentor_name + contact_email jsou povinné i na serveru
        // (PracticeSerializer required=True) — bez nich končí update 400 VALIDATION_ERROR.
        const required = ['start_date', 'coefficient', 'contact_user', 'subject_id', 'available_positions', 'title', 'description', 'responsibilities', 'mentor_name', 'contact_email'];

        required.forEach(field => {
            if (!validateRequired(formData[field])) {
                newErrors[field] = t('form.field_required');
            }
        });

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    // BL-07/PBUG-01: coefficient je deprecated/read-only (FE-021) — nesmí do payloadu.
    const buildPayload = () => {
        const { coefficient, ...payload } = formData;
        return payload;
    };

    // BL-07/PBUG-01: pole→hláška mapa z normalizované (apiClient) i raw (axios) chyby.
    const extractFieldErrors = (error) => {
        const data = error?.responseData || error?.response?.data || null;
        const fromNormalized = error?.details && typeof error.details === "object" && !Array.isArray(error.details) ? error.details : null;
        const fromRaw = data?.details && typeof data.details === "object" && !Array.isArray(data.details) ? data.details : null;
        return fromNormalized || fromRaw || null;
    };

    const handleUpdate = async () => {
        if (!validateForm()) {
            addMessage(t('form.validation_error'), "W");
            return;
        }

        try {
            const res = await nabidkaAPI.updateNabidka(id, buildPayload(), false);
            if (res) {
                navigate(-1);
            }
        } catch (error) {
            console.error("Error updating offer:", error);
            const fieldErrors = extractFieldErrors(error);
            if (fieldErrors) {
                setErrors(fieldErrors);
                addMessage(t('form.validation_error'), "E");
                return;
            }
            // Resolver dostane i raw axios tvar (response.data), aby se zachovala
            // dřívější správa serverového `detail` (apiClient normalizace + fallback).
            addMessage(
                getApiErrorMessage(
                    {
                        code: error?.code,
                        details: error?.details ?? (typeof error?.response?.data?.detail === "string" ? error.response.data.detail : undefined),
                        responseData: error?.responseData ?? error?.response?.data ?? null,
                    },
                    t,
                    'form.create_error_unknown'
                ),
                "E"
            );
        }

    }

    const handleChange = (inputObj) => {
        setFormData(prev => ({
            ...prev,
            ...inputObj
        }));
    };

    const handleCalc = async(startDate, empLoad) => {
        if (startDate && empLoad) {
            const endDate = await nabidkaAPI.calculateEndDate(startDate, empLoad);
            if (endDate) {
                setFormData(prev => ({
                    ...prev,
                    end_date: endDate
                }));
            }
        }
    }

    useEffect(() => {
        if (isInitialized && formData.coefficient && formData.start_date) {
            handleCalc(formData.start_date, formData.coefficient);
        }
    }, [formData.coefficient, formData.start_date, isInitialized]);

    useEffect(() => {
        if (organizationUsers.length > 0 && formData && formData.contact_user_info && !formData.contact_user) {
            const fullName = `${formData.contact_user_info.first_name} ${formData.contact_user_info.last_name}`;
            const contactUser = organizationUsers.find(user =>
                user.label === fullName
            );

            if (contactUser) {
                setFormData(prev => ({
                    ...prev,
                    contact_user: contactUser.value
                }));
            }
        }
    }, [organizationUsers, formData]);

    if (loading) {
        return (
            <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
                <BackButton/>
                <Container property="text-center py-8">
                    <Paragraph>{t('form.loading_form')}</Paragraph>
                </Container>
            </ContainerForEntity>
        );
    }

    return(
        <>
            <BackButton/>
            <Container property={"bg-white mt-2 p-8 rounded-lg shadow-sm"}>
                {user.isDepartmentMg() && t('form.role_edit_warning')}
                <NabidkaForm
                    formData={formData}
                    organizationUsers={organizationUsers}
                    subjects={subjects}
                    handleChange={handleChange}
                    handleSubmit={handleUpdate}
                    isEdit={true}
                    errors={errors}
                />
            </Container>
        </>
    )
}
