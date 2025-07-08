import React, {useState} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import BackButton from "@core/Button/BackButton";
import TextBox from "@core/Form/TextBox";
import Nav from "@components/core/Nav";
import CustomDatePicker from "@core/Form/DatePicker";
import Button from "@components/core/Button/Button";

export default function UserForm() {
    return(
        <>
        <Container property={"grid gap-2 grid-cols-3"}>
            <TextField 
                id={"name"}
                required={true}
                label={"Jméno"} 
                placeholder={"Zadejte jméno"}
                onChange={(value) => console.log(value)}
            />
            <TextField 
                id={"surname"}
                required={true}
                label={"Příjmení"} 
                placeholder={"Zadejte příjmení"}
                onChange={(value) => console.log(value)}
            />

            <CustomDatePicker
                id={"birthDate"}
                selected={birthDate}
                label={"Datum narození"}
                required={true}
                onChange={(value) => console.log(value)}
            />

            <TextField 
                id={"email"}
                required={true}
                label={"E-mailová adresa"} 
                placeholder={"Zadejte e-mailovou adresu"}
                onChange={(value) => console.log(value)}
            />

            <TextField 
                id={"phone"}
                required={true}
                label={"Telefonní číslo"} 
                placeholder={"Zadejte svoje telefonní číslo"}
                onChange={(value) => console.log(value)}
            />

            <TextField 
                id={"birthPlace"}
                required={true}
                label={"Místo narození"} 
                placeholder={"Místo narození"}
                onChange={(value) => console.log(value)}
            />

            <TextField 
                id={"city"}
                required={true}
                label={"Město"} 
                placeholder={"Město"}
                onChange={(value) => console.log(value)}
            />

            <TextField 
                id={"street"}
                required={true}
                label={"Ulice"} 
                placeholder={"Ulice"}
                onChange={(value) => console.log(value)}
            />

            <TextField 
                id={"houseNum"}
                required={true}
                label={"Číslo popisné"} 
                placeholder={"Číslo popisné"}
                onChange={(value) => console.log(value)}
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

        <TextBox
            id={"aboutMe"}
            required={true}
            label={"O mě"}
            placeholder={"Napište něco o sobě"}
            onChange={(value) => console.log(value)}
        />

        <TextBox
            id={"skills"}
            required={true}
            label={"Moje schopnosti"}
            placeholder={"Popište svoje znalosti, zkušenosti a dovednosti, které můžete firmě nabídnout"}
            onChange={(value) => console.log(value)}
        />

        <Button 
            property={"w-full px-2 py-1 text-base text-gray-900 bg-gray-100 rounded-lg border-2 mt-2 hover:bg-gray-200"} 
            noVariant={true}
            icon={"upload"}
            iconColor="text-gray-900"
            onClick={() => console.log("Nahraju profile pic")}
        >
            
            Nahrát profilový obrázek
        </Button>

        <Container property={"flex w-full justify-end ml-auto"}>
            <Button 
                property={"mt-2 px-16"} 
                onClick={() => console.log("Ukládám vole")}
            >
                Uložit
            </Button>

    </Container>
    </>
    )
}