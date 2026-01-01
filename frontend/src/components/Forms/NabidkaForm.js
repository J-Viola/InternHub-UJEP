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
import { useTranslation } from "react-i18next";

export default function NabidkaForm({organizationUsers, subjects, formData, handleChange, handleSubmit, isEdit = false, errors = {}}) {
    const { t } = useTranslation();
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const uvazek = [
        {"label": 0.5, "value" : "0.5"},
        {"label": 1, "value" : "1"}
    ]

    const availablePositions = [
        {"label": 1, "value": "1"},
        {"label": 2, "value": "2"},
        {"label": 3, "value": "3"},
        {"label": 4, "value": "4"},
        {"label": 5, "value": "5"},
        {"label": 6, "value": "6"},
        {"label": 7, "value": "7"},
        {"label": 8, "value": "8"},
        {"label": 9, "value": "9"},
        {"label": 10, "value": "10"}
    ]


    const handleSkillChange = (index, value) => {
        const newSkills = [...(formData.skills || [])];
        newSkills[index] = value;
        handleChange({ target: { id: 'skills', value: newSkills } });
    };

    const handleAddSkillRow = () => {
        const currentSkills = formData.skills || [];
        if (currentSkills.length < 5) {
            handleChange({ target: { id: 'skills', value: [...currentSkills, ""] } });
        }
    };

    const handleRemoveSkill = (index) => {
        const newSkills = [...(formData.skills || [])];
        newSkills.splice(index, 1);
        handleChange({ target: { id: 'skills', value: newSkills } });
    };

    return(
            <>
                <Container>
                    <Headings sizeTag={"h4"} property={"mb-4 font-bold"}>
                        {t('form.offer_data')}
                    </Headings>
                </Container>
                <Container property={`grid gap-2 grid-cols-2 ${isEdit ? "mt-4" : "mt-4" }`}>
                    <CustomDatePicker
                        id={"start_date"}
                        value={formData?.start_date}
                        label={t('form.start_date')}
                        required={true}
                        onChange={handleChange}
                        error={errors.start_date}
                    />


                    <DropDown
                        id={"coefficient"}
                        value={formData?.coefficient}
                        required={true}
                        label={t('form.coefficient')}
                        options={uvazek}
                        onChange={handleChange}
                        error={errors.coefficient}
                    />

                    <CustomDatePicker
                        id={"end_date"}
                        locked={true}
                        value={formData?.end_date}
                        label={t('form.end_date')}
                        required={true}
                        onChange={handleChange}
                        error={errors.end_date}
                    />

                    <DropDown
                        id={"contact_user"}
                        value={formData?.contact_user}
                        required={true}
                        label={t('form.contact_user')}
                        icon={"user"}
                        options={organizationUsers}
                        onChange={handleChange}
                        error={errors.contact_user}
                    />

                    <DropDown
                        id={"subject_id"}
                        value={formData?.subject_id}
                        required={true}
                        label={t('form.subject')}
                        icon={"book"}
                        options={subjects}
                        onChange={handleChange}
                        error={errors.subject_id}
                    />

                    <DropDown
                        id={"available_positions"}
                        value={formData?.available_positions}
                        required={true}
                        label={t('form.available_positions')}
                        icon={"users"}
                        options={availablePositions}
                        onChange={handleChange}
                        error={errors.available_positions}
                    />
                </Container>

                <Container property={"w-full gap-2 mt-2 flex-cols"}>

                    <TextField
                        id={"title"}
                        value={formData?.title}
                        required={true}
                        label={t('form.title')}
                        placeholder={t('form.title_placeholder')}
                        onChange={handleChange}
                        error={errors.title}
                    />

                    <TextBox
                        id={"description"}
                        value={formData?.description}
                        required={true}
                        label={t('form.description')}
                        placeholder={t('form.description_placeholder')}
                        onChange={handleChange}
                        error={errors.description}
                    />

                    <TextBox
                        id={"responsibilities"}
                        value={formData?.responsibilities}
                        required={true}
                        label={t('form.responsibilities')}
                        placeholder={t('form.responsibilities_placeholder')}
                        onChange={handleChange}
                        error={errors.responsibilities}
                    />

                    {/* SKILLS SECTION */}
                    <Container property="mt-4">
                        <Headings sizeTag="h5" property="mb-2 font-bold">{t('profile.skills_limit')}</Headings>
                        <Container property="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {formData?.skills?.map((skill, index) => (
                                <Container key={index} property="flex gap-2 items-center">
                                    <TextField
                                        id={`skill-${index}`}
                                        placeholder={t('profile.skill_placeholder', { index: index + 1 })}
                                        value={skill}
                                        onChange={(e) => handleSkillChange(index, e.target.value)}
                                        property="flex-grow"
                                    />
                                    <Button 
                                        variant="redSmall" 
                                        onClick={() => handleRemoveSkill(index)}
                                        property="h-fit"
                                    >
                                        ✕
                                    </Button>
                                </Container>
                            ))}
                        </Container>
                        {(!formData?.skills || formData.skills.length < 5) && (
                            <Button 
                                variant="blueSmall" 
                                onClick={handleAddSkillRow}
                                property="mt-2"
                            >
                                + {t('profile.add_skill')}
                            </Button>
                        )}
                    </Container>
                </Container>


                {/* PROSTOR PRO TLAČÍKO */}
                <Container property={"flex w-full justify-end ml-auto"}>
                    <Button
                        property={"mt-2 px-16"}
                        onClick={() => handleSubmit()}
                    >
                        {isEdit ? t('form.save_changes') : t('form.create')}
                    </Button>
                </Container>
            </>
        )
}
