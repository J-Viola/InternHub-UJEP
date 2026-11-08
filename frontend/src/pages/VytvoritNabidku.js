import React, { useState, useEffect, useRef } from "react";
import Container from "@core/Container/Container";
import BackButton from "@core/Button/BackButton";
import NabidkaForm from "@components/Forms/NabidkaForm";
import { useCodeListAPI } from "@api/code_list/code_listAPI";
import { useUserAPI } from "@api/user/userAPI";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI";
import { useNavigate } from "react-router-dom";
import { useMessage } from "@hooks/MessageContext";
import { validateRequired } from "@utils/validationUtils";
import getApiErrorMessage from "@utils/apiErrorUtils";
import LoadingState from "@components/core/Feedback/LoadingState";
import ErrorState from "@components/core/Feedback/ErrorState";


export default function VytvoritNabidku() {
    const [ formData, setFormData ] = useState({})
    const [ subjects, setSubjects ] = useState([])
    const [ organizationUsers, setOrganizationUsers ] = useState([]);
    const [ errors, setErrors ] = useState({});
    const [loading, setLoading] = useState(true);
    const [loadError, setLoadError] = useState(false);
    const [submitting, setSubmitting] = useState(false);
    const submittingRef = useRef(false);
    const codeList = useCodeListAPI();
    const userAPI = useUserAPI();
    const nabidkaAPI = useNabidkaAPI();
    const navigate = useNavigate();
    const { addMessage } = useMessage();

    const fetchInitData = async () => {
        setLoading(true);
        setLoadError(false);
        try {
            const [subjectsRes, usersRes] = await Promise.all([
                codeList.getUniqueSubjects(),
                userAPI.getOrganizationUsers()
            ]);
            setSubjects(subjectsRes);
            setOrganizationUsers(usersRes);
        } catch (error) {
            addMessage("Chyba při načítání dat pro formulář", "E");
            setLoadError(true);
        } finally {
            setLoading(false);
        }
    };

    useEffect(()=> {
        fetchInitData();
    },[])


    const validateForm = () => {
        const newErrors = {};
        // BL-07/PBUG-01: mentor_name + contact_email jsou povinné i na serveru
        // (PracticeSerializer required=True) — bez nich končí create 400 VALIDATION_ERROR.
        const required = ['start_date', 'coefficient', 'contact_user', 'subject_id', 'available_positions', 'title', 'description', 'responsibilities', 'mentor_name', 'contact_email'];

        required.forEach(field => {
            if (!validateRequired(formData[field])) {
                newErrors[field] = "Toto pole je povinné.";
            }
        });

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    // BL-07/PBUG-01: coefficient je deprecated/read-only (FE-021) — nesmí do payloadu.
    // Slouží jen k UI náhledu výpočtu end_date (get-end-date).
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

    const handleCreation = async () => {
        if (submittingRef.current) return;
        if (!validateForm()) {
            addMessage("Zkontrolujte prosím chyby ve formuláři.", "W");
            return;
        }

        setErrors({});
        submittingRef.current = true;
        setSubmitting(true);
        try {
            const res = await nabidkaAPI.createNabidka(buildPayload());
            if (res) {
                // addMessage("Nabídka byla úspěšně vytvořena", "S"); // Již se přidává v nabidkaAPI
                navigate(-1);
            }
        } catch (error) {
            console.error("Chyba při vytváření nabídky:", error);
            const fieldErrors = extractFieldErrors(error);
            if (fieldErrors) {
                setErrors(fieldErrors);
                addMessage("Zkontrolujte prosím chyby ve formuláři.", "E");
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
                    "Nastala neočekávaná chyba při ukládání nabídky."
                ),
                "E"
            );
        } finally {
            submittingRef.current = false;
            setSubmitting(false);
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
        if (formData.coefficient && formData.start_date) {
            handleCalc(formData.start_date, formData.coefficient);
        }
    }, [formData.coefficient, formData.start_date]);

    return(
        <>
            <BackButton/>
            {loading && (
                <LoadingState message={"Načítání formuláře..."} />
            )}
            {!loading && loadError && (
                <ErrorState
                    description={"Chyba při načítání dat pro formulář"}
                    onRetry={fetchInitData}
                />
            )}
            {!loading && !loadError && (
            <Container property={"bg-white mt-2 p-8 rounded-lg shadow-sm"}>
                <NabidkaForm
                    formData={formData}
                    organizationUsers={organizationUsers}
                    subjects={subjects}
                    handleChange={handleChange}
                    handleSubmit={handleCreation}
                    errors={errors}
                    submitting={submitting}
                />
            </Container>
            )}
        </>
    )
}
