import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Nav from "@components/core/Nav";
import Headings from "@core/Text/Headings";
import BackButton from "@core/Button/BackButton";
import Button from "@core/Button/Button";
import TextField from "@core/Form/TextField";
import TextBox from "@core/Form/TextBox";
import DropDown from "@core/Form/DropDown";
import CustomDatePicker from "@core/Form/DatePicker";
import VytvoritNabidkuForm from "@components/Forms/VytvoritNabidkuForm";
import { useCodeListAPI } from "src/api/code_list/code_listAPI";
import { useUserAPI } from "src/api/user/userAPI";
import { useNabidkaAPI } from "src/api/nabidka/nabidkaAPI";
import { useNavigate } from "react-router-dom";




export default function VytvoritNabidku() {
    const [ formData, setFormData ] = useState({})
    const [ subjects, setSubjects ] = useState([])
    const [ organizationUsers, setOrganizationUsers ] = useState([]);
    const codeList = useCodeListAPI();
    const userAPI = useUserAPI();
    const nabidkaAPI = useNabidkaAPI();
    const navigate = useNavigate();

    useEffect(()=> {
        const initFetch = async() => {
            const res1 = await codeList.getUniqueSubjects().then(val => setSubjects(val))
            const res2 = await userAPI.getOrganizationUsers().then(val => setOrganizationUsers(val))
        }
        initFetch();
    },[])


    const handleCreation = async () => {
        const res = await nabidkaAPI.createNabidka(formData);
        res && navigate(-1);
        
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
        <Container property="min-h-screen">
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <BackButton/>
                <Container property={"bg-gray-50 mt-2 p-4 rounded-lg"}>
                    <VytvoritNabidkuForm
                        formData={formData}
                        organizationUsers={organizationUsers}
                        subjects={subjects}
                        handleChange={handleChange}
                        handleSubmit={handleCreation}
                    />
                </Container>

            </Container>
        </Container>
    )
}