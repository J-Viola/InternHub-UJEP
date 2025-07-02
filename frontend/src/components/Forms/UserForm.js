import React, {useState, useEffect} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import BackButton from "@core/Button/BackButton";
import TextBox from "@core/Form/TextBox";
import Nav from "@components/core/Nav";
import CustomDatePicker from "@core/Form/DatePicker";
import Button from "@components/core/Button/Button";

export default function UserForm({userProfile, handleChange}) {

    return(
        <>
        <Container property={"grid gap-2 grid-cols-3"}>
            <TextField 
                id={"first_name"}
                required={true}
                label={"Jméno"} 
                placeholder={"Zadejte jméno"}
                value={userProfile?.first_name || ""}
                onChange={handleChange}
            />
            <TextField 
                id={"last_name"}
                required={true}
                label={"Příjmení"} 
                placeholder={"Zadejte příjmení"}
                value={userProfile?.last_name || ""}
                onChange={handleChange}
            />

            {/* nefunguje kvůli formátu datumu */}
            <CustomDatePicker
                id={"date_of_birth"}
                selected={userProfile?.date_of_birth}
                label={"Datum narození"}
                required={true}
                onChange={handleChange}
            />

            <TextField 
                id={"email"}
                required={true}
                label={"E-mailová adresa"} 
                placeholder={"Zadejte e-mailovou adresu"}
                value={userProfile?.email || ""}
                onChange={handleChange}
            />

            <TextField 
                id={"phone"}
                required={true}
                label={"Telefonní číslo"} 
                placeholder={"Zadejte svoje telefonní číslo"}
                value={userProfile?.phone || ""}
                onChange={handleChange}
            />

            <TextField 
                id={"place_of_birth"}
                required={true}
                label={"Místo narození"} 
                placeholder={"Místo narození"}
                value={userProfile?.place_of_birth || ""}
                onChange={handleChange}
            />

            <TextField 
                id={"city"}
                required={true}
                label={"Město"} 
                placeholder={"Město"}
                value={userProfile?.city || ""}
                onChange={handleChange}
            />

            <TextField 
                id={"street"}
                required={true}
                label={"Ulice"} 
                placeholder={"Ulice"}
                value={userProfile?.street || ""}
                onChange={handleChange}
            />

            <TextField 
                id={"street_number"}
                required={true}
                label={"Číslo popisné"} 
                placeholder={"Číslo popisné"}
                value={userProfile?.street_number || ""}
                onChange={handleChange}
            />

            <TextField 
                id={"zip_code"}
                required={true}
                label={"PSČ"} 
                placeholder={"PSČ"}
                value={userProfile?.zip_code || ""}
                onChange={handleChange}
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
            id={"additional_info"}
            required={true}
            label={"O mě"}
            placeholder={"Napište něco o sobě"}
            value={userProfile?.additional_info || ""}
            onChange={handleChange}
        />

        <TextBox
            id={"resume"}
            required={true}
            label={"Moje schopnosti"}
            placeholder={"Popište svoje znalosti, zkušenosti a dovednosti, které můžete firmě nabídnout"}
            value={userProfile?.resume || ""}
            onChange={handleChange}
        />

        {/* DODĚLAT SKILLS - multipicker */}

        {/* DODĚLAT HANDLER - na upload obrázků */}
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
                onClick={() => console.log("Ukládám vole", userProfile)}
            >
                Uložit
            </Button>

    </Container>
    </>
    )
}