// zde bude switch podle paramu na příslušný formulář - tohle bude sloužit pro založení předmětů, organizačních účtů atd..
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
import NabidkaForm from "@components/Forms/NabidkaForm";
import { useCodeListAPI } from "src/api/code_list/code_listAPI";
import { useUserAPI } from "src/api/user/userAPI";
import { useNabidkaAPI } from "src/api/nabidka/nabidkaAPI";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import Paragraph from "@components/core/Text/Paragraph";
import handleToDoAlert from "@utils/ToDoAlert";
import { useUser } from "@hooks/UserProvider";
import SubjectForm from "@components/Forms/SubjectForm";
import UserForm from "@components/Forms/UserForm";

export default function FormPage() {
    const [searchParams] = useSearchParams();
    const [formData, setFormData] = useState({});

    useEffect(() => {
        const type = searchParams.get('type');
        const action = searchParams.get('action');
        const id = searchParams.get('id');
        console.log('Type:', type);
        console.log('Action:', action);
        console.log('ID:', id);
        // PODLE ACTIONU UDĚLAT FETCH
    }, [searchParams]);

    const handleCreate = (data) => {
        console.log('Ukládám data:', data);
        // Zde bude API volání pro uložení
    };

    const renderForm = () => {
        const type = searchParams.get('type');
        
        switch(type) {
            case 'subject':
                return <SubjectForm formData={formData} handleCreate={handleCreate} />;
            case 'org_users':
                return <UserForm organizationUser={true}/>;
            default:
                return <Paragraph>Neznámý typ formuláře</Paragraph>;
        }
    };
    
    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <BackButton/>
                <Container property={"bg-gray-50 mt-2 p-4 rounded-lg"}>
                    {renderForm()}
                </Container>
            </Container>
        </Container>
    )
}