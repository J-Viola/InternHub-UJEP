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
import { useUserAPI } from "@api/user/userAPI";
import CompanyForm from "@components/Forms/CompanyForm";

// UDĚLAT POLE PRO TITULY - PŘED A ZA + HANDLER NA SUCCESS REGISTRACI
export default function RegistracePage() {
    const ares = useAresAPI();
    const user = useUserAPI();
    const [entity, setEntity] = useState(null);
    const [formValue, setFormValue] = useState({});

    useEffect(() => {
        console.log("Form value:", formValue);
    }, [formValue]);

    const handleARESCall = async (ico) => {
        try {
            const res = await ares.getData(ico);
            console.log("ARES response:", res);
            if (res) {
                setEntity(res);
                // CHATKEM přidané hodnoty přímo z ARESU do dat k zaslání - musíme prodiskutoivat
                setFormValue(prevValue => ({
                    ...prevValue,
                    ico: res.ico,
                    //company_name: res.obchodniJmeno,
                    //address: res.sidlo ? 
                    //    `${res.sidlo.nazevUlice ? res.sidlo.nazevUlice : ''} ${res.sidlo.cisloDomovni}${res.sidlo.cisloOrientacni ? '/' + res.sidlo.cisloOrientacni : ''}, ${res.sidlo.nazevCastiObce}, ${res.sidlo.psc} ${res.sidlo.nazevObce}` : 
                    //    '',
                    //dic: res.dic,
                    //legal_form: res.pravniForma,
                    //establishment_date: res.datumVzniku,
                    //financial_office: res.financniUrad
                }));
            }
        } catch (error) {
            console.error("Error ARES fetch:", error);
            throw error;
        }
    }

    const handleFormValues = (value) => {
        setFormValue(prevValue => ({
            ...prevValue,
            ...value
        }));
    }

    const handleFileChange = (file) => {
        console.log("File changed:", file);
        setFormValue(prevValue => ({
            ...prevValue,
            logo: file
        }));
    }

    const handleRegistration = async () => {
        try {
            const dataToSend = {
                ...formValue,
                
            }
            console.log("Sending registration data:", formValue);
            const res = await user.postRegister(formValue);
            console.log("Registration response:", res);
            res && setEntity(res);
        } catch (error) {
            console.error("Error registration fetch:", error);
            throw error;
        }
    }

    const renderForm = () => {
        return <CompanyForm 
            entity={entity} 
            handleARESCall={handleARESCall} 
            handleFormValues={handleFormValues}
            handleRegistration={handleRegistration}
            handleFileChange={handleFileChange}
        />;
    };

    return(
        <Container property={"min-h-screen"}>
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <BackButton></BackButton>
                <Container property={"bg-gray-50 mt-2 p-4 rounded-lg"}>
                    {renderForm()}
                </Container>
            </Container>
        </Container>
    );
}