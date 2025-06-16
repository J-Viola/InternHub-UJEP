import CompanyForm from "@components/Forms/CompanyForm"
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

export default function RegistracePage() {
    const [entity, setEntity] = useState({});
    const ares = useAresAPI();

    useEffect(() => {
        console.log("Nastavuji entitu")
        console.log(entity)
    },[entity])

    const handleARESCall = async (ico) => {
        try {
            const res = await ares.getData(ico);
            console.log("RES", res)
            res && setEntity(res);
        } catch (error) {
            console.error("Error ARES fetch:", error);
            throw error;
        }
    };

    const renderForm = () => {
        return <CompanyForm entity={entity} handleARESCall={handleARESCall}/>;
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
    )
}