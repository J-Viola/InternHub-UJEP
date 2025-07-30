import React from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import TextBox from "@core/Form/TextBox";
import Button from "@components/core/Button/Button";
import UploadFile from "@core/Form/UploadFile";
import Image from "@core/Image/Image";

export default function ProfileForm({ formData, handleInputChange, handleSubmit }) {

    return (
        <>
            <Container property={"grid gap-2 grid-cols-3"}>
                <TextField 
                    id={"first_name"}
                    required={true}
                    label={"Jméno"} 
                    placeholder={"Zadejte jméno"}
                    value={formData?.first_name || ''}
                    onChange={(value) => handleInputChange('first_name', value)}
                />
                
                <TextField 
                    id={"last_name"}
                    required={true}
                    label={"Příjmení"} 
                    placeholder={"Zadejte příjmení"}
                    value={formData?.last_name || ''}
                    onChange={(value) => handleInputChange('last_name', value)}
                />
                
                <TextField 
                    id={"email"}
                    required={true}
                    label={"E-mailová adresa"} 
                    placeholder={"Zadejte e-mailovou adresu"}
                    value={formData?.email || ''}
                    onChange={(value) => handleInputChange('email', value)}
                />
                
                <TextField 
                    id={"phone"}
                    required={false}
                    label={"Telefonní číslo"} 
                    placeholder={"Zadejte telefonní číslo"}
                    value={formData?.phone || ''}
                    onChange={(value) => handleInputChange('phone', value)}
                />
                
                <TextField 
                    id={"title_before"}
                    required={false}
                    label={"Titul před jménem"} 
                    placeholder={"např. Ing., Mgr."}
                    value={formData?.title_before || ''}
                    onChange={(value) => handleInputChange('title_before', value)}
                />
                
                <TextField 
                    id={"title_after"}
                    required={false}
                    label={"Titul za jménem"} 
                    placeholder={"např. Ph.D."}
                    value={formData?.title_after || ''}
                    onChange={(value) => handleInputChange('title_after', value)}
                />
                
                <TextField 
                    id={"street"}
                    required={false}
                    label={"Ulice"} 
                    placeholder={"Zadejte ulici"}
                    value={formData?.street || ''}
                    onChange={(value) => handleInputChange('street', value)}
                />
                
                <TextField 
                    id={"street_number"}
                    required={false}
                    label={"Číslo popisné"} 
                    placeholder={"Zadejte číslo popisné"}
                    value={formData?.street_number || ''}
                    onChange={(value) => handleInputChange('street_number', value)}
                />
                
                <TextField 
                    id={"city"}
                    required={false}
                    label={"Město"} 
                    placeholder={"Zadejte město"}
                    value={formData?.city || ''}
                    onChange={(value) => handleInputChange('city', value)}
                />
                
                <TextField 
                    id={"zip_code"}
                    required={false}
                    label={"PSČ"} 
                    placeholder={"Zadejte PSČ"}
                    value={formData?.zip_code || ''}
                    onChange={(value) => handleInputChange('zip_code', value)}
                />
                
                <TextField 
                    id={"field_of_study"}
                    required={false}
                    label={"Obor"} 
                    placeholder={"Zadejte obor studia"}
                    value={formData?.field_of_study || ''}
                    onChange={(value) => handleInputChange('field_of_study', value)}
                />
                
                <TextField 
                    id={"specialization"}
                    required={false}
                    label={"Specializace"} 
                    placeholder={"Zadejte specializaci"}
                    value={formData?.specialization || ''}
                    onChange={(value) => handleInputChange('specialization', value)}
                />
                
                <TextField 
                    id={"year_of_study"}
                    required={false}
                    label={"Ročník"} 
                    placeholder={"Zadejte ročník"}
                    value={formData?.year_of_study || ''}
                    onChange={(value) => handleInputChange('year_of_study', value)}
                />
                
                {/*<TextField 
                    id={"company_name"}
                    required={false}
                    label={"Název firmy"} 
                    placeholder={"Zadejte název firmy"}
                    value={formData?.employer_profile?.company_name || ''}
                    onChange={(value) => handleInputChange('company_name', value)}
                />
                
                <TextField 
                    id={"ico"}
                    required={false}
                    label={"IČO"} 
                    placeholder={"Zadejte IČO"}
                    value={formData?.employer_profile?.ico || ''}
                    onChange={(value) => handleInputChange('ico', value)}
                />
                
                <TextField 
                    id={"address"}
                    required={false}
                    label={"Adresa organizace"} 
                    placeholder={"Zadejte adresu organizace"}
                    value={formData?.employer_profile?.address || ''}
                    onChange={(value) => handleInputChange('address', value)}
                />
                
                <TextField 
                    id={"organization_city"}
                    required={false}
                    label={"Město organizace"} 
                    placeholder={"Zadejte město organizace"}
                    value={formData?.employer_profile?.city || ''}
                    onChange={(value) => handleInputChange('organization_city', value)}
                />*/}
            </Container>

            <Container property={"w-full gap-2 mt-2 flex-cols"}>
                <TextBox
                    id={"additional_info"}
                    required={false}
                    label={"O mě"}
                    placeholder={"Napište něco o sobě"}
                    value={formData?.additional_info || ''}
                    onChange={(value) => handleInputChange('additional_info', value)}
                />
                
                <TextBox
                    id={"skills"}
                    required={false}
                    label={"Moje schopnosti"}
                    placeholder={"Popište svoje znalosti, zkušenosti a dovednosti"}
                    value={formData?.skills || ''}
                    onChange={(value) => handleInputChange('skills', value)}
                />
            </Container>

            <Container property={"w-full gap-2 mt-2 flex-cols"}>
                {/* Aktuální profilový obrázek */}
                {formData?.profile_picture && (
                    <Container property="mb-4">
                        <Container property="text-sm font-medium text-gray-700 mb-2">
                            Aktuální profilový obrázek:
                        </Container>
                        <Container property="w-32 h-32 bg-blue-600 rounded-lg p-4 flex items-center justify-center">
                            <Image
                                src={formData.profile_picture}
                                alt="Profilový obrázek"
                                width="100%"
                                height="100%"
                                objectFit="cover"
                                borderRadius="0.5rem"
                                property="w-full h-full"
                            />
                        </Container>
                    </Container>
                )}
                
                {/* Upload nového obrázku */}
                <UploadFile
                    id={"profile_picture"}
                    label={"Nahrát nový profilový obrázek"}
                    accept={"image/*"}
                    onChange={(file) => handleInputChange('profile_picture', file)}
                />
                {/*<UploadFile
                    id={"resume"}
                    label={"CV/Životopis"}
                    accept={".pdf,.doc,.docx"}
                    onChange={(file) => handleInputChange('resume', file)}
                />*/}
            </Container>

            <Container property={"flex justify-end mt-4"}>
                <Button 
                    onClick={handleSubmit}
                >
                    Uložit
                </Button>
            </Container>
        </>
    );
} 