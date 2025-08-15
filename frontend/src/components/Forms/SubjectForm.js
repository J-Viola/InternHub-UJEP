import React, {useState} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import CustomDatePicker from "@core/Form/DatePicker";
import Button from "@components/core/Button/Button";
import Headings from "@core/Text/Headings";

export default function SubjectForm(formData, handleCreate) {
    return(
        <>
        <Container property={"space-y-6"}>
            {/* Údaje předmětu */}
            <Container property={"space-y-4"}>
                <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                    Údaje předmětu
                </Headings>
                
                <Container property={"grid gap-4 grid-cols-1 md:grid-cols-2"}>
                    <TextField 
                        id={"name"}
                        required={true}
                        label={"Název"} 
                        placeholder={"Název"}
                        onChange={(value) => console.log(value)}
                    />
                    
                    <TextField 
                        id={"subjectCode"}
                        required={true}
                        label={"Kód předmětu"} 
                        placeholder={"Kód"}
                        onChange={(value) => console.log(value)}
                    />

                    <TextField 
                        id={"timeCriterion"}
                        required={true}
                        label={"Časové kritérium"} 
                        placeholder={"Časové kritérium"}
                        onChange={(value) => console.log(value)}
                    />

                    <DropDown 
                        id={"subjectManager"}
                        required={true}
                        label={"Správce předmětu"} 
                        placeholder={"Správce předmětu"}
                        options={[]}
                        onChange={(value) => console.log(value)}
                    />
                    

                </Container>
            </Container>

            <Container property={"flex justify-end"}>
                <Button 
                    property={"px-16 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"} 
                    onClick={() => console.log("Vytvořit předmět")}
                >
                    Vytvořit
                </Button>
            </Container>
        </Container>
        </>
    )
}