import React, {useState} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import BackButton from "@core/Button/BackButton";
import TextBox from "@core/Form/TextBox";
import Nav from "@components/core/Nav";
import CustomDatePicker from "@core/Form/DatePicker";
import Button from "@components/core/Button/Button";


export default function CompanyForm() {
 return(
        <>
            <Container property={"grid gap-2 grid-cols-3"}>
                <TextField 
                    id={"companyName"}
                    required={true}
                    label={"Vyplnění údajů pomocí systému ARES"} 
                    placeholder={"Zadejte název firmy"}
                    onChange={(value) => console.log(value)}
                    property={"w-full"}
                />
                <Button
                    property={"w-1/3 mt-6 px-4 justify-self-end"} 
                    onClick={() => console.log("Vyplním údaje pomocí systému ARES")}
                    variant={"blueSmall"}
                >
                    Hledat
                </Button>
            </Container>

            <Container property={"grid gap-2 grid-cols-3"}>
                <TextField 
                    id={"companyName"}
                    required={true}
                    label={"Název společnosti"} 
                    placeholder={"Zadejte název společnosti"}
                    onChange={(value) => console.log(value)}
                />

                <TextField 
                    id={"ico"}
                    required={true}
                    label={"IČO"} 
                    placeholder={"Zadejte IČO"}
                    onChange={(value) => console.log(value)}
                />

                <TextField 
                    id={"address"}
                    required={true}
                    label={"Adresa"} 
                    placeholder={"Zadejte adresu"}
                    onChange={(value) => console.log(value)}
                />

                <TextField 
                    id={"executiveName"}
                    required={true}
                    label={"Jméno jednatele"} 
                    placeholder={"Zadejte jméno a příjmení jednatele"}
                    onChange={(value) => console.log(value)}
                />

                <TextField 
                    id={"executiveSurname"}
                    required={true}
                    label={"Příjmení jednatele"} 
                    placeholder={"Zadejte příjmení jednatele"}
                    onChange={(value) => console.log(value)}
                />

                <TextField 
                    id={"executiveEmail"}
                    required={true}
                    label={"E-mailová adresa jednatele"} 
                    placeholder={"Zadejte e-mailovou adresu jednatele"}
                    onChange={(value) => console.log(value)}
                />

                <TextField 
                    id={"executivePhone"}
                    required={true}
                    label={"Telefonní číslo jednatele"} 
                    placeholder={"Zadejte telefonní číslo jednatele"}
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

            <Container property={"flex w-full justify-start gap-2 mt-4 ml-auto"}>
                <TextField 
                    id={"executivePassword1"}
                    required={true}
                    label={"Heslo"} 
                    placeholder={"Zadejte heslo"}
                    type={"password"}
                    onChange={(value) => console.log(value)}
                />

                <TextField 
                    id={"executivePassword2"}
                    required={true}
                    label={"Heslo znovu"} 
                    placeholder={"Zadejte heslo znovu"}
                    type={"password"}
                    onChange={(value) => console.log(value)}
                />

            </Container>
            
            <Button 
                property={"w-full px-2 py-1 text-base text-gray-900 bg-gray-100 rounded-lg border-2 mt-2 hover:bg-gray-200"} 
                noVariant={true}
                icon={"upload"}
                iconColor="text-gray-900"
                onClick={() => console.log("Nahraju logo organizace")}
            >
                Nahrát logo organizace
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