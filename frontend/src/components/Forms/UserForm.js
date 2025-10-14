import React, {useState, useEffect} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import BackButton from "@core/Button/BackButton";
import TextBox from "@core/Form/TextBox";
import Nav from "@components/core/Nav";
import CustomDatePicker from "@core/Form/DatePicker";
import Button from "@components/core/Button/Button";
import Headings from "@core/Text/Headings";
import handleToDoAlert from "@utils/ToDoAlert";
import { useSearchParams } from "react-router-dom";
import { useUserAPI } from "src/api/user/userAPI";

export default function UserForm({ organizationUser = false, action, id, handleCreate, handleUpdate }) {
    const [formData, setFormData] = useState({
        name: "",
        surname: "",
        titleBefore: "",
        titleAfter: "",
        email: "",
        phone: "",
        company: "",
        role: "",
        password: "",
        passwordConfirm: ""
    });
    const [loading, setLoading] = useState(false);
    const userAPI = useUserAPI();
    const isEditing = action === 'edit';

    useEffect(() => {
        if (isEditing && id) {
            loadUser();
        }
    }, [action, id]);

    const loadUser = async () => {
        try {
            setLoading(true);
            const user = await userAPI.getUserById(id);
            if (user) {
                setFormData({
                    name: user.first_name || "",
                    surname: user.last_name || "",
                    titleBefore: user.title_before || "",
                    titleAfter: user.title_after || "",
                    email: user.email || "",
                    phone: user.phone || "",
                    company: user.company || "",
                    role: user.role || "",
                    password: "",
                    passwordConfirm: ""
                });
            }
        } catch (error) {
            console.error('Chyba při načítání uživatele:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleInputChange = (field, value) => {
        setFormData(prev => ({
            ...prev,
            [field]: value
        }));
    };

    const handleSubmit = () => {
        // Validation for passwords
        if (!isEditing && formData.password !== formData.passwordConfirm) {
            console.error('Hesla se neshodují');
            return;
        }

        // Prepare data for API
        const userData = {
            first_name: formData.name,
            last_name: formData.surname,
            title_before: formData.titleBefore,
            title_after: formData.titleAfter,
            email: formData.email,
            phone: formData.phone,
            company: formData.company,
            role: formData.role
        };

        // Add password only for create or if password is provided for update
        if (!isEditing || formData.password) {
            userData.password = formData.password;
            userData.password2 = formData.passwordConfirm;
        }

        if (isEditing) {
            handleUpdate(userData);
        } else {
            handleCreate(userData);
        }
    };

    if (loading) {
        return <Container property={"text-center py-4"}>Načítání...</Container>;
    }

    return(
        <>
        <Container property={"mb-6"}>
            <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                {isEditing ? 'Upravit uživatele' : 'Údaje uživatele'}
            </Headings>
        </Container>
        {/* Osobní údaje sekce */}
        <Container property={"mb-6"}>
            <Container property={"grid gap-4 grid-cols-3"}>
                <TextField 
                    id={"name"}
                    required={true}
                    label={"Jméno"} 
                    placeholder={"Jméno"}
                    value={formData.name}
                    onChange={(value) => handleInputChange('name', value.name)}
                />
                <TextField 
                    id={"surname"}
                    required={true}
                    label={"Příjmení"} 
                    placeholder={"Příjmení"}
                    value={formData.surname}
                    onChange={(value) => handleInputChange('surname', value.surname)}
                />
                <DropDown
                    id={"titleBefore"}
                    required={false}
                    label={"Titul před"}
                    placeholder={"Titul před"}
                    value={formData.titleBefore}
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
                    value={formData.titleAfter}
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
                    value={formData.email}
                    onChange={(value) => handleInputChange('email', value.email)}
                />

                <TextField 
                    id={"phone"}
                    required={true}
                    label={"Telefon"} 
                    placeholder={"Telefon"}
                    value={formData.phone}
                    onChange={(value) => handleInputChange('phone', value.phone)}
                />

                <DropDown
                    id={"company"}
                    required={true}
                    label={"Přiřadit ke společnosti"}
                    placeholder={"Společnost"}
                    value={formData.company}
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
                    value={formData.role}
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
            <Headings sizeTag={"h5"} property={"mb-4 font-bold"}>
                {isEditing ? 'Změna hesla (volitelné)' : 'Heslo'}
            </Headings>
            
            <Container property={"grid gap-4 grid-cols-2"}>
                <TextField 
                    id={"password"}
                    required={!isEditing}
                    placeholder={"*********"}
                    label={"Heslo"} 
                    type={"password"}
                    value={formData.password}
                    onChange={(value) => handleInputChange('password', value.password)}
                />

                <TextField 
                    id={"passwordConfirm"}
                    required={!isEditing}
                    placeholder={"*********"}
                    label={"Potvrdit heslo"} 
                    type={"password"}
                    value={formData.passwordConfirm}
                    onChange={(value) => handleInputChange('passwordConfirm', value.passwordConfirm)}
                />
            </Container>
        </Container>

        <Container property={"flex w-full justify-end"}>
            <Button 
                property={"px-16 py-2"} 
                onClick={handleSubmit}
            >
                {isEditing ? "Uložit změny" : "Vytvořit"}
            </Button>
        </Container>
        </>
    )
}