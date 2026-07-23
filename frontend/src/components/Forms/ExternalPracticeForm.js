import React, { useEffect, useState } from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import TextBox from "@core/Form/TextBox";
import CustomDatePicker from "@core/Form/DatePicker";
import Headings from "@core/Text/Headings";
import { useTranslation } from "react-i18next";
import { useAresAPI } from "@api/ARES/aresJusticeAPI";
import useDebounce from "@hooks/useDebounce";

export default function ExternalPracticeForm({
  formData,
  handleChange,
  handleSubmit,
  errors = {},
  subjects = [],
}) {
  const { t } = useTranslation();
  const aresAPI = useAresAPI();
  const [aresLoading, setAresLoading] = useState(false);
  const [aresStatus, setAresStatus] = useState(null); // { type: 'success'|'warning'|'error', text: '' }

  const debouncedIco = useDebounce(formData?.ico, 500);

  useEffect(() => {
    if (!debouncedIco || String(debouncedIco).trim().length !== 8) {
      setAresStatus(null);
      return;
    }

    const fetchAres = async () => {
      setAresLoading(true);
      setAresStatus(null);
      try {
        const data = await aresAPI.getEntityByICO(debouncedIco);
        if (data && data.obchodniJmeno) {
          const companyName = data.obchodniJmeno;
          const address = data.sidlo?.textovaAdresa || "";
          handleChange({
            employer_name: companyName,
            address: address,
          });
          const sourceText = data.source === "cache" ? "z databáze (cache)" : "z ARES";
          setAresStatus({ type: "success", text: `Údaje firmy načteny ${sourceText}.` });
        }
      } catch (err) {
        if (err.response?.status === 404 && err.response?.data?.manual_input) {
          setAresStatus({
            type: "warning",
            text: "ARES nedostupný a IČO nenalezeno v databázi — vyplňte údaje ručně.",
          });
        } else {
          setAresStatus({
            type: "warning",
            text: "Nepodařilo se ověřit IČO v ARES. Zkontrolujte IČO nebo zadat ručně.",
          });
        }
      } finally {
        setAresLoading(false);
      }
    };

    fetchAres();
  }, [debouncedIco]);

  const coefficientOptions = [
    { label: "0.5", value: "0.5" },
    { label: "1", value: "1" },
  ];

  const availablePositions = [
    { label: 1, value: "1" },
    { label: 2, value: "2" },
    { label: 3, value: "3" },
    { label: 4, value: "4" },
    { label: 5, value: "5" },
    { label: 6, value: "6" },
    { label: 7, value: "7" },
    { label: 8, value: "8" },
    { label: 9, value: "9" },
    { label: 10, value: "10" },
  ];

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        handleSubmit();
      }}
    >
      {/* Section 1: External Organization */}
      <Headings sizeTag="h4" property="mb-4 font-bold">
        {t("external_practice.section_employer")}
      </Headings>

      <Container property="grid gap-2 grid-cols-2 mt-4">
        <TextField
          id="employer_name"
          value={formData?.employer_name}
          required={true}
          label={t("external_practice.employer_name")}
          placeholder={t("external_practice.employer_name_placeholder")}
          onChange={handleChange}
          error={errors.employer_name}
        />

        <TextField
          id="contact_person"
          value={formData?.contact_person}
          label={t("external_practice.contact_person")}
          placeholder={t("external_practice.contact_person_placeholder")}
          onChange={handleChange}
          error={errors.contact_person}
        />

        <TextField
          id="contact_email"
          value={formData?.contact_email}
          label={t("external_practice.contact_email")}
          placeholder={t("external_practice.contact_email_placeholder")}
          type="email"
          onChange={handleChange}
          error={errors.contact_email}
        />

        <TextField
          id="contact_phone"
          value={formData?.contact_phone}
          label={t("external_practice.contact_phone")}
          placeholder={t("external_practice.contact_phone_placeholder")}
          onChange={handleChange}
          error={errors.contact_phone}
        />

        <div>
          <TextField
            id="ico"
            value={formData?.ico}
            label={t("external_practice.ico")}
            placeholder={t("external_practice.ico_placeholder")}
            onChange={handleChange}
            error={errors.ico}
          />
          {aresLoading && (
            <p className="text-xs text-blue-600 mt-1">Ověřuji IČO v ARES...</p>
          )}
          {aresStatus && (
            <p
              className={`text-xs mt-1 font-medium ${
                aresStatus.type === "success"
                  ? "text-green-600"
                  : "text-amber-600"
              }`}
            >
              {aresStatus.text}
            </p>
          )}
        </div>

        <TextField
          id="address"
          value={formData?.address}
          label={t("external_practice.address")}
          placeholder={t("external_practice.address_placeholder")}
          onChange={handleChange}
          error={errors.address}
        />
      </Container>

      {/* Section 2: Practice Details */}
      <Headings sizeTag="h4" property="mb-4 mt-6 font-bold">
        {t("external_practice.section_practice")}
      </Headings>

      <Container property="grid gap-2 grid-cols-2 mt-4">
        <DropDown
          id="subject_id"
          value={formData?.subject_id}
          required={true}
          label={t("form.subject")}
          icon="book"
          options={subjects}
          onChange={handleChange}
          error={errors.subject_id}
        />

        <DropDown
          id="coefficient"
          value={formData?.coefficient}
          required={true}
          label={t("form.coefficient")}
          options={coefficientOptions}
          onChange={handleChange}
          error={errors.coefficient}
        />

        <CustomDatePicker
          id="start_date"
          value={formData?.start_date}
          label={t("form.start_date")}
          required={true}
          onChange={handleChange}
          error={errors.start_date}
        />

        <CustomDatePicker
          id="end_date"
          locked={true}
          value={formData?.end_date}
          label={t("form.end_date")}
          required={true}
          onChange={handleChange}
          error={errors.end_date}
        />

        <DropDown
          id="available_positions"
          value={formData?.available_positions}
          required={true}
          label={t("form.available_positions")}
          icon="users"
          options={availablePositions}
          onChange={handleChange}
          error={errors.available_positions}
        />
      </Container>

      <Container property="w-full gap-2 mt-2 flex-cols">
        <TextField
          id="title"
          value={formData?.title}
          required={true}
          label={t("form.title")}
          placeholder={t("form.title_placeholder")}
          onChange={handleChange}
          error={errors.title}
        />

        <TextBox
          id="description"
          value={formData?.description}
          label={t("form.description")}
          placeholder={t("form.description_placeholder")}
          onChange={handleChange}
          error={errors.description}
        />

        <TextBox
          id="responsibilities"
          value={formData?.responsibilities}
          label={t("form.responsibilities")}
          placeholder={t("form.responsibilities_placeholder")}
          onChange={handleChange}
          error={errors.responsibilities}
        />
      </Container>

      {/* Submit button */}
      <Container property="flex w-full justify-end ml-auto mt-6">
        <button
          type="submit"
          className="bg-facultyCol text-white px-4 py-2 rounded-lg transition-colors duration-200 mt-2 px-16 cursor-pointer"
        >
          {t("external_practice.create")}
        </button>
      </Container>
    </form>
  );
}
