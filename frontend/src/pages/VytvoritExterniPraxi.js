import React, { useState, useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import Container from "@core/Container/Container";
import BackButton from "@core/Button/BackButton";
import Headings from "@core/Text/Headings";
import ExternalPracticeForm from "@components/Forms/ExternalPracticeForm";
import { useCodeListAPI } from "@api/code_list/code_listAPI";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI";
import { useMessage } from "@hooks/MessageContext";
import { validateRequired } from "@utils/validationUtils";
import LoadingState from "@components/core/Feedback/LoadingState";
import ErrorState from "@components/core/Feedback/ErrorState";

export default function VytvoritExterniPraxi() {
    const { t } = useTranslation();
    const [ formData, setFormData ] = useState({});
    const [ subjects, setSubjects ] = useState([]);
    const [ errors, setErrors ] = useState({});
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const codeList = useCodeListAPI();
    const nabidkaAPI = useNabidkaAPI();
    const navigate = useNavigate();
    const { addMessage } = useMessage();

    const fetchInitData = async () => {
        setLoading(true);
        setLoadError(false);
        try {
            const subjectsRes = await codeList.getUniqueSubjects();
            setSubjects(subjectsRes);
        } catch (error) {
            addMessage(t('form.load_error'), "E");
            setLoadError(true);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchInitData();
    }, []);

    // Auto-calculate end_date when start_date or coefficient changes
    const handleCalc = async (startDate, coefficient) => {
        if (startDate && coefficient) {
            const endDate = await nabidkaAPI.calculateEndDate(startDate, coefficient);
            if (endDate) {
                setFormData(prev => ({
                    ...prev,
                    end_date: endDate
                }));
            }
        }
    };

    useEffect(() => {
        if (formData.coefficient && formData.start_date) {
            handleCalc(formData.start_date, formData.coefficient);
        }
    }, [formData.coefficient, formData.start_date]);

    const validateForm = () => {
        const newErrors = {};
        const required = ['employer_name', 'subject_id', 'title', 'start_date', 'end_date', 'coefficient', 'available_positions'];

        required.forEach(field => {
            if (!validateRequired(formData[field])) {
                newErrors[field] = t('form.field_required');
            }
        });

        // dokument s detaily praxe je povinný (accept.pdf/.docx)
        if (!formData.external_details_file) {
            newErrors.external_details_file = t('external.details_required');
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleCreation = async () => {
        if (!validateForm()) {
            addMessage(t('form.validation_error'), "W");
            return;
        }

        setErrors({});
        try {
            // Externí praxe nese povinnou přílohu external_details_file → nabidkaAPI
            // interně přepne payload na multipart/FormData.
            const res = await nabidkaAPI.createExternalPractice(formData);
            if (res) {
                addMessage(t('external_practice.create_success'), "S");
                navigate('/nabidka');
            }
        } catch (error) {
            console.error("Chyba při vytváření mimosystémové praxe:", error);
            if (error.details) {
                setErrors(error.details);
            } else if (error.response?.data) {
                setErrors(error.response.data);
            }
            const errorCode = error.code;
            const detail = error.response?.data?.detail;
            const fallback = detail || t('external_practice.create_error_unknown');
            const message = errorCode ? t(`api_errors.${errorCode}`, { defaultValue: fallback }) : fallback;
            addMessage(message, "E");
        }
    };

    const handleChange = (inputObj) => {
        setFormData(prev => ({
            ...prev,
            ...inputObj
        }));
    };

    return (
        <div className="page-container" style={{ maxWidth: "800px", margin: "0 auto" }}>
            <BackButton />
            {loading && (
                <LoadingState message={t('form.loading_form')} />
            )}
            {!loading && loadError && (
                <ErrorState
                    description={t('form.load_error')}
                    onRetry={fetchInitData}
                />
            )}
            {!loading && !loadError && (
                <Container property="bg-white mt-2 p-8 rounded-lg shadow-sm">
                    <Headings sizeTag="h2" property="text-2xl font-bold mb-6">
                        {t('external_practice.title')}
                    </Headings>
                    <ExternalPracticeForm
                        formData={formData}
                        handleChange={handleChange}
                        handleSubmit={handleCreation}
                        errors={errors}
                        subjects={subjects}
                    />
                </Container>
            )}
        </div>
    );
}
