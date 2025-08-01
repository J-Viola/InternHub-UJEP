import React, {useState} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import BackButton from "@core/Button/BackButton";
import TextBox from "@core/Form/TextBox";
import Nav from "@components/core/Nav";
import CustomDatePicker from "@core/Form/DatePicker";
import Button from "@components/core/Button/Button";

export default function UserForm({ organizationUser = false }) {
    return(
        <>
        <Container property={"grid gap-2 grid-cols-3"}>
            <TextField 
                id={"name"}
                required={true}
                label={"Jméno"} 
                placeholder={"Jméno"}
                onChange={(value) => console.log(value)}
            />
            <TextField 
                id={"surname"}
                required={true}
                label={"Příjmení"} 
                placeholder={"Příjmení"}
                onChange={(value) => console.log(value)}
            />

            <DropDown
                id={"titleBefore"}
                required={false}
                label={"Titul před"}
                placeholder={"Titul před"}
                options={[
                    { value: "Ing.", label: "Ing." },
                    { value: "Mgr.", label: "Mgr." },
                    { value: "Ph.D.", label: "Ph.D." },
                    { value: "Doc.", label: "Doc." },
                    { value: "Prof.", label: "Prof." }
                ]}
                onChange={(value) => console.log(value)}
            />

            <DropDown
                id={"titleAfter"}
                required={false}
                label={"Titul za"}
                placeholder={"Titul za"}
                options={[
                    { value: "MBA", label: "MBA" },
                    { value: "Ph.D.", label: "Ph.D." },
                    { value: "CSc.", label: "CSc." },
                    { value: "DrSc.", label: "DrSc." }
                ]}
                onChange={(value) => console.log(value)}
            />

            <TextField 
                id={"email"}
                required={true}
                label={"E-mail"} 
                placeholder={"Příjmení"}
                onChange={(value) => console.log(value)}
            />

            <TextField 
                id={"phone"}
                required={true}
                label={"Telefon"} 
                placeholder={"Placeholder"}
                onChange={(value) => console.log(value)}
            />

            {organizationUser && (
                <>
                    <TextField 
                        id={"password"}
                        required={true}
                        placeholder={"*********"}
                        label={"Heslo"} 
                        type={"password"}
                        onChange={(value) => console.log(value)}
                    />

                    <TextField 
                        id={"passwordConfirm"}
                        required={true}
                        placeholder={"*********"}
                        label={"Heslo"} 
                        type={"password"}
                        onChange={(value) => console.log(value)}
                    />
                </>
            )}

            {!organizationUser && (
                <>
                    <CustomDatePicker
                        id={"birthDate"}
                        selected={birthDate}
                        label={"Datum narození"}
                        required={true}
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
                </>
            )}

        </Container>

        {!organizationUser && (
            <>
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
            </>
        )}

        <Container property={"flex w-full justify-end ml-auto"}>
            <Button 
                property={"mt-2 px-16"} 
                onClick={() => console.log("Ukládám vole")}
            >
                {organizationUser ? "Vytvořit" : "Uložit"}
            </Button>
        </Container>
        </>
    )
}