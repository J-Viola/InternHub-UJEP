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

export default function CompanyForm({entity, aresFetched, handleARESCall, handleFormValues, handleRegistration, handleFileChange, action = "create"}) {
    const ares = useAresAPI();
    const { addMessage } = useMessage();
    const [ico, setICO] = useState('');
    const [formData, setFormData] = useState({});

    useEffect(() => {
        console.log('CompanyForm - action:', action);
        console.log('CompanyForm - entity:', entity);
        console.log('CompanyForm - aresFetched:', aresFetched);
    }, [action, entity, aresFetched]);

    // Validace povinných polí
    const validateForm = () => {
        const requiredFields = {
            'executiveName': 'Jméno jednatele',
            'executiveSurname': 'Příjmení jednatele',
            'executiveEmail': 'E-mailová adresa jednatele',
            'executivePhone': 'Telefonní číslo jednatele',
            'executivePassword1': 'Heslo',
            'executivePassword2': 'Heslo znovu'
        };

        const missingFields = [];

        // Kontrola, zda byly načteny údaje z ARES pomocí aresFetched prop
        if (!aresFetched) {
            addMessage("Nejprve načtěte údaje z ARES", "E");
            return false;
        }
        
        for (const [fieldId, fieldName] of Object.entries(requiredFields)) {
            if (!formData[fieldId] || formData[fieldId].trim() === '') {
                missingFields.push(fieldName);
            }
        }

        // Kontrola, zda jsou hesla stejná
        if (formData.executivePassword1 && formData.executivePassword2 && 
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
        handleFormValues(value);
    };

    const handleRegistrationClick = () => {
        if (validateForm()) {
            handleRegistration();
        }
    };

    return(
            <>
                {action !== "edit" && (
                    <Container property={"grid gap-2 grid-cols-2"}>
                        <TextField 
                            id={"ico"}
                            required={true}
                            label={"Vyplnění údajů pomocí systému ARES"} 
                            placeholder={"Zadejte IČO firmy"}
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

                <Container property={"grid gap-2 grid-cols-2"}>
                    <TextField 
                        id={"companyName"}
                        required={true}
                        label={"Název společnosti"} 
                        value={entity?.obchodniJmeno}
                        placeholder={"Zadejte název společnosti"}
                        onChange={(value) => handleFormChange(value)}
                        disabled={true}
                    />

                    <TextField 
                        id={"address"}
                        required={true}
                        label={"Adresa"} 
                        value={entity?.sidlo?.textovaAdresa || ''}
                        placeholder={"Zadejte adresu"}
                        onChange={(value) => handleFormChange(value)}
                        disabled={true}
                    />

                    <TextField 
                        id={"titleBefore"}
                        required={false}
                        label={"Titul před jménem"} 
                        placeholder={"např. Ing., Mgr., Dr."}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField 
                        id={"executiveName"}
                        required={true}
                        label={"Jméno jednatele"} 
                        placeholder={"Zadejte jméno jednatele"}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField 
                        id={"executiveSurname"}
                        required={true}
                        label={"Příjmení jednatele"} 
                        placeholder={"Zadejte příjmení jednatele"}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField 
                        id={"titleAfter"}
                        required={false}
                        label={"Titul za jménem"} 
                        placeholder={"např. Ph.D., MBA"}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField 
                        id={"executiveEmail"}
                        required={true}
                        label={"E-mailová adresa jednatele"} 
                        placeholder={"Zadejte e-mailovou adresu jednatele"}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField 
                        id={"executivePhone"}
                        required={true}
                        label={"Telefonní číslo jednatele"} 
                        placeholder={"Zadejte telefonní číslo jednatele"}
                        onChange={(value) => handleFormChange(value)}
                    />

                    {/*<DropDown
                        id={"kategorie"}
                        required={true}
                        label={"Vyberte kategorii"}
                        //icon={"eye"}
                        options={[
                            { value: "1", label: "GEJ" },
                            { value: "2", label: "NE GEJ" }
                        ]}
                        onChange={(value) => console.log(value)}
                    />*/}

                </Container>

                <Container property={"grid grid-cols-2 gap-2 mt-2"}>
                    <TextField 
                        id={"executivePassword1"}
                        required={true}
                        label={"Heslo"} 
                        placeholder={"Zadejte heslo"}
                        type={"password"}
                        onChange={(value) => handleFormChange(value)}
                    />

                    <TextField 
                        id={"executivePassword2"}
                        required={true}
                        label={"Heslo znovu"} 
                        placeholder={"Zadejte heslo znovu"}
                        type={"password"}
                        onChange={(value) => handleFormChange(value)}
                    />
                </Container>
                
                <UploadFile 
                    id="companyLogo"
                    property={"mt-4"}
                    onChange={handleFileChange}
                    label={"Nahrát logo organizace"}
                    accept="image/*"
                    previewOn={true}
                />

                <Container property={"flex w-full justify-end ml-auto mt-4"}>
                    <Button 
                        property={"mt-2 px-16"} 
                        icon={action == "edit" ? "edit" : ""}
                        onClick={handleRegistration ? handleRegistrationClick : () => console.log("Není handler")}
                        disabled={action == "edit" ? true : false}
                    >
                        {action == "edit" ? "Upravit profil" : "Dokončit registraci"}
                    </Button>

                </Container>
            </>
        )
}