import React, {useState} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import BackButton from "@core/Button/BackButton";
import TextBox from "@core/Form/TextBox";
import Nav from "@components/core/Nav";
import CustomDatePicker from "@core/Form/DatePicker";
import Button from "@components/core/Button/Button";

export default function VytvoritNabidkuForm({organizationUsers, subjects, formData, handleChange, handleSubmit}) {

    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const uvazek = [
        {"label": 0.5, "value" : "0.5"},
        {"label": 1, "value" : "1"}
    ]

    const availablePositions = [
        {"label": 1, "value": "1"},
        {"label": 2, "value": "2"},
        {"label": 3, "value": "3"},
        {"label": 4, "value": "4"},
        {"label": 5, "value": "5"},
        {"label": 6, "value": "6"},
        {"label": 7, "value": "7"},
        {"label": 8, "value": "8"},
        {"label": 9, "value": "9"},
        {"label": 10, "value": "10"}
    ]


    return(
            <>
                <Container property={"grid gap-2 grid-cols-2"}>
                    <CustomDatePicker
                        id={"start_date"}
                        value={formData?.start_date}
                        label={"Čas období od"}
                        required={true}
                        onChange={handleChange}
                    />

                    
                    <DropDown
                        id={"coefficient"}
                        required={true}
                        label={"Úvazek"}
                        options={uvazek}
                        onChange={handleChange}
                    />

                    <CustomDatePicker
                        id={"end_date"}
                        locked={true}
                        value={formData?.end_date}
                        label={"Čas období do"}
                        required={true}
                        onChange={handleChange}
                    />

                    <DropDown
                        id={"contact_user"}
                        required={true}
                        label={"Správce inzerátu"}
                        icon={"user"}
                        options={organizationUsers}
                        onChange={handleChange}
                    />

                    <DropDown
                        id={"subject_id"}
                        required={true}
                        label={"Přiřazený předmět"}
                        icon={"book"}
                        options={subjects}
                        onChange={handleChange}
                    />

                    <DropDown
                        id={"available_positions"}
                        required={true}
                        label={"Počet volných míst"}
                        icon={"users"}
                        options={availablePositions}
                        onChange={handleChange}
                    />
                </Container>

                <Container property={"w-full gap-2 mt-2 flex-cols"}>

                    <TextField 
                        id={"title"}
                        required={true}
                        label={"Název"} 
                        placeholder={"Název stáže"}
                        onChange={handleChange}
                    />

                    <TextBox
                        id={"description"}
                        required={true}
                        label={"Popis stáže"}
                        placeholder={"Napište popis stáže"}
                        onChange={handleChange}
                    />

                    <TextBox
                        id={"responsibilities"}
                        required={true}
                        label={"Odpovědnost stáže"}
                        placeholder={"Popište odpovědnost stáže"}
                        onChange={handleChange}
                    />
                </Container>


                {/* PROSTOR PRO TLAČÍKO */}
                <Container property={"flex w-full justify-end ml-auto"}>
                    <Button 
                        property={"mt-2 px-16"} 
                        onClick={() => handleSubmit()}
                    >
                        Vytvořit
                    </Button>
                </Container>
            </>
        )
}
