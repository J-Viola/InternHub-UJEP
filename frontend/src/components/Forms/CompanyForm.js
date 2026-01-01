import React, {useEffect, useState} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import TextBox from "@core/Form/TextBox";
import UploadFile from "@core/Form/UploadFile";
import Button from "@core/Button/Button";
import Headings from "@components/core/Text/Headings";
import { useAresAPI } from "@api/ARES/aresJusticeAPI";
import { useMessage } from "@hooks/MessageContext";
import { useCompanyAPI } from "src/api/company/companyAPI";

export default function CompanyForm({ handleCreate, handleUpdate, action, id, errors = {} }) {
    const ares = useAresAPI();
    const { addMessage } = useMessage();
    const companyAPI = useCompanyAPI();

    const [icoValue, setICOValue] = useState(''); // Local state for ICO input, before it's part of formData
    const [searchResults, setSearchResults] = useState([]); // Array of found companies
    const [entity, setEntity] = useState(null);
    const [aresFetched, setAresFetched] = useState(false);
    const [loading, setLoading] = useState(false);
    const [localErrors, setLocalErrors] = useState({}); // Local state for frontend validation errors

    const [formData, setFormData] = useState({
        companyName: '',
        address: '',
        ico: '',
        dic: '',
        titleBefore: '',
        executiveName: '',
        executiveSurname: '',
        titleAfter: '',
        executiveEmail: '',
        executivePhone: '',
        executivePassword1: '',
        executivePassword2: '',
        logo: null
    });

    const isEditing = action === 'edit';

    useEffect(() => {
        if (isEditing && id) {
            loadCompany();
        }
    }, [action, id]);

    const loadCompany = async () => {
        try {
            setLoading(true);
            const company = await companyAPI.getCompanyById(id);
            if (company) {
                setFormData({
                    companyName: company.company_name || '',
                    address: company.address || '',
                    ico: company.ico || '',
                    dic: company.dic || '',
                    titleBefore: '',
                    executiveName: '',
                    executiveSurname: '',
                    titleAfter: '',
                    executiveEmail: '',
                    executivePhone: '',
                    executivePassword1: '',
                    executivePassword2: '',
                    logo: null
                });
                setEntity({
                    obchodniJmeno: company.company_name,
                    sidlo: { textovaAdresa: company.address }
                });
                setAresFetched(true);
            }
        } catch (error) {
            console.error('Chyba při načítání společnosti:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleARESCall = async (icoValue) => {
        setLocalErrors({}); // Clear previous local errors
        setSearchResults([]); // Clear previous results
        if (!icoValue) {
            setLocalErrors(prev => ({ ...prev, ico: "Zadejte IČO" }));
            addMessage("Zadejte IČO", "E");
            return;
        }

        try {
            setLoading(true);
            const response = await ares.getEntityByICO(icoValue);
            if (response) {
                // ARES typically returns one specific entity for an ICO
                setSearchResults([response]);
                addMessage("Nalezeny údaje v ARES", "S");
            } else {
                addMessage("Žádné údaje pro toto IČO nebyly nalezeny", "W");
            }
        } catch (error) {
            setLocalErrors(prev => ({ ...prev, ico: "Chyba při načítání údajů z ARES" }));
            addMessage("Chyba při načítání údajů z ARES", "E");
        } finally {
            setLoading(false);
        }
    };

    const selectCompany = (company) => {
        setEntity(company);
        setFormData(prev => ({
            ...prev,
            companyName: company.obchodniJmeno || '',
            address: company.sidlo?.textovaAdresa || '',
            ico: company.ico,
            dic: company.dic || ''
        }));
        setAresFetched(true);
        setSearchResults([]); // Clear results after selection
        addMessage("Údaje firmy byly předvyplněny", "S");
    };

    const validateForm = () => {
        const newLocalErrors = {};
        let isValid = true;

        const requiredFields = {
            'executiveName': 'Jméno jednatele',
            'executiveSurname': 'Příjmení jednatele',
            'executiveEmail': 'E-mailová adresa jednatele',
            'executivePhone': 'Telefonní číslo jednatele'
        };

        if (!isEditing) {
            requiredFields['executivePassword1'] = 'Heslo';
            requiredFields['executivePassword2'] = 'Heslo znovu';
        }

        if (!aresFetched && !isEditing) {
            newLocalErrors.ico = "Nejprve načtěte údaje z ARES";
            isValid = false;
        }
        
        for (const [fieldId, fieldName] of Object.entries(requiredFields)) {
            if (!formData[fieldId] || formData[fieldId].trim() === '') {
                newLocalErrors[fieldId] = `${fieldName} je povinné.`;
                isValid = false;
            }
        }

        if (!isEditing && formData.executivePassword1 && formData.executivePassword2 &&
            formData.executivePassword1 !== formData.executivePassword2) {
            newLocalErrors.executivePassword2 = "Hesla se neshodují.";
            isValid = false;
        }

        setLocalErrors(newLocalErrors); // Update local errors state
        return isValid;
    };

    const handleFormChange = (value) => {
        setFormData(prev => ({
            ...prev,
            ...value
        }));
    };

    const handleFileChange = (file) => {
        setFormData(prev => ({
            ...prev,
            logo: file
        }));
    };

    const handleSubmit = () => {
        if (validateForm()) {
            // Prepare data for API
            const companyData = {
                company_name: formData.companyName,
                ico: formData.ico,
                dic: formData.dic,
                address: formData.address,
                company_profile: '',
                first_name: formData.executiveName,
                last_name: formData.executiveSurname,
                title_before: formData.titleBefore,
                title_after: formData.titleAfter,
                email: formData.executiveEmail,
                phone: formData.executivePhone
            };

            if (!isEditing && formData.executivePassword1) {
                companyData.password = formData.executivePassword1;
                companyData.password2 = formData.executivePassword2;
            }

            if (formData.logo) {
                companyData.logo = formData.logo;
            }

            if (isEditing) {
                handleUpdate(companyData);
            } else {
                handleCreate(companyData);
            }
        }
    };

    if (loading) {
        return <Container property={"text-center py-4"}>Načítání...</Container>;
    }

    return(
            <>
                <Container>
                     <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                        {isEditing ? 'Upravit společnost' : 'Údaje firmy'}
                    </Headings>
                </Container>
                {!isEditing && (
                    <Container property={"mb-6"}>
                        <Container property={"grid gap-2 grid-cols-2 mb-2"}>
                            <TextField
                                id={"ico"}
                                required={true}
                                label={"Vyplnění údajů pomocí systému ARES"} 
                                placeholder={"Zadejte IČO firmy"}
                                value={icoValue}
                                onChange={(value) => setICOValue(value.ico)} 
                                property={"w-full"}
                                error={localErrors.ico || errors.ico}
                            />
                            <Button
                                property={"w-1/3 mt-6 px-4 justify-self-end"} 
                                onClick={() => handleARESCall(icoValue)}
                                variant={"blueSmall"}
                            >
                                Hledat
                            </Button>
                        </Container>

                        {/* Search Results Section */}
                        {searchResults.length > 0 && (
                            <Container property="bg-white border border-gray-200 rounded-lg p-4 mt-2 shadow-sm">
                                <Headings sizeTag="h5" property="mb-2 font-bold text-gray-700">Výsledky vyhledávání</Headings>
                                {searchResults.map((result, index) => (
                                    <div key={index} className="flex flex-col md:flex-row justify-between items-center p-3 border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors">
                                        <div className="flex flex-col mb-2 md:mb-0">
                                            <span className="font-bold text-lg">{result.obchodniJmeno}</span>
                                            <span className="text-sm text-gray-600">IČO: {result.ico}</span>
                                            <span className="text-sm text-gray-600">{result.sidlo?.textovaAdresa}</span>
                                        </div>
                                        <Button 
                                            variant="secondary" 
                                            onClick={() => selectCompany(result)}
                                            icon="check"
                                            property="whitespace-nowrap"
                                        >
                                            Vybrat
                                        </Button>
                                    </div>
                                ))}
                            </Container>
                        )}
                    </Container>
                )}

                <Container property={"grid gap-4 grid-cols-1 md:grid-cols-2 mb-6"}>
                    <TextField
                        id={"companyName"}
                        required={true}
                        label={"Název společnosti"} 
                        value={formData.companyName}
                        placeholder={"Zadejte název společnosti"}
                        onChange={(value) => handleFormChange(value)}
                        disabled={!isEditing && aresFetched}
                        error={localErrors.companyName || errors.company_name}
                    />

                    <TextField 
                        id={"address"}
                        required={true}
                        label={"Adresa"} 
                        value={formData.address}
                        placeholder={"Zadejte adresu"}
                        onChange={(value) => handleFormChange(value)}
                        disabled={!isEditing && aresFetched}
                        error={localErrors.address || errors.address}
                    />

                    <TextField 
                        id={"titleBefore"}
                        required={false}
                        label={"Titul před jménem"} 
                        placeholder={"např. Ing., Mgr., Dr."}
                        value={formData.titleBefore}
                        onChange={(value) => handleFormChange(value)}
                        error={localErrors.titleBefore || errors.title_before}
                    />

                    <TextField 
                        id={"executiveName"}
                        required={true}
                        label={"Jméno jednatele"} 
                        placeholder={"Zadejte jméno jednatele"}
                        value={formData.executiveName}
                        onChange={(value) => handleFormChange(value)}
                        error={localErrors.executiveName || errors.first_name}
                    />

                    <TextField 
                        id={"executiveSurname"}
                        required={true}
                        label={"Příjmení jednatele"} 
                        placeholder={"Zadejte příjmení jednatele"}
                        value={formData.executiveSurname}
                        onChange={(value) => handleFormChange(value)}
                        error={localErrors.executiveSurname || errors.last_name}
                    />

                    <TextField 
                        id={"titleAfter"}
                        required={false}
                        label={"Titul za jménem"} 
                        placeholder={"např. Ph.D., MBA"}
                        value={formData.titleAfter}
                        onChange={(value) => handleFormChange(value)}
                        error={localErrors.titleAfter || errors.title_after}
                    />

                    <TextField 
                        id={"executiveEmail"}
                        required={true}
                        label={"E-mailová adresa jednatele"} 
                        placeholder={"Zadejte e-mailovou adresu jednatele"}
                        value={formData.executiveEmail}
                        onChange={(value) => handleFormChange(value)}
                        error={localErrors.executiveEmail || errors.email}
                    />

                    <TextField 
                        id={"executivePhone"}
                        required={true}
                        label={"Telefonní číslo jednatele"} 
                        placeholder={"Zadejte telefonní číslo jednatele"}
                        value={formData.executivePhone}
                        onChange={(value) => handleFormChange(value)}
                        error={localErrors.executivePhone || errors.phone}
                    />
                </Container>

                {!isEditing && (
                    <Container property={"grid grid-cols-1 md:grid-cols-2 gap-4 mb-4"}>
                        <TextField
                            id={"executivePassword1"}
                            required={true}
                            label={"Heslo"}
                            placeholder={"Zadejte heslo"}
                            type={"password"}
                            value={formData.executivePassword1}
                            onChange={(value) => handleFormChange(value)}
                            error={localErrors.executivePassword1 || errors.password}
                        />

                        <TextField
                            id={"executivePassword2"}
                            required={true}
                            label={"Heslo znovu"}
                            placeholder={"Zadejte heslo znovu"}
                            type={"password"}
                            value={formData.executivePassword2}
                            onChange={(value) => handleFormChange(value)}
                            error={localErrors.executivePassword2 || errors.password2}
                        />
                    </Container>
                )}

                <UploadFile 
                    id="companyLogo"
                    property={"mt-4"}
                    onChange={handleFileChange}
                    label={"Nahrát logo organizace"}
                    accept="image/*"
                    previewOn={true}
                />

                <Container property={"flex w-full justify-end ml-auto mt-4"}>
                    <Button 
                        property={"mt-2 px-16"} 
                        onClick={handleSubmit}
                    >
                        {isEditing ? "Uložit změny" : "Vytvořit společnost"}
                    </Button>

                </Container>
            </>
        )
}