import React, {useEffect, useState} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import BackButton from "@core/Button/BackButton";
import TextBox from "@core/Form/TextBox";
import Nav from "@components/core/Nav";
import CustomDatePicker from "@core/Form/DatePicker";
import Button from "@components/core/Button/Button";
import { useAresAPI } from "@api/ARES/aresJusticeAPI";
import UploadFile from "@core/Form/UploadFile";
import { useMessage } from "@hooks/MessageContext";
import Headings from "@core/Text/Headings";
import { useEmployerAPI } from "src/api/employer/employerAPI";

export default function EmployerForm({ handleCreate, handleUpdate, action, id }) {
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
            console.error('Chyba při načítání zaměstnavatele:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleARESCall = async (icoValue) => {
        if (!icoValue) {
            addMessage("Zadejte IČO", "E");
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
                addMessage("Údaje byly úspěšně načteny z ARES", "S");
            }
        } catch (error) {
            addMessage("Chyba při načítání údajů z ARES", "E");
        } finally {
            setLoading(false);
        }
    };

    const validateForm = () => {
        const requiredFields = {
            'executiveName': 'Jméno jednatele',
            'executiveSurname': 'Příjmení jednatele',
            'executiveEmail': 'E-mailová adresa jednatele',
            'executivePhone': 'Telefonní číslo jednatele'
        };

        if (!isEditing) {
            requiredFields['executivePassword1'] = 'Heslo';
            requiredFields['executivePassword2'] = 'Heslo znovu';
        }

        const missingFields = [];

        if (!aresFetched && !isEditing) {
            addMessage("Nejprve načtěte údaje z ARES", "E");
            return false;
        }
        
        for (const [fieldId, fieldName] of Object.entries(requiredFields)) {
            if (!formData[fieldId] || formData[fieldId].trim() === '') {
                missingFields.push(fieldName);
            }
        }

        if (!isEditing && formData.executivePassword1 && formData.executivePassword2 && 
            formData.executivePassword1 !== formData.executivePassword2) {
            addMessage("Hesla se neshodují", "E");
            return false;
        }

        if (missingFields.length > 0) {
            addMessage(`Chybí povinné údaje: ${missingFields.join(', ')}`, "E");
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
            // Prepare data for API
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
        return <Container property={"text-center py-4"}>Načítání...</Container>;
    }

    return(
            <>
                <Container>
                     <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                        {isEditing ? 'Upravit zaměstnavatele' : 'Údaje zaměstnavatele'}
                    </Headings>
                </Container>
                {!isEditing && (
                    <Container property={"grid gap-2 grid-cols-2 mb-4"}>
                        <TextField 
                            id={"ico"}
                            required={true}
                            label={"Vyplnění údajů pomocí systému ARES"} 
                            placeholder={"Zadejte IČO"}
                            value={ico}
                            onChange={(value) => setICO(value.ico)} 
                            property={"w-full"}
                        />
                        <Button
                            property={"w-1/3 mt-6 px-4 justify-self-end"} 
                            onClick={() => handleARESCall(ico)}
                            variant={"blueSmall"}
                        >
                            Hledat
                        </Button>
                    </Container>
                )}

                <Container property={"grid gap-4 grid-cols-1 md:grid-cols-2 mb-6"}>
                    <TextField 
                        id={"employerName"}
                        required={true}
                        label={"Název zaměstnavatele"} 
                        value={formData.employerName}
                        placeholder={"Zadejte název zaměstnavatele"}
                        onChange={(value) => handleFormChange(value)}
                        disabled={!isEditing && aresFetched}
                    />

                    <TextField 
                        id={"address"}
                        required={true}
                        label={"Adresa"} 
                        value={formData.address}
                        placeholder={"Zadejte adresu"}
                        onChange={(value) => handleFormChange(value)}
                        disabled={!isEditing && aresFetched}
                    />

                    <TextField 
                        id={"titleBefore"}
                        required={false}
                        label={"Titul před jménem"} 
                        placeholder={"např. Ing., Mgr., Dr."}
                        value={formData.titleBefore}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField 
                        id={"executiveName"}
                        required={true}
                        label={"Jméno jednatele"} 
                        placeholder={"Zadejte jméno jednatele"}
                        value={formData.executiveName}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField 
                        id={"executiveSurname"}
                        required={true}
                        label={"Příjmení jednatele"} 
                        placeholder={"Zadejte příjmení jednatele"}
                        value={formData.executiveSurname}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField 
                        id={"titleAfter"}
                        required={false}
                        label={"Titul za jménem"} 
                        placeholder={"např. Ph.D., MBA"}
                        value={formData.titleAfter}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField 
                        id={"executiveEmail"}
                        required={true}
                        label={"E-mailová adresa jednatele"} 
                        placeholder={"Zadejte e-mailovou adresu jednatele"}
                        value={formData.executiveEmail}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField 
                        id={"executivePhone"}
                        required={true}
                        label={"Telefonní číslo jednatele"} 
                        placeholder={"Zadejte telefonní číslo jednatele"}
                        value={formData.executivePhone}
                        onChange={(value) => handleFormChange(value)}
                    />
                </Container>

                {!isEditing && (
                    <Container property={"grid grid-cols-1 md:grid-cols-2 gap-4 mb-4"}>
                        <TextField 
                            id={"executivePassword1"}
                            required={true}
                            label={"Heslo"} 
                            placeholder={"Zadejte heslo"}
                            type={"password"}
                            value={formData.executivePassword1}
                            onChange={(value) => handleFormChange(value)}
                        />

                        <TextField 
                            id={"executivePassword2"}
                            required={true}
                            label={"Heslo znovu"} 
                            placeholder={"Zadejte heslo znovu"}
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
                    label={"Nahrát logo organizace"}
                    accept="image/*"
                    previewOn={true}
                />

                <Container property={"flex w-full justify-end ml-auto mt-4"}>
                    <Button 
                        property={"mt-2 px-16"} 
                        onClick={handleSubmit}
                    >
                        {isEditing ? "Uložit změny" : "Vytvořit zaměstnavatele"}
                    </Button>
                </Container>
            </>
        )
}
