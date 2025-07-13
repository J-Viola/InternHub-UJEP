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
import UploadFile from "@core/Form/UploadFile";

export default function CompanyForm({entity, handleARESCall, handleFormValues, handleRegistration, handleFileChange}) {
    const ares = useAresAPI();
    const [ico, setICO] = useState('');

    //useEffect(() => {
        //console.log(ico);
    //},[ico])

    return(
            <>
                <Container property={"grid gap-2 grid-cols-2"}>
                    <TextField 
                        id={"ico"}
                        required={true}
                        label={"Vyplnění údajů pomocí systému ARES"} 
                        placeholder={"Zadejte IČO firmy"}
                        value={ico[ico]}
                        onChange={(value) => setICO(value)} // to poslouží pro volání ARES api
                        property={"w-full"}
                    />
                    <Button
                        property={"w-1/3 mt-6 px-4 justify-self-end"} 
                        onClick={() => handleARESCall(ico)}
                        variant={"blueSmall"}
                    >
                        Hledat
                    </Button>
                </Container>

                <Container property={"grid gap-2 grid-cols-2"}>
                    <TextField 
                        id={"companyName"}
                        required={true}
                        label={"Název společnosti"} 
                        value={entity?.obchodniJmeno}
                        placeholder={"Zadejte název společnosti"}
                        onChange={(value) => handleFormValues(value)}
                        disabled={true}
                    />

                    <TextField 
                        id={"address"}
                        required={true}
                        label={"Adresa"} 
                        value={entity?.sidlo?.textovaAdresa || ''}
                        placeholder={"Zadejte adresu"}
                        onChange={(value) => handleFormValues(value)}
                        disabled={true}
                    />

                    <TextField 
                        id={"titleBefore"}
                        required={false}
                        label={"Titul před jménem"} 
                        placeholder={"např. Ing., Mgr., Dr."}
                        onChange={(value) => handleFormValues(value)}
                    />

                    <TextField 
                        id={"executiveName"}
                        required={true}
                        label={"Jméno jednatele"} 
                        placeholder={"Zadejte jméno jednatele"}
                        onChange={(value) => handleFormValues(value)}
                    />

                    <TextField 
                        id={"executiveSurname"}
                        required={true}
                        label={"Příjmení jednatele"} 
                        placeholder={"Zadejte příjmení jednatele"}
                        onChange={(value) => handleFormValues(value)}
                    />

                    <TextField 
                        id={"titleAfter"}
                        required={false}
                        label={"Titul za jménem"} 
                        placeholder={"např. Ph.D., MBA"}
                        onChange={(value) => handleFormValues(value)}
                    />

                    <TextField 
                        id={"executiveEmail"}
                        required={true}
                        label={"E-mailová adresa jednatele"} 
                        placeholder={"Zadejte e-mailovou adresu jednatele"}
                        onChange={(value) => handleFormValues(value)}
                    />

                    <TextField 
                        id={"executivePhone"}
                        required={true}
                        label={"Telefonní číslo jednatele"} 
                        placeholder={"Zadejte telefonní číslo jednatele"}
                        onChange={(value) => handleFormValues(value)}
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

                <Container property={"grid grid-cols-2 gap-2 mt-2"}>
                    <TextField 
                        id={"executivePassword1"}
                        required={true}
                        label={"Heslo"} 
                        placeholder={"Zadejte heslo"}
                        type={"password"}
                        onChange={(value) => handleFormValues(value)}
                    />

                    <TextField 
                        id={"executivePassword2"}
                        required={true}
                        label={"Heslo znovu"} 
                        placeholder={"Zadejte heslo znovu"}
                        type={"password"}
                        onChange={(value) => handleFormValues(value)}
                    />
                </Container>
                
                <UploadFile 
                    id="companyLogo"
                    property={"w-full px-2 py-1 text-base text-gray-900 bg-gray-100 rounded-lg border-2 mt-4 hover:bg-gray-200"} 
                    icon={"upload"}
                    iconColor="text-gray-900"
                    onChange={(file) => handleFileChange(file)}
                    label={"Nahrát logo organizace"}
                    accept="image/*"
                    previewOn={true}
                />

                <Container property={"flex w-full justify-end ml-auto mt-4"}>
                    <Button 
                        property={"mt-2 px-16"} 
                        onClick={() => handleRegistration()}
                    >
                        Dokončit registraci
                    </Button>

                </Container>
            </>
        )
}