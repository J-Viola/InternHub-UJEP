import React, {useState} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import BackButton from "@core/Button/BackButton";
import TextBox from "@core/Form/TextBox";
import Nav from "@components/core/Nav";
import CustomDatePicker from "@core/Form/DatePicker";
import Button from "@components/core/Button/Button";

export default function VytvoritNabidkuForm() {

    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");

    return(
            <>
                <Container property={"grid gap-2 grid-cols-2"}>
                    <CustomDatePicker
                        id={"startDate"}
                        selected={startDate}
                        label={"Čas období od"}
                        required={true}
                        onChange={(value) => console.log(value)}
                    />

                    <CustomDatePicker
                        id={"endDate"}
                        selected={endDate}
                        label={"Čas období do"}
                        required={true}
                        onChange={(value) => console.log(value)}
                    />

                    <DropDown
                        id={"spravceInzeratu"}
                        required={true}
                        label={"Správce inzerátu"}
                        icon={"user"}
                        options={[
                            { value: "1", label: "volba1" },
                            { value: "2", label: "volba2" }
                        ]}
                        onChange={(value) => console.log(value)}
                    />

                    <DropDown
                        id={"predmet"}
                        required={true}
                        label={"Přiřazený předmět"}
                        icon={"book"}
                        options={[
                            { value: "1", label: "volba1" },
                            { value: "2", label: "volba2" }
                        ]}
                        onChange={(value) => console.log(value)}
                    />
                </Container>

                <Container property={"w-full gap-2 mt-2 flex-cols"}>

                    <TextField 
                        id={"nazev"}
                        required={true}
                        label={"Název"} 
                        placeholder={"Název stáže"}
                        onChange={(value) => console.log(value)}
                    />

                    <TextBox
                        id={"popisStaze"}
                        required={true}
                        label={"Popis stáže"}
                        placeholder={"Napište popis stáže"}
                        onChange={(value) => console.log(value)}
                    />

                    <TextBox
                        id={"odpovednostStaze"}
                        required={true}
                        label={"Odpovědnost stáže"}
                        placeholder={"Popište odpovědnost stáže"}
                        onChange={(value) => console.log(value)}
                    />
                </Container>


                {/* PROSTOR PRO TLAČÍKO */}
                <Container property={"flex w-full justify-end ml-auto"}>
                    <Button 
                        property={"mt-2 px-16"} 
                        onClick={() => console.log("Vytvářim nabídku")}
                    >
                        Vytvořit
                    </Button>
                </Container>
            </>
        )
}
