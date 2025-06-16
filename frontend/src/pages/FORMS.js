import React, {useState} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import BackButton from "@core/Button/BackButton";
import TextBox from "@core/Form/TextBox";
import Nav from "@components/core/Nav";
import CustomDatePicker from "@core/Form/DatePicker";
import Button from "@components/core/Button/Button";


export default function ProfileForm() {

    // datum narození
    const [birthDate, setBirthDate] = useState("");

    // DEBUG
    const [isStudent, setIsStudent] = useState(true);

    // formuláře proiflu - student
    const studentForm = () => {
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

    const companyForm = () => {
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

    // switch pro formuláře profilu
    const handleFormRender = () => {
        // pokud budeš mít roli ze session/param, tak to vykresli podle role
        return isStudent ? studentForm() : companyForm();
    }

    return(
        <Container property={"min-h-screen"}>
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <BackButton></BackButton>
                {/* DEBUG BUTTON - PŘEPÍNAČ */}
                <Button
                    property={"px-16 ml-4"} 
                    onClick={() => setIsStudent(!isStudent)}
                >
                    Přepni se na jiný formulář
                </Button>
                <Container property={"bg-gray-50 mt-2 p-4 rounded-lg"}>
                    {handleFormRender()}
                </Container>
            </Container>

        </Container>
    )
}

