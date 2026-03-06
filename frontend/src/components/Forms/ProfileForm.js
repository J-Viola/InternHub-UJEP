import React, { useState } from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import TextBox from "@core/Form/TextBox";
import Button from "@components/core/Button/Button";
import UploadFile from "@core/Form/UploadFile";
import Image from "@core/Image/Image";
import Headings from "@core/Text/Headings";
import { useTranslation } from "react-i18next";

const convertToBase64 = (file) => {
    return new Promise((resolve, reject) => {
        const fileReader = new FileReader();
        fileReader.readAsDataURL(file);
        fileReader.onload = () => {
            resolve(fileReader.result);
        };
        fileReader.onerror = (error) => {
            reject(error);
        };
    });
};

export default function ProfileForm({ formData, handleInputChange, handleSubmit }) {
    const { t } = useTranslation();
    const handleProfilePicChange = async (file) => {
        if (file) {
            try {
                const base64 = await convertToBase64(file);
                handleInputChange({ profile_picture: base64 });
            } catch (error) {
                console.error("Error converting file to base64:", error);
            }
        }
    };

    const handleSkillChange = (index, value) => {
        const newSkills = [...(formData.skills || [])];
        newSkills[index] = value;
        handleInputChange({ skills: newSkills });
    };

    const handleAddSkillRow = () => {
        const currentSkills = formData.skills || [];
        if (currentSkills.length < 5) {
            handleInputChange({ skills: [...currentSkills, ""] });
        }
    };

    const handleRemoveSkill = (index) => {
        const newSkills = [...(formData.skills || [])];
        newSkills.splice(index, 1);
        handleInputChange({ skills: newSkills });
    };

    return (
        <>
            <Container>
                <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                    {t('profile.profile_data')}
                </Headings>
            </Container>

            <Container property={"grid gap-2 grid-cols-3"}>
                <TextField
                    id={"first_name"}
                    required={true}
                    label={t('profile.first_name')}
                    placeholder={t('profile.first_name_placeholder')}
                    value={formData?.first_name || ''}
                    onChange={handleInputChange}
                />

                <TextField
                    id={"last_name"}
                    required={true}
                    label={t('profile.last_name')}
                    placeholder={t('profile.last_name_placeholder')}
                    value={formData?.last_name || ''}
                    onChange={handleInputChange}
                />

                <TextField
                    id={"email"}
                    required={true}
                    label={t('profile.email')}
                    placeholder={t('profile.email_placeholder')}
                    value={formData?.email || ''}
                    onChange={handleInputChange}
                />

                <TextField
                    id={"phone"}
                    required={false}
                    label={t('profile.phone')}
                    placeholder={t('profile.phone_placeholder')}
                    value={formData?.phone || ''}
                    onChange={handleInputChange}
                />

                <TextField
                    id={"title_before"}
                    required={false}
                    label={t('profile.title_before')}
                    placeholder={t('profile.title_before_placeholder')}
                    value={formData?.title_before || ''}
                    onChange={handleInputChange}
                />

                <TextField
                    id={"title_after"}
                    required={false}
                    label={t('profile.title_after')}
                    placeholder={t('profile.title_after_placeholder')}
                    value={formData?.title_after || ''}
                    onChange={handleInputChange}
                />

                <TextField
                    id={"street"}
                    required={false}
                    label={`${t('profile.residence')} (${t('profile.street')})`}
                    placeholder={t('profile.street_placeholder')}
                    value={formData?.street || ''}
                    onChange={handleInputChange}
                />

                <TextField
                    id={"street_number"}
                    required={false}
                    label={t('profile.street_number')}
                    placeholder={t('profile.street_number_placeholder')}
                    value={formData?.street_number || ''}
                    onChange={handleInputChange}
                />

                <TextField
                    id={"city"}
                    required={false}
                    label={t('profile.city')}
                    placeholder={t('profile.city_placeholder')}
                    value={formData?.city || ''}
                    onChange={handleInputChange}
                />

                <TextField
                    id={"zip_code"}
                    required={false}
                    label={t('profile.zip_code')}
                    placeholder={t('profile.zip_code_placeholder')}
                    value={formData?.zip_code || ''}
                    onChange={handleInputChange}
                />

                <TextField
                    id={"field_of_study"}
                    required={false}
                    label={t('profile.field_of_study')}
                    placeholder={t('profile.field_of_study_placeholder')}
                    value={formData?.field_of_study || ''}
                    onChange={handleInputChange}
                />

                <TextField
                    id={"specialization"}
                    required={false}
                    label={t('profile.specialization')}
                    placeholder={t('profile.specialization_placeholder')}
                    value={formData?.specialization || ''}
                    onChange={handleInputChange}
                />

                <TextField
                    id={"year_of_study"}
                    required={false}
                    label={t('profile.year_of_study')}
                    placeholder={t('profile.year_of_study_placeholder')}
                    value={formData?.year_of_study || ''}
                    onChange={handleInputChange}
                />
            </Container>

            <Container property={"w-full gap-2 mt-2 flex-cols"}>
                <TextBox
                    id={"additional_info"}
                    required={false}
                    label={t('profile.about_me')}
                    placeholder={t('profile.about_me_placeholder')}
                    value={formData?.additional_info || ''}
                    onChange={handleInputChange}
                />

                <Container property="mt-4">
                    <Headings sizeTag="h5" property="mb-2 font-bold">{t('profile.skills_limit')}</Headings>
                    <div className="flex flex-col gap-2 mb-2">
                        {formData?.skills?.map((skill, index) => (
                            <div key={index} className="flex items-center gap-2">
                                <input
                                    type="text"
                                    className="px-2 py-1 text-base text-gray-900 bg-gray-100 rounded-lg border-2 border-gray-300 w-full max-w-md"
                                    placeholder={t('profile.skill_placeholder', { index: index + 1 })}
                                    value={skill}
                                    onChange={(e) => handleSkillChange(index, e.target.value)}
                                />
                                <Button
                                    onClick={() => handleRemoveSkill(index)}
                                    icon="cross"
                                    noVariant={true}
                                    iconColor="text-red-600"
                                    property="hover:bg-red-100 p-1 rounded"
                                />
                            </div>
                        ))}
                    </div>
                    {(!formData?.skills || formData.skills.length < 5) && (
                        <Button
                            onClick={handleAddSkillRow}
                            icon="plus"
                            variant="blueSmall"
                            property="w-fit"
                        >
                            {t('profile.add_skill')}
                        </Button>
                    )}
                </Container>
            </Container>

            <Container property={"w-full gap-2 mt-2 flex-cols"}>
                {formData?.profile_picture && (
                    <Container property="mb-4">
                        <Container property="text-sm font-medium text-gray-700 mb-2">
                            {t('profile.current_photo')}:
                        </Container>
                        <Container property="w-32 h-32 bg-blue-600 rounded-lg p-4 flex items-center justify-center">
                            <Image
                                src={formData.profile_picture}
                                alt={t('profile.current_photo')}
                                width="100%"
                                height="100%"
                                objectFit="cover"
                                borderRadius="0.5rem"
                                property="w-full h-full"
                            />
                        </Container>
                    </Container>
                )}

                <UploadFile
                    id={"profile_picture"}
                    label={t('profile.upload_photo')}
                    accept={"image/*"}
                    onChange={handleProfilePicChange}
                />

                <Container property="mt-4">
                     <UploadFile
                        id={"cv_file"}
                        label={t('profile.upload_cv_pdf')}
                        accept={".pdf"}
                        onChange={(file) => handleInputChange({ cv_file: file })}
                    />
                </Container>
            </Container>

            <Container property={"flex justify-end mt-4"}>
                <Button
                    onClick={handleSubmit}
                >
                    {t('common.save')}
                </Button>
            </Container>
        </>
    );
}
