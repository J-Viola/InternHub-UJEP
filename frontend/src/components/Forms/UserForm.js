import React, {useState} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import BackButton from "@core/Button/BackButton";
import TextBox from "@core/Form/TextBox";
import Nav from "@components/core/Nav";
import CustomDatePicker from "@core/Form/DatePicker";
import Button from "@components/core/Button/Button";
import Headings from "@core/Text/Headings";

export default function UserForm({ organizationUser = false }) {
    const [formData, setFormData] = useState({});

    const handleInputChange = (field, value) => {
        setFormData(prev => ({
            ...prev,
            [field]: value
        }));
    };

    return(
        <>
        {/* Osobní údaje sekce */}
        <Container property={"mb-6"}>
            <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                Osobní údaje
            </Headings>
            
            <Container property={"grid gap-4 grid-cols-3"}>
                <TextField 
                    id={"name"}
                    required={true}
                    label={"Jméno"} 
                    placeholder={"Jméno"}
                    onChange={(value) => handleInputChange('name', value.name)}
                />
                <TextField 
                    id={"surname"}
                    required={true}
                    label={"Příjmení"} 
                    placeholder={"Příjmení"}
                    onChange={(value) => handleInputChange('surname', value.surname)}
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
                    onChange={(value) => handleInputChange('titleBefore', value.titleBefore)}
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
                    onChange={(value) => handleInputChange('titleAfter', value.titleAfter)}
                />

                <TextField 
                    id={"email"}
                    required={true}
                    label={"E-mail"} 
                    placeholder={"E-mail"}
                    onChange={(value) => handleInputChange('email', value.email)}
                />

                <TextField 
                    id={"phone"}
                    required={true}
                    label={"Telefon"} 
                    placeholder={"Telefon"}
                    onChange={(value) => handleInputChange('phone', value.phone)}
                />

                <DropDown
                    id={"company"}
                    required={true}
                    label={"Přiřadit ke společnosti"}
                    placeholder={"Společnost"}
                    options={[
                        { value: "1", label: "Apple" },
                        { value: "2", label: "BMW" },
                        { value: "3", label: "Microsoft" }
                    ]}
                    onChange={(value) => handleInputChange('company', value.company)}
                />

                <DropDown
                    id={"role"}
                    required={true}
                    label={"Role"}
                    placeholder={"Role"}
                    options={[
                        { value: "OWNER", label: "Jednatel firmy" },
                        { value: "INSERTER", label: "Správce inzerátů" }
                    ]}
                    onChange={(value) => handleInputChange('role', value.role)}
                />
            </Container>
        </Container>

        {/* Heslo sekce */}
        <Container property={"mb-6"}>
            <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                Heslo
            </Headings>
            
            <Container property={"grid gap-4 grid-cols-2"}>
                <TextField 
                    id={"password"}
                    required={true}
                    placeholder={"*********"}
                    label={"Heslo"} 
                    type={"password"}
                    onChange={(value) => handleInputChange('password', value.password)}
                />

                <TextField 
                    id={"passwordConfirm"}
                    required={true}
                    placeholder={"*********"}
                    label={"Potvrdit heslo"} 
                    type={"password"}
                    onChange={(value) => handleInputChange('passwordConfirm', value.passwordConfirm)}
                />
            </Container>
        </Container>

        <Container property={"flex w-full justify-end"}>
            <Button 
                property={"px-16 py-2"} 
                onClick={() => console.log("Vytvářím uživatele:", formData)}
            >
                Vytvořit
            </Button>
        </Container>
        </>
    )
}