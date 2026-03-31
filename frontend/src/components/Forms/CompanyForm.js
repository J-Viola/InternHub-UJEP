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
import { useTranslation } from "react-i18next";
import { validateEmail, validateICO, validateRequired, validatePassword } from "@utils/validationUtils";

export default function CompanyForm({ handleCreate, handleUpdate, action, id, errors = {} }) {
    const { t } = useTranslation();
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
            console.error('Error loading company:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleARESCall = async (icoValue) => {
        setLocalErrors({}); // Clear previous local errors
        setSearchResults([]); // Clear previous results
        if (!validateRequired(icoValue)) {
            setLocalErrors(prev => ({ ...prev, ico: t('employer.ares_fill') }));
            addMessage(t('employer.ares_fill'), "E");
            return;
        }

        if (!validateICO(icoValue)) {
            setLocalErrors(prev => ({ ...prev, ico: t('company.invalid_ico') }));
            addMessage(t('company.invalid_ico'), "E");
            return;
        }

        try {
            setLoading(true);
            const response = await ares.getEntityByICO(icoValue);
            if (response) {
                // ARES typically returns one specific entity for an ICO
                setSearchResults([response]);
                addMessage(t('employer.ares_success'), "S");
            } else {
                addMessage(t('employer.ares_error'), "W");
            }
        } catch (error) {
            setLocalErrors(prev => ({ ...prev, ico: t('employer.ares_error') }));
            addMessage(t('employer.ares_error'), "E");
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
        addMessage(t('company.prefilled_success'), "S");
    };

    const validateForm = () => {
        const newLocalErrors = {};
        let isValid = true;

        const requiredFields = {
            'executiveName': t('employer.executive_name'),
            'executiveSurname': t('employer.executive_surname'),
            'executiveEmail': t('employer.executive_email'),
            'executivePhone': t('employer.executive_phone'),
            'companyName': t('company.name_label'),
            'address': t('profile.address')
        };

        if (!isEditing) {
            requiredFields['executivePassword1'] = t('login.password');
            requiredFields['executivePassword2'] = t('login.password');
        }

        if (!aresFetched && !isEditing) {
            newLocalErrors.ico = t('employer.ares_needed');
            isValid = false;
        }

        for (const [fieldId, fieldName] of Object.entries(requiredFields)) {
            if (!validateRequired(formData[fieldId])) {
                newLocalErrors[fieldId] = t('company.is_required', { field: fieldName });
                isValid = false;
            }
        }

        if (formData.executiveEmail && !validateEmail(formData.executiveEmail)) {
            newLocalErrors.executiveEmail = t('login.invalid_email');
            isValid = false;
        }

        if (!isEditing && formData.executivePassword1 && !validatePassword(formData.executivePassword1)) {
            newLocalErrors.executivePassword1 = t('login.password_min_length', { length: 8 });
            isValid = false;
        }

        if (!isEditing && formData.executivePassword1 && formData.executivePassword2 &&
            formData.executivePassword1 !== formData.executivePassword2) {
            newLocalErrors.executivePassword2 = t('employer.password_mismatch');
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
        return <Container property={"text-center py-4"}>{t('common.loading')}</Container>;
    }

    return(
            <>
                <Container>
                     <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                        {isEditing ? t('company.edit_title') : t('company.data_title')}
                    </Headings>
                </Container>
                {!isEditing && (
                    <Container property={"mb-8"}>
                        <Container property={"grid gap-4 grid-cols-[1fr,auto] items-end mb-4"}>
                            <TextField
                                id={"ico"}
                                required={true}
                                label={t('company.ico_placeholder')}
                                placeholder={"12345678"}
                                value={icoValue}
                                onChange={(value) => setICOValue(value.ico)}
                                property={"w-full"}
                                error={localErrors.ico || errors.ico}
                            />
                            <Button
                                property={"px-8 h-[45px] mb-[1px]"}
                                onClick={() => handleARESCall(icoValue)}
                                variant={"blueSmall"}
                            >
                                {t('common.search')}
                            </Button>
                        </Container>

                        {/* Search Results Section */}
                        {searchResults.length > 0 && (
                            <Container property="bg-blue-50 border-2 border-blue-200 rounded-xl p-6 mt-4 shadow-sm animate-fadeIn">
                                <Headings sizeTag="h5" property="mb-4 font-black uppercase tracking-wider text-blue-900 border-b border-blue-200 pb-2">
                                    {t('company.search_results')}
                                </Headings>
                                {searchResults.map((result, index) => (
                                    <div key={index} className="flex flex-col md:flex-row justify-between items-center p-4 bg-white rounded-lg border border-blue-100 hover:border-blue-300 transition-all shadow-sm">
                                        <div className="flex flex-col mb-4 md:mb-0">
                                            <span className="font-black text-xl text-gray-900">{result.obchodniJmeno}</span>
                                            <div className="flex gap-4 mt-1">
                                                <span className="text-sm font-bold text-blue-700 bg-blue-100 px-2 py-0.5 rounded">{t('profile.ico')}: {result.ico}</span>
                                                {result.dic && <span className="text-sm font-bold text-gray-600">DIČ: {result.dic}</span>}
                                            </div>
                                            <span className="text-sm text-gray-500 mt-1 italic">{result.sidlo?.textovaAdresa}</span>
                                        </div>
                                        <Button
                                            variant="greenSmall"
                                            onClick={() => selectCompany(result)}
                                            icon="check"
                                            property="whitespace-nowrap px-6"
                                        >
                                            {t('company.select')}
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
                        label={t('company.name_label')}
                        value={formData.companyName}
                        placeholder={t('company.name_placeholder')}
                        onChange={(value) => handleFormChange(value)}
                        disabled={!isEditing && aresFetched}
                        error={localErrors.companyName || errors.company_name}
                    />

                    <TextField
                        id={"address"}
                        required={true}
                        label={t('profile.address')}
                        value={formData.address}
                        placeholder={t('profile.address')}
                        onChange={(value) => handleFormChange(value)}
                        disabled={!isEditing && aresFetched}
                        error={localErrors.address || errors.address}
                    />

                    <TextField
                        id={"titleBefore"}
                        required={false}
                        label={t('profile.title_before')}
                        placeholder={t('profile.title_before_placeholder')}
                        value={formData.titleBefore}
                        onChange={(value) => handleFormChange(value)}
                        error={localErrors.titleBefore || errors.title_before}
                    />

                    <TextField
                        id={"executiveName"}
                        required={true}
                        label={t('employer.executive_name')}
                        placeholder={t('profile.first_name_placeholder')}
                        value={formData.executiveName}
                        onChange={(value) => handleFormChange(value)}
                        error={localErrors.executiveName || errors.first_name}
                    />

                    <TextField
                        id={"executiveSurname"}
                        required={true}
                        label={t('employer.executive_surname')}
                        placeholder={t('profile.last_name_placeholder')}
                        value={formData.executiveSurname}
                        onChange={(value) => handleFormChange(value)}
                        error={localErrors.executiveSurname || errors.last_name}
                    />

                    <TextField
                        id={"titleAfter"}
                        required={false}
                        label={t('profile.title_after')}
                        placeholder={t('profile.title_after_placeholder')}
                        value={formData.titleAfter}
                        onChange={(value) => handleFormChange(value)}
                        error={localErrors.titleAfter || errors.title_after}
                    />

                    <TextField
                        id={"executiveEmail"}
                        required={true}
                        label={t('employer.executive_email')}
                        placeholder={t('profile.email_placeholder')}
                        value={formData.executiveEmail}
                        onChange={(value) => handleFormChange(value)}
                        error={localErrors.executiveEmail || errors.email}
                    />

                    <TextField
                        id={"executivePhone"}
                        required={true}
                        label={t('employer.executive_phone')}
                        placeholder={t('profile.phone_placeholder')}
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
                            label={t('login.password')}
                            placeholder={"******"}
                            type={"password"}
                            value={formData.executivePassword1}
                            onChange={(value) => handleFormChange(value)}
                            error={localErrors.executivePassword1 || errors.password}
                        />

                        <TextField
                            id={"executivePassword2"}
                            required={true}
                            label={t('login.password')}
                            placeholder={"******"}
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
                    label={t('employer.upload_logo')}
                    accept="image/*"
                    previewOn={true}
                />

                <Container property={"flex w-full justify-end ml-auto mt-4"}>
                    <Button
                        property={"mt-2 px-16"}
                        onClick={handleSubmit}
                    >
                        {isEditing ? t('form.save_changes') : t('company.create_button')}
                    </Button>

                </Container>
            </>
        )
}
