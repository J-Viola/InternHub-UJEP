import React, { useEffect, useState } from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import TextBox from "@core/Form/TextBox";
import CustomDatePicker from "@core/Form/DatePicker";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import { useTranslation } from "react-i18next";
import { useAresAPI } from "@api/ARES/aresJusticeAPI";
import useDebounce from "@hooks/useDebounce";

// Shodné se settings.MAX_UPLOAD_SIZE (10 MB) na backendu.
const MAX_EXTERNAL_DETAILS_SIZE = 10 * 1024 * 1024;

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
  const [aresLocked, setAresLocked] = useState(false);
  const [detailsFileError, setDetailsFileError] = useState("");

  const debouncedIco = useDebounce(formData?.ico, 500);

  useEffect(() => {
    if (!debouncedIco || String(debouncedIco).trim().length !== 8) {
      setAresStatus(null);
      setAresLocked(false);
      return;
    }

    const fetchAres = async () => {
      setAresLoading(true);
      setAresStatus(null);
      // Během lookupu jsou pole odemčená; zamknou se až po úspěšném prefillu.
      setAresLocked(false);
      try {
        const data = await aresAPI.getEntityByICO(debouncedIco);
        if (data && (data.obchodniJmeno || data.name)) {
          const companyName = data.obchodniJmeno || data.name;
          const address = data.sidlo?.textovaAdresa || data.address || "";
          handleChange({
            employer_name: companyName,
            address: address,
            ares_locked: true,
          });
          setAresLocked(true);
          const sourceKey =
            data.source === "cache" ? "ares.found_cache" : "ares.found_ares";
          setAresStatus({ type: "success", text: t(sourceKey) });
        } else if (data && data.found === false) {
          // ARES odpověděl, ale subjekt s tímto IČO nenašel.
          handleChange({ ares_locked: false });
          setAresStatus({ type: "warning", text: t("ares.not_found") });
        }
      } catch (err) {
        handleChange({ ares_locked: false });
        const code = err.code || err.response?.data?.error_code;
        if (code === "ARES_NOT_FOUND") {
          // 404 → subjekt nenalezen v ARES, pole odemčená.
          setAresStatus({ type: "warning", text: t("ares.not_found") });
        } else if (
          code === "ARES_UNAVAILABLE" ||
          err.response?.status === 503 ||
          (err.response?.status === 404 && err.response?.data?.manual_input)
        ) {
          // 503 → výpadek ARES + cache miss → manuální režim.
          setAresStatus({ type: "warning", text: t("ares.unavailable") });
        } else {
          setAresStatus({ type: "warning", text: t("ares.verify_error") });
        }
      } finally {
        setAresLoading(false);
      }
    };

    fetchAres();
  }, [debouncedIco]);

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    setDetailsFileError("");
    if (!file) {
      handleChange({ external_details_file: null });
      return;
    }
    const isAllowed = /\.(pdf|docx)$/i.test(file.name);
    if (!isAllowed) {
      setDetailsFileError(t("external.file_type_error"));
      e.target.value = "";
      return;
    }
    if (file.size > MAX_EXTERNAL_DETAILS_SIZE) {
      setDetailsFileError(t("api_errors.FILE_TOO_LARGE"));
      e.target.value = "";
      return;
    }
    handleChange({ external_details_file: file });
  };

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
        <div>
          <TextField
            id="employer_name"
            value={formData?.employer_name}
            required={true}
            label={t("external_practice.employer_name")}
            placeholder={t("external_practice.employer_name_placeholder")}
            onChange={handleChange}
            error={errors.employer_name}
            disabled={aresLocked}
          />
          {aresLocked && (
            <p className="text-xs text-gray-500 mt-1" title={t("ares.locked")}>
              {t("ares.locked")}
            </p>
          )}
        </div>

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
            <p className="text-xs text-blue-600 mt-1">{t("ares.loading")}</p>
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
          disabled={aresLocked}
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

      {/* Povinný dokument s detaily praxe */}
      <Container property="w-full gap-2 mt-4">
        <div>
          <label className="block text-base font-medium text-gray-700 mb-1">
            {t("external.details_label")}
            <span className="text-red-600 ml-1">*</span>
          </label>
          <input
            type="file"
            accept=".pdf,.docx"
            onChange={handleFileChange}
            aria-required="true"
            className="block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          {(detailsFileError || errors.external_details_file) && (
            <Paragraph property="text-red-500 text-sm mt-1" role="alert">
              {detailsFileError || errors.external_details_file}
            </Paragraph>
          )}
          {formData?.external_details_file?.name && (
            <Paragraph property="text-green-700 text-sm mt-1">
              {t("external.file_selected")}: {formData.external_details_file.name}
            </Paragraph>
          )}
        </div>
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
