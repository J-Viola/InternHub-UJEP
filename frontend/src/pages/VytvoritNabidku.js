import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import BackButton from "@core/Button/BackButton";
import NabidkaForm from "@components/Forms/NabidkaForm";
import { useCodeListAPI } from "@api/code_list/code_listAPI";
import { useUserAPI } from "@api/user/userAPI";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI";
import { useNavigate } from "react-router-dom";
import { useMessage } from "@hooks/MessageContext";


export default function VytvoritNabidku() {
    const [ formData, setFormData ] = useState({})
    const [ subjects, setSubjects ] = useState([])
    const [ organizationUsers, setOrganizationUsers ] = useState([]);
    const [ errors, setErrors ] = useState({});
    const codeList = useCodeListAPI();
    const userAPI = useUserAPI();
    const nabidkaAPI = useNabidkaAPI();
    const navigate = useNavigate();
    const { addMessage } = useMessage();

    useEffect(()=> {
        const initFetch = async() => {
            await codeList.getUniqueSubjects().then(val => setSubjects(val))
            await userAPI.getOrganizationUsers().then(val => setOrganizationUsers(val))
        }
        initFetch();
    },[])


    const handleCreation = async () => {
        setErrors({});
        try {
            const res = await nabidkaAPI.createNabidka(formData);
            if (res) {
                // addMessage("Nabídka byla úspěšně vytvořena", "S"); // Již se přidává v nabidkaAPI
                navigate(-1);
            }
        } catch (error) {
            console.error("Chyba při vytváření nabídky:", error);
            if (error.response?.data) {
                setErrors(error.response.data);
                if (error.response.data.detail) {
                    addMessage(error.response.data.detail, "E");
                } else {
                    addMessage("Zkontrolujte prosím formulář.", "E");
                }
            } else {
                addMessage("Došlo k neznámé chybě při vytváření nabídky.", "E");
            }
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
        console.log("Form", formData);
    },[formData])


    useEffect(() => {
        if (formData.coefficient && formData.start_date) {
            console.log("Volám API na endDate")
            handleCalc(formData.start_date, formData.coefficient);
        }
    }, [formData.coefficient, formData.start_date]);

    return(
        <>
            <BackButton/>
            <Container property={"bg-white mt-2 p-8 rounded-lg shadow-sm"}>
                <NabidkaForm
                    formData={formData}
                    organizationUsers={organizationUsers}
                    subjects={subjects}
                    handleChange={handleChange}
                    handleSubmit={handleCreation}
                    errors={errors}
                />
            </Container>
        </>
    )
}
