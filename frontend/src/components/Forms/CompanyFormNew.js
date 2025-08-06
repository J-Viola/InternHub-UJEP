import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import TextBox from "@core/Form/TextBox";
import TextField from "@core/Form/TextField";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useCompanyAPI } from "@api/company/companyAPI";
import { useMessage } from "@hooks/MessageContext";

export default function CompanyFormNew() {
    const [searchParams] = useSearchParams();
    const action = searchParams.get('action');
    const id = searchParams.get('id');
    const navigate = useNavigate();
    const companyAPI = useCompanyAPI();
    const { showMessage } = useMessage();

    const [formData, setFormData] = useState({
        company_name: '',
        ico: '',
        dic: '',
        address: '',
        zip_code: '',
        company_profile: ''
    });

    const [loading, setLoading] = useState(false);

    useEffect(() => {
        if (action === 'edit' && id) {
            loadCompany();
        }
    }, [action, id]);

    const loadCompany = async () => {
        try {
            setLoading(true);
            const company = await companyAPI.getCompanyById(id);
            if (company) {
                setFormData({
                    company_name: company.company_name || '',
                    ico: company.ico || '',
                    dic: company.dic || '',
                    address: company.address || '',
                    zip_code: company.zip_code || '',
                    company_profile: company.company_profile || ''
                });
            }
        } catch (error) {
            showMessage('Chyba při načítání společnosti', 'error');
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

    const handleSubmit = async (e) => {
        e.preventDefault();
        
        if (!formData.company_name.trim()) {
            showMessage('Název společnosti je povinný', 'error');
            return;
        }

        if (!formData.ico.trim()) {
            showMessage('IČO je povinné', 'error');
            return;
        }

        try {
            setLoading(true);
            
            if (action === 'create') {
                await companyAPI.createCompany(formData);
                showMessage('Společnost byla úspěšně vytvořena', 'success');
            } else if (action === 'edit') {
                await companyAPI.updateCompany(id, formData);
                showMessage('Společnost byla úspěšně aktualizována', 'success');
            }
            
            navigate('/companies');
        } catch (error) {
            showMessage('Chyba při ukládání společnosti', 'error');
        } finally {
            setLoading(false);
        }
    };

    const getTitle = () => {
        if (action === 'create') return 'Vytvořit novou společnost';
        if (action === 'edit') return 'Upravit společnost';
        return 'Formulář společnosti';
    };

    return (
        <Container>
            <Headings sizeTag={"h2"} property={"mb-6"}>
                {getTitle()}
            </Headings>

            <form onSubmit={handleSubmit}>
                <Container property={"space-y-6"}>
                    <Container>
                        <TextBox
                            id="company_name"
                            label="Název společnosti"
                            value={formData.company_name}
                            onChange={(value) => handleInputChange('company_name', value.company_name)}
                            placeholder="Zadejte název společnosti"
                            required
                            rows={1}
                        />
                    </Container>

                    <Container property="grid grid-cols-2 gap-4">
                        <Container>
                            <TextField
                                id="ico"
                                label="IČO"
                                value={formData.ico}
                                onChange={(value) => handleInputChange('ico', value.ico)}
                                placeholder="Zadejte IČO"
                                required
                            />
                        </Container>
                        <Container>
                            <TextField
                                id="dic"
                                label="DIČ"
                                value={formData.dic}
                                onChange={(value) => handleInputChange('dic', value.dic)}
                                placeholder="Zadejte DIČ"
                            />
                        </Container>
                    </Container>

                    <Container property="grid grid-cols-2 gap-4">
                        <Container>
                            <TextBox
                                id="address"
                                label="Adresa"
                                value={formData.address}
                                onChange={(value) => handleInputChange('address', value.address)}
                                placeholder="Zadejte adresu"
                                rows={2}
                            />
                        </Container>
                        <Container>
                            <TextField
                                id="zip_code"
                                label="PSČ"
                                value={formData.zip_code}
                                onChange={(value) => handleInputChange('zip_code', value.zip_code)}
                                placeholder="Zadejte PSČ"
                            />
                        </Container>
                    </Container>

                    <Container>
                        <TextBox
                            id="company_profile"
                            label="Profil společnosti"
                            value={formData.company_profile}
                            onChange={(value) => handleInputChange('company_profile', value.company_profile)}
                            placeholder="Zadejte popis společnosti"
                            rows={4}
                        />
                    </Container>

                    <Container property={"flex gap-4 pt-6"}>
                        <Button
                            type="submit"
                            disabled={loading}
                            icon={action === 'create' ? 'plus' : 'save'}
                        >
                            {loading ? 'Ukládám...' : (action === 'create' ? 'Vytvořit společnost' : 'Uložit změny')}
                        </Button>
                        
                        <Button
                            type="button"
                            variant="gray"
                            onClick={() => navigate('/companies')}
                            disabled={loading}
                        >
                            Zrušit
                        </Button>
                    </Container>
                </Container>
            </form>
        </Container>
    );
} 