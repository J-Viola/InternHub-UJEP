import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Headings from "@core/Text/Headings";
import Nav from "@core/Nav";
import Paragraph from "@components/core/Text/Paragraph";
import { useUserAPI } from "@api/user/userAPI";
import { useParams, useSearchParams } from "react-router-dom";
import handleToDoAlert from "@utils/ToDoAlert";
import ProfileForm from "@components/Forms/ProfileForm";
import { useNavigate } from "react-router-dom";
import Image from "@core/Image/Image";

import { useMessage } from "@hooks/MessageContext";

export default function ProfilPage() {
    const { getCurrentUserProfile, getStudentProfile, updateProfile } = useUserAPI();
    const [userData, setUserData] = useState(null);
    const [loading, setLoading] = useState(true);
    const { id } = useParams();
    const [searchParams] = useSearchParams();
    const isEditMode = searchParams.get('edit') === 'true';
    const navigate = useNavigate();
    const { addMessage } = useMessage();
    // přidělat check na param id -> pak bud tahadam data ciziho profilu, nebo svůj

    useEffect(() => {
        const fetchUserData = async () => {
            try {
                setLoading(true);

                let data;
                if (id) {
                    data = await getStudentProfile(id);
                } else {
                    data = await getCurrentUserProfile();
                }
                if (data) setUserData(data);
            } catch (error) {
                console.error(error);
            } finally {
                setLoading(false);
            }
        };

        fetchUserData();
    }, []);

    const handleInputChange = (value) => {
        setUserData(prevValue => ({
            ...prevValue,
            ...value
        }));
    }

    const handleSubmit = async () => {
        try {
            await updateProfile(userData);
            addMessage("Profil byl úspěšně aktualizován", "S");
            navigate(-1);
        } catch (error) {
            console.error('Error profile update:', error);
            addMessage("Chyba při aktualizaci profilu", "E");
        }
    }

    if (loading) {
        return (
            <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
                <BackButton/>
                <Headings sizeTag={"h2"}>Načítání...</Headings>
            </ContainerForEntity>
        );
    }

    if (!userData) {
        return (
            <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
                <BackButton/>
                <Headings sizeTag={"h2"}>Profil nenalezen</Headings>
            </ContainerForEntity>
        );
    }

    return(
        <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
            <BackButton/>
            
            {isEditMode ? (
                <ProfileForm 
                    formData={userData} 
                    handleInputChange={handleInputChange} 
                    handleSubmit={handleSubmit} 
                />
            ) : (
                // Zobrazení profilu
                <>
                    <Container property="grid grid-cols-[auto,1fr] gap-4 mt-2 mb-8">
                        
                        {/* PROFILE PIC */}
                        <Container property="w-32 h-32 bg-blue-600 rounded-lg p-4 flex items-center justify-center">
                            {userData.profile_picture ? (
                                <Image
                                    src={userData.profile_picture}
                                    alt="Profilový obrázek"
                                    width="100%"
                                    height="100%"
                                    objectFit="cover"
                                />
                            ) : (
                                <Headings sizeTag="h4" property="text-white">
                                    {userData.first_name?.charAt(0) || "U"}
                                </Headings>
                            )}
                        </Container>

                        {/* USER NAME */}
                        <Container property="flex flex-col justify-center">
                            <Headings sizeTag={"h2"} property={"mb-2"}>
                                {userData.full_name || `${userData.first_name} ${userData.last_name}`}
                            </Headings>
                            <Paragraph property="text-gray-600">
                                {userData.email}
                            </Paragraph>
                            {userData.role && (
                                <Paragraph property="text-blue-600 font-medium">
                                    {userData.role}
                                </Paragraph>
                            )}
                        </Container>

                    </Container>

                    <Container property={"w-full mt-2 grid-cols-1 space-y-6"}>

                        {/* O MĚ */}
                        {userData.additional_info && (
                            <Container property="p-1 space-y-1 mb-4">
                                <Headings sizeTag={"h4"}>O mě</Headings>
                                <Paragraph>
                                    {userData.additional_info}
                                </Paragraph>
                            </Container>
                        )}

                        {/* OSOBNÍ ÚDAJE */}
                        <Container property="p-1 space-y-1">
                            <Headings sizeTag={"h4"}>Osobní údaje</Headings>
                            <Container property="grid grid-cols-1 md:grid-cols-2 gap-4">
                                <Container>
                                    <Paragraph property="font-medium">Jméno:</Paragraph>
                                    <Paragraph>{userData.first_name}</Paragraph>
                                </Container>
                                <Container>
                                    <Paragraph property="font-medium">Příjmení:</Paragraph>
                                    <Paragraph>{userData.last_name}</Paragraph>
                                </Container>
                                <Container>
                                    <Paragraph property="font-medium">Email:</Paragraph>
                                    <Paragraph>{userData.email}</Paragraph>
                                </Container>
                                {userData.phone && (
                                    <Container>
                                        <Paragraph property="font-medium">Telefon:</Paragraph>
                                        <Paragraph>{userData.phone}</Paragraph>
                                    </Container>
                                )}
                                {userData.title_before && (
                                    <Container>
                                        <Paragraph property="font-medium">Titul před:</Paragraph>
                                        <Paragraph>{userData.title_before}</Paragraph>
                                    </Container>
                                )}
                                {userData.title_after && (
                                    <Container>
                                        <Paragraph property="font-medium">Titul za:</Paragraph>
                                        <Paragraph>{userData.title_after}</Paragraph>
                                    </Container>
                                )}
                            </Container>
                        </Container>

                        {/* TRVALÉ BYDLIŠTĚ - pouze pro studenty */}
                        {userData.user_type === 'student' && (userData.street || userData.city) && (
                            <Container property="p-1 space-y-1">
                                <Headings sizeTag={"h4"}>Trvalé bydliště</Headings>
                                <Container property="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {userData.street && (
                                        <Container>
                                            <Paragraph property="font-medium">Ulice:</Paragraph>
                                            <Paragraph>{userData.street} {userData.street_number}</Paragraph>
                                        </Container>
                                    )}
                                    {userData.city && (
                                        <Container>
                                            <Paragraph property="font-medium">Město:</Paragraph>
                                            <Paragraph>{userData.city}</Paragraph>
                                        </Container>
                                    )}
                                    {userData.zip_code && (
                                        <Container>
                                            <Paragraph property="font-medium">PSČ:</Paragraph>
                                            <Paragraph>{userData.zip_code}</Paragraph>
                                        </Container>
                                    )}
                                </Container>
                            </Container>
                        )}

                        {/* STUDIJNÍ INFORMACE - pouze pro studenty */}
                        {userData.user_type === 'student' && (userData.field_of_study || userData.specialization) && (
                            <Container property="p-1 space-y-1">
                                <Headings sizeTag={"h4"}>Studijní informace</Headings>
                                <Container property="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {userData.field_of_study && (
                                        <Container>
                                            <Paragraph property="font-medium">Obor:</Paragraph>
                                            <Paragraph>{userData.field_of_study}</Paragraph>
                                        </Container>
                                    )}
                                    {userData.specialization && (
                                        <Container>
                                            <Paragraph property="font-medium">Specializace:</Paragraph>
                                            <Paragraph>{userData.specialization}</Paragraph>
                                        </Container>
                                    )}
                                    {userData.year_of_study && (
                                        <Container>
                                            <Paragraph property="font-medium">Ročník:</Paragraph>
                                            <Paragraph>{userData.year_of_study}</Paragraph>
                                        </Container>
                                    )}
                                </Container>
                            </Container>
                        )}

                        {/* ORGANIZACE - pouze pro organizační uživatele */}
                        {userData.user_type === 'organization' && userData.employer_profile && (
                            <Container property="p-1 space-y-1">
                                <Headings sizeTag={"h4"}>Organizace</Headings>
                                <Container property="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {userData.employer_profile.company_name && (
                                        <Container>
                                            <Paragraph property="font-medium">Název firmy:</Paragraph>
                                            <Paragraph>{userData.employer_profile.company_name}</Paragraph>
                                        </Container>
                                    )}
                                    {userData.employer_profile.ico && (
                                        <Container>
                                            <Paragraph property="font-medium">IČO:</Paragraph>
                                            <Paragraph>{userData.employer_profile.ico}</Paragraph>
                                        </Container>
                                    )}
                                    {userData.employer_profile.address && (
                                        <Container>
                                            <Paragraph property="font-medium">Adresa:</Paragraph>
                                            <Paragraph>{userData.employer_profile.address}</Paragraph>
                                        </Container>
                                    )}
                                    {userData.employer_profile.city && (
                                        <Container>
                                            <Paragraph property="font-medium">Město:</Paragraph>
                                            <Paragraph>{userData.employer_profile.city}</Paragraph>
                                        </Container>
                                    )}
                                </Container>
                            </Container>
                        )}

                        {/* SKILLS - pouze pro studenty */}
                        {userData.user_type === 'student' && userData.skills && userData.skills.length > 0 && (
                            <Container property="p-1 space-y-1">
                                <Headings sizeTag={"h4"}>Skills</Headings>
                                <div className="flex flex-wrap gap-2">
                                    {userData.skills.map((skill, index) => (
                                        <span key={index} className="bg-blue-100 text-blue-800 text-sm font-medium mr-2 px-2.5 py-0.5 rounded">
                                            {skill}
                                        </span>
                                    ))}
                                </div>
                            </Container>
                        )}

                        {/* CV - pouze pro studenty */}
                        {userData.user_type === 'student' && userData.cv_file && (
                            <Container property="p-1 space-y-1">
                                <Headings sizeTag={"h4"}>CV</Headings>
                                <a href={userData.cv_file} target="_blank" rel="noopener noreferrer" className="text-blue-600 hover:underline flex items-center gap-2">
                                    <Button icon="download" noVariant={true} iconColor="text-blue-600" />
                                    Stáhnout CV
                                </a>
                            </Container>
                        )}

                    </Container>

                    {/* EDIT PROFILE BUTTON */}
                    <Container property="flex items-center justify-end gap-2">
                        {!id && userData.user_type === 'student' && (
                            <Button 
                                onClick={() => navigate(`/moje-prihlasky`)} 
                                icon={"list"}
                                variant="secondary"
                            >
                                Moje přihlášky
                            </Button>
                        )}
                        {!id && userData.user_type !== 'student' && userData.user_type !== 'professor' && (
                            <Button 
                                onClick={() => navigate(`/change-password`)} 
                                icon={"lock"}
                                variant="secondary"
                            >
                                Změnit heslo
                            </Button>
                        )}
                        <Button 
                            onClick={() => navigate(`/profil/${id ? id :""}?edit=true`)} 
                            icon={"edit"}
                        >
                            Upravit profil
                        </Button>
                    </Container>
                </>
            )}

        </ContainerForEntity>
    )
}