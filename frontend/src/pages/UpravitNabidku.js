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
import { useNavigate, useParams } from "react-router-dom";
import Paragraph from "@components/core/Text/Paragraph";
import handleToDoAlert from "@utils/ToDoAlert";
import { useUser } from "@hooks/UserProvider";

export default function UpravitNabidku() {
    const [ formData, setFormData ] = useState({})
    const [ subjects, setSubjects ] = useState([])
    const [ organizationUsers, setOrganizationUsers ] = useState([]);
    const [ loading, setLoading ] = useState(true);
    const [ isInitialized, setIsInitialized ] = useState(false);
    const codeList = useCodeListAPI();
    const userAPI = useUserAPI();
    const nabidkaAPI = useNabidkaAPI();
    const navigate = useNavigate();
    const { id } = useParams();
    const { user } = useUser();

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
                        console.log("Hledám uživatele:", fullName);
                        console.log("Dostupní uživatelé:", usersRes);
                        
                        const contactUser = usersRes.find(user => 
                            user.label === fullName
                        );
                        
                        console.log("Nalezený uživatel:", contactUser);
                        
                        if (contactUser) {
                            contactUserId = contactUser.value;
                            console.log("Nastavuji contact_user:", contactUserId);
                        }
                    }
                    
                    const transformedData = {
                        title: practiceRes.title,
                        description: practiceRes.description,
                        responsibilities: practiceRes.responsibilities,
                        available_positions: practiceRes.available_positions,
                        start_date: practiceRes.start_date,
                        end_date: practiceRes.end_date,
                        coefficient: practiceRes.coefficient,
                        subject_id: practiceRes.subject?.subject_id,
                        contact_user: contactUserId,
                        contact_user_info: practiceRes.contact_user_info,
                        image_base64: practiceRes.image_base64
                    };
                    console.log("Transformed data:", transformedData);
                    setFormData(transformedData);
                }
            } catch (error) {
                console.error("Chyba při načítání dat:", error);
            } finally {
                setLoading(false);
                setIsInitialized(true);
            }
        }
        initFetch();
    },[id])


    const handleUpdate = async () => {
        // TODO: Implementovat aktualizaci nabídky (PUT/POST na API, validace, navigace zpět)
        handleToDoAlert();
        /*
        try {
            const res = await nabidkaAPI.updateNabidka(id, formData, false); 
            if (res) {
                navigate(-1);
            }
        } catch (error) {
            console.error("Chyba při aktualizaci nabídky:", error);
        }
        */
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
            console.log("Volám API na endDate")
            handleCalc(formData.start_date, formData.coefficient);
        }
    }, [formData.coefficient, formData.start_date, isInitialized]);

    useEffect(() => {
        console.log("form data", formData);
    }, [formData])

    useEffect(() => {
        console.log("useEffect triggered - organizationUsers:", organizationUsers.length, "formData:", formData);
        
        if (organizationUsers.length > 0 && formData && formData.contact_user_info && !formData.contact_user) {
            const fullName = `${formData.contact_user_info.first_name} ${formData.contact_user_info.last_name}`;
            console.log("Hledám uživatele:", fullName);
            console.log("Dostupní uživatelé:", organizationUsers);
            
            const contactUser = organizationUsers.find(user => 
                user.label === fullName
            );
            
            console.log("Nalezený uživatel:", contactUser);
            
            if (contactUser) {
                console.log("Nastavuji contact_user na:", contactUser.value);
                setFormData(prev => ({
                    ...prev,
                    contact_user: contactUser.value
                }));
            } else {
                console.log("Uživatel nenalezen pro jméno:", fullName);
            }
        } else {
            console.log("Podmínky nesplněny:");
            console.log("- organizationUsers.length > 0:", organizationUsers.length > 0);
            console.log("- formData existuje:", !!formData);
            console.log("- formData.contact_user_info existuje:", !!(formData && formData.contact_user_info));
            console.log("- !formData.contact_user:", !!(formData && !formData.contact_user));
        }
    }, [organizationUsers, formData]);

    if (loading) {
        return (
            <Container property="min-h-screen">
                <Nav/>
                <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                    <BackButton/>
                    <Container property="bg-gray-50 mt-2 p-4 rounded-lg">
                        <Container property="text-center py-8">
                            <Paragraph>Načítání formuláře...</Paragraph>
                        </Container>
                    </Container>
                </Container>
            </Container>
        );
    }

    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <BackButton/>
                <Container property={"bg-gray-50 mt-2 p-4 rounded-lg"}>
                    <Headings className="mb-4">Upravit nabídku</Headings>
                    {user.isDepartmentMg() && ("Editace nabídky nefunguje pro Vaší roli správně..")}
                    <NabidkaForm
                        formData={formData}
                        organizationUsers={organizationUsers}
                        subjects={subjects}
                        handleChange={handleChange}
                        handleSubmit={handleUpdate}
                        isEdit={true}
                    />
                </Container>
            </Container>
        </Container>
    )
}