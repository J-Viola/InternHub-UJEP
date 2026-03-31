import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import { useUserAPI } from "@api/user/userAPI";
import { useParams, useSearchParams } from "react-router-dom";
import ProfileForm from "@components/Forms/ProfileForm";
import { useNavigate } from "react-router-dom";
import Image from "@core/Image/Image";
import { useTranslation } from "react-i18next";

import { useMessage } from "@hooks/MessageContext";

export default function ProfilPage() {
    const { t } = useTranslation();
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
            addMessage(t('profile.update_success'), "S");
            navigate(-1);
        } catch (error) {
            console.error('Error profile update:', error);
            const errorCode = error.code || "UNKNOWN_ERROR";
            addMessage(t(`api_errors.${errorCode}`, { defaultValue: t('profile.update_error') }), "E");
        }
    }

    if (loading) {
        return (
            <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
                <BackButton/>
                <Headings sizeTag={"h2"}>{t('common.loading')}</Headings>
            </ContainerForEntity>
        );
    }

    if (!userData) {
        return (
            <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
                <BackButton/>
                <Headings sizeTag={"h2"}>{t('profile.not_found')}</Headings>
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
                                    alt={t('profile.personal_info')}
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

                    <Container property={"w-full mt-2 grid-cols-1 space-y-10"}>

                        {/* OSOBNÍ ÚDAJE */}
                        <Container property="p-1 space-y-4">
                            <Headings sizeTag={"h4"} property="border-b border-gray-200 pb-2">{t('profile.personal_info')}</Headings>
                            <Container property="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-4">
                                <Container>
                                    <Paragraph property="text-gray-500 text-sm mb-0.5">{t('profile.first_name')}</Paragraph>
                                    <Paragraph property="font-medium text-lg">{userData.first_name}</Paragraph>
                                </Container>
                                <Container>
                                    <Paragraph property="text-gray-500 text-sm mb-0.5">{t('profile.last_name')}</Paragraph>
                                    <Paragraph property="font-medium text-lg">{userData.last_name}</Paragraph>
                                </Container>
                                <Container>
                                    <Paragraph property="text-gray-500 text-sm mb-0.5">{t('profile.email')}</Paragraph>
                                    <Paragraph property="font-medium text-lg">{userData.email}</Paragraph>
                                </Container>
                                {userData.phone && (
                                    <Container>
                                        <Paragraph property="text-gray-500 text-sm mb-0.5">{t('profile.phone')}</Paragraph>
                                        <Paragraph property="font-medium text-lg">{userData.phone}</Paragraph>
                                    </Container>
                                )}
                                {userData.title_before && (
                                    <Container>
                                        <Paragraph property="text-gray-500 text-sm mb-0.5">{t('profile.title_before')}</Paragraph>
                                        <Paragraph property="font-medium text-lg">{userData.title_before}</Paragraph>
                                    </Container>
                                )}
                                {userData.title_after && (
                                    <Container>
                                        <Paragraph property="text-gray-500 text-sm mb-0.5">{t('profile.title_after')}</Paragraph>
                                        <Paragraph property="font-medium text-lg">{userData.title_after}</Paragraph>
                                    </Container>
                                )}
                            </Container>
                        </Container>

                        {/* TRVALÉ BYDLIŠTĚ - pouze pro studenty */}
                        {userData.user_type === 'student' && (userData.street || userData.city) && (
                            <Container property="p-1 space-y-4">
                                <Headings sizeTag={"h4"} property="border-b border-gray-200 pb-2">{t('profile.residence')}</Headings>
                                <Container property="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-4">
                                    {userData.street && (
                                        <Container>
                                            <Paragraph property="text-gray-500 text-sm mb-0.5">{t('profile.street')}</Paragraph>
                                            <Paragraph property="font-medium text-lg">{userData.street} {userData.street_number}</Paragraph>
                                        </Container>
                                    )}
                                    {userData.city && (
                                        <Container>
                                            <Paragraph property="text-gray-500 text-sm mb-0.5">{t('profile.city')}</Paragraph>
                                            <Paragraph property="font-medium text-lg">{userData.city}</Paragraph>
                                        </Container>
                                    )}
                                    {userData.zip_code && (
                                        <Container>
                                            <Paragraph property="text-gray-500 text-sm mb-0.5">{t('profile.zip_code')}</Paragraph>
                                            <Paragraph property="font-medium text-lg">{userData.zip_code}</Paragraph>
                                        </Container>
                                    )}
                                </Container>
                            </Container>
                        )}

                        {/* O MĚ */}
                        {userData.additional_info && (
                            <Container property="p-1 space-y-4">
                                <Headings sizeTag={"h4"} property="border-b border-gray-200 pb-2">{t('profile.about_me')}</Headings>
                                <Paragraph property="text-lg leading-relaxed text-gray-800">
                                    {userData.additional_info}
                                </Paragraph>
                            </Container>
                        )}

                        {/* SKILLS - pouze pro studenty */}
                        {userData.user_type === 'student' && userData.skills && userData.skills.length > 0 && (
                            <Container property="p-1 space-y-4">
                                <Headings sizeTag={"h4"} property="border-b border-gray-200 pb-2">{t('profile.skills')}</Headings>
                                <div className="flex flex-wrap gap-3 pt-2">
                                    {userData.skills.map((skill, index) => (
                                        <span
                                            key={index}
                                            className="bg-blue-50 text-blue-700 text-sm font-bold px-5 py-2 rounded-full border border-blue-100 shadow-sm"
                                        >
                                            {skill}
                                        </span>
                                    ))}
                                </div>
                            </Container>
                        )}

                        {/* STUDIJNÍ INFORMACE - pouze pro studenty */}
                        {userData.user_type === 'student' && (userData.os_cislo || userData.faculty || userData.department) && (
                            <Container property="p-1 space-y-4">
                                <Headings sizeTag={"h4"} property="border-b border-gray-200 pb-2">{t('profile.study_info')}</Headings>
                                <Container property="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-4">
                                    {userData.os_cislo && (
                                        <Container>
                                            <Paragraph property="text-gray-500 text-sm mb-0.5">{t('profile.os_cislo')}</Paragraph>
                                            <Paragraph property="font-medium text-lg">{userData.os_cislo}</Paragraph>
                                        </Container>
                                    )}
                                    {userData.faculty && (
                                        <Container>
                                            <Paragraph property="text-gray-500 text-sm mb-0.5">{t('profile.faculty')}</Paragraph>
                                            <Paragraph property="font-medium text-lg">{userData.faculty}</Paragraph>
                                        </Container>
                                    )}
                                    {userData.department && (
                                        <Container>
                                            <Paragraph property="text-gray-500 text-sm mb-0.5">{t('profile.department')}</Paragraph>
                                            <Paragraph property="font-medium text-lg">{userData.department}</Paragraph>
                                        </Container>
                                    )}
                                </Container>
                            </Container>
                        )}

                        {/* CV - pouze pro studenty */}
                        {userData.user_type === 'student' && userData.cv_file && (
                            <Container property="p-1 space-y-4">
                                <Headings sizeTag={"h4"} property="border-b border-gray-200 pb-2">{t('profile.cv')}</Headings>
                                <Container property="pt-2">
                                    <a
                                        href={userData.cv_file}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="inline-flex items-center gap-3 bg-gray-50 hover:bg-gray-100 text-blue-600 font-bold py-3 px-6 rounded-lg border border-gray-200 transition-colors shadow-sm"
                                    >
                                        <Button icon="download" noVariant={true} iconColor="text-blue-600" />
                                        {t('profile.download_cv')}
                                    </a>
                                </Container>
                            </Container>
                        )}

                        {/* ORGANIZACE - pouze pro organizační uživatele */}
                        {userData.user_type === 'organization' && userData.employer_profile && (
                            <Container property="p-1 space-y-1">
                                <Headings sizeTag={"h4"}>{t('profile.organization')}</Headings>
                                <Container property="grid grid-cols-1 md:grid-cols-2 gap-4">
                                    {userData.employer_profile.company_name && (
                                        <Container>
                                            <Paragraph property="font-medium">{t('profile.company_name')}:</Paragraph>
                                            <Paragraph>{userData.employer_profile.company_name}</Paragraph>
                                        </Container>
                                    )}
                                    {userData.employer_profile.ico && (
                                        <Container>
                                            <Paragraph property="font-medium">{t('profile.ico')}:</Paragraph>
                                            <Paragraph>{userData.employer_profile.ico}</Paragraph>
                                        </Container>
                                    )}
                                    {userData.employer_profile.address && (
                                        <Container>
                                            <Paragraph property="font-medium">{t('profile.address')}:</Paragraph>
                                            <Paragraph>{userData.employer_profile.address}</Paragraph>
                                        </Container>
                                    )}
                                    {userData.employer_profile.city && (
                                        <Container>
                                            <Paragraph property="font-medium">{t('profile.city')}:</Paragraph>
                                            <Paragraph>{userData.employer_profile.city}</Paragraph>
                                        </Container>
                                    )}
                                </Container>
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
                                {t('nav.my_applications')}
                            </Button>
                        )}
                        {!id && userData.user_type !== 'student' && userData.user_type !== 'professor' && (
                            <Button
                                onClick={() => navigate(`/change-password`)}
                                icon={"lock"}
                                variant="secondary"
                            >
                                {t('profile.change_password')}
                            </Button>
                        )}
                        <Button
                            onClick={() => navigate(`/profil/${id ? id :""}?edit=true`)}
                            icon={"edit"}
                        >
                            {t('profile.edit_profile')}
                        </Button>
                    </Container>
                </>
            )}

        </ContainerForEntity>
    )
}
