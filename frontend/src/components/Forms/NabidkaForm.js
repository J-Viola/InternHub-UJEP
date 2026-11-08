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
import { REGION_OPTIONS } from "@components/Nabidka/regions";
import { normalizeSkills, SKILL_CATEGORIES, SKILL_LABELS } from "@utils/skills";

export default function NabidkaForm({organizationUsers, subjects, formData, handleChange, handleSubmit, isEdit = false, errors = {}, submitting = false}) {
    const [startDate, setStartDate] = useState("");
    const [endDate, setEndDate] = useState("");
    const skillCategories = SKILL_CATEGORIES;
    const skills = normalizeSkills(formData?.skills);
    const [skillTexts, setSkillTexts] = useState(() => Object.fromEntries(skillCategories.map(category => [category, skills[category].join(', ')])));
    const parseSkillText = (text) => text.split(',').map(item => item.trim()).filter(Boolean);
    const submitWithSkills = () => {
        const parsedSkills = Object.fromEntries(skillCategories.map(category => [category, parseSkillText(skillTexts[category] || '')]));
        handleChange({ skills: parsedSkills });
        handleSubmit({ ...formData, skills: parsedSkills });
    };
    const semesterOptions = [
        { label: "Neuvedeno", value: "" },
        { label: "Zimní semestr (ZS)", value: "ZS" },
        { label: "Letní semestr (LS)", value: "LS" },
    ];
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
                        {"Údaje nabídky"}
                    </Headings>
                </Container>
                <Container property={`grid gap-2 grid-cols-2 ${isEdit ? "mt-4" : "mt-4" }`}>
                    <CustomDatePicker
                        id={"start_date"}
                        value={formData?.start_date}
                        label={"Čas období od"}
                        required={true}
                        onChange={handleChange}
                        error={errors.start_date}
                    />


                    <DropDown
                        id="semester"
                        value={formData?.semester || ""}
                        label={"Semestr"}
                        options={semesterOptions}
                        onChange={handleChange}
                        error={errors.semester}
                    />
                    <DropDown
                        id={"coefficient"}
                        value={formData?.coefficient}
                        required={true}
                        label={"Úvazek"}
                        options={uvazek}
                        onChange={handleChange}
                        error={errors.coefficient}
                    />

                    <CustomDatePicker
                        id={"end_date"}
                        locked={true}
                        value={formData?.end_date}
                        label={"Čas období do"}
                        required={true}
                        onChange={handleChange}
                        error={errors.end_date}
                    />

                    <DropDown
                        id={"contact_user"}
                        value={formData?.contact_user}
                        required={true}
                        label={"Správce inzerátu"}
                        icon={"user"}
                        options={organizationUsers}
                        onChange={handleChange}
                        error={errors.contact_user}
                    />

                    <DropDown
                        id={"subject_id"}
                        value={formData?.subject_id}
                        required={true}
                        label={"Přiřazený předmět"}
                        icon={"book"}
                        options={subjects}
                        onChange={handleChange}
                        error={errors.subject_id}
                    />

                    <DropDown
                        id={"available_positions"}
                        value={formData?.available_positions}
                        required={true}
                        label={"Počet volných míst"}
                        icon={"users"}
                        options={availablePositions}
                        onChange={handleChange}
                        error={errors.available_positions}
                    />
                </Container>

                {/* Mentor, kontaktní e-mail, kraj, lokalita */}
                <Container property={"grid gap-2 grid-cols-2 mt-4"}>
                    <TextField
                        id={"mentor_name"}
                        value={formData?.mentor_name}
                        required={true}
                        label={"Jméno mentora"}
                        placeholder={"Jméno mentora"}
                        onChange={handleChange}
                        error={errors.mentor_name}
                    />

                    <TextField
                        id={"contact_email"}
                        value={formData?.contact_email}
                        required={true}
                        type="email"
                        label={"Kontaktní e-mail"}
                        placeholder={"Kontaktní e-mail"}
                        onChange={handleChange}
                        error={errors.contact_email}
                    />

                    <DropDown
                        id={"region"}
                        value={formData?.region}
                        label={"Kraj"}
                        placeholder={"Všechny"}
                        options={REGION_OPTIONS}
                        onChange={handleChange}
                        error={errors.region}
                    />

                    <TextField
                        id={"city"}
                        value={formData?.city}
                        label={"Lokalita"}
                        placeholder={"Lokalita"}
                        onChange={handleChange}
                        error={errors.city}
                    />
                </Container>

                <Container property={"w-full gap-2 mt-2 flex-cols"}>

                    <TextField
                        id={"title"}
                        value={formData?.title}
                        required={true}
                        label={"Název"}
                        placeholder={"Název stáže"}
                        onChange={handleChange}
                        error={errors.title}
                    />

                    <TextBox
                        id={"description"}
                        value={formData?.description}
                        required={true}
                        label={"Popis stáže"}
                        placeholder={"Napište popis stáže"}
                        onChange={handleChange}
                        error={errors.description}
                    />

                    <TextBox
                        id={"responsibilities"}
                        value={formData?.responsibilities}
                        required={true}
                        label={"Náplň práce"}
                        placeholder={"Popište náplň práce"}
                        onChange={handleChange}
                        error={errors.responsibilities}
                    />

                    {/* Dovednosti v kategoriích; payload zůstává v poli skills. */}
                    <Container property="mt-4">
                        {skillCategories.map(category => (
                            <TextField key={category} id={`skills-${category}`}
                                label={SKILL_LABELS[category]}
                                placeholder={"Oddělte položky čárkou"}
                                value={skillTexts[category] || ''}
                                onChange={(changed) => {
                                    const text = changed[`skills-${category}`] || '';
                                    setSkillTexts(previous => ({ ...previous, [category]: text }));
                                    handleChange({ skills: { ...skills, [category]: parseSkillText(text) } });
                                }}
                                onBlur={() => handleChange({ skills: { ...skills, [category]: parseSkillText(skillTexts[category] || '') } })} />
                        ))}
                    </Container>
                </Container>


                {/* PROSTOR PRO TLAČÍKO */}
                <Container property={"flex w-full justify-end ml-auto"}>
                    <Button
                        property={"mt-2 px-16"}
                        disabled={submitting}
                        onClick={submitWithSkills}
                    >
                        {isEdit ? "Uložit změny" : "Vytvořit"}
                    </Button>
                </Container>
            </>
        )
}
