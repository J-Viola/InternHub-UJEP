import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import Container from "@core/Container/Container";
import BackButton from "@core/Button/BackButton";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import { useMessage } from "@hooks/MessageContext";
import { useApi } from "@hooks/useApi";
import { useStudentPracticeAPI } from "@api/student_practice/student_practiceAPI";
import { buildFormData } from "@utils/formDataUtils";
import { useUser } from "@hooks/UserProvider";

export default function EvaluationForm() {
  const { id } = useParams(); // student_practice_id
  const api = useApi();
  const navigate = useNavigate();
  const { addMessage } = useMessage();
  const studentPracticeAPI = useStudentPracticeAPI();
  const { user } = useUser();

  const [entity, setEntity] = useState(null);
  const [loading, setLoading] = useState(true);

  const [formData, setFormData] = useState({
    expertise_rating: 5,
    expertise_comment: "",
    communication_rating: 5,
    communication_comment: "",
    initiative_rating: 5,
    initiative_comment: "",
    overall_comment: "",
  });

  const [pdfFile, setPdfFile] = useState(null);
  const [pdfError, setPdfError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const fetchEntity = async () => {
      try {
        const data = await studentPracticeAPI.getStudentPracticeCard(id);
        setEntity(data);
      } catch {
        addMessage("Chyba při načítání karty praxe", "E");
      } finally {
        setLoading(false);
      }
    };
    fetchEntity();
  }, [id, studentPracticeAPI, addMessage]);

  const isEnded = entity?.student_practice_status?.workflow_status === "ENDED";

  const handleRatingChange = (category, value) => {
    setFormData((prev) => ({
      ...prev,
      [category]: parseInt(value, 10),
    }));
  };

  const handleTextChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleFileChange = (e) => {
    const file = e.target.files[0];
    setPdfError("");
    if (!file) {
      setPdfFile(null);
      return;
    }
    const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf) {
      setPdfError("Povolený formát je pouze PDF");
      setPdfFile(null);
      e.target.value = "";
      return;
    }
    setPdfFile(file);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (pdfError) return;

    // PDF protocol is required
    if (!pdfFile) {
      setPdfError("Nahrání podepsaného hodnotícího archu je povinné");
      return;
    }
    setSubmitting(true);

    try {
      let payload;
      if (pdfFile) {
        payload = buildFormData({
          student_practice_id: parseInt(id, 10),
          ...formData,
          // BL-07/PBUG: EvaluationSerializer přijímá soubor pod polem `pdf_file`
          // (dříve se posílalo `pdf_protocol`, které backend ignoruje → validátor
          // „PDF je povinný" vracel 400 INVALID a protokol se nikdy nenahrál).
          pdf_file: pdfFile,
        });
        await api.post("/student-practices/evaluations/", payload, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      } else {
        payload = {
          student_practice_id: parseInt(id, 10),
          ...formData,
        };
        await api.post("/student-practices/evaluations/", payload);
      }
      addMessage("Evaluace byla úspěšně odeslána", "S");
      // FE-014: /praxe/:id neexistuje (vedlo na 404 stránku) — správně
      // karta praxe (SP detail).
      navigate(`/karta-praxe/${id}`);
    } catch (err) {
      // 403 EVALUATION_NOT_ENDED → česká hláška.
      if (err.code === "EVALUATION_NOT_ENDED") {
        addMessage("Evaluace je dostupná až po ukončení praxe", "E");
      } else {
        const msg = err.response?.data?.detail || "Chyba při odesílání evaluace";
        addMessage(msg, "E");
      }
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container" style={{ maxWidth: "800px", margin: "0 auto" }}>
        <BackButton />
        <Container property="bg-white mt-4 p-8 rounded-lg shadow-sm">
          <Paragraph property="text-gray-500">{"Načítání..."}</Paragraph>
        </Container>
      </div>
    );
  }

  // Role guard: only mentors/organization workers can submit evaluations
  if (user.isStudent()) {
    return (
      <div className="page-container" style={{ maxWidth: "800px", margin: "0 auto" }}>
        <BackButton />
        <Container property="bg-white mt-4 p-8 rounded-lg shadow-sm">
          <Paragraph property="text-red-600 font-medium">
            {"Evaluace je dostupná pouze mentorovi."}
          </Paragraph>
        </Container>
      </div>
    );
  }

  return (
    <div className="page-container" style={{ maxWidth: "800px", margin: "0 auto" }}>
      <BackButton />
      <Container property="bg-white mt-4 p-8 rounded-lg shadow-sm">
        <Headings sizeTag="h2" property="text-2xl font-bold mb-6">
          {"Hodnocení praxe"}
        </Headings>

        {!isEnded && entity && (
          <Container property="bg-yellow-50 border border-yellow-300 text-yellow-800 p-4 rounded-lg mb-6">
            <Paragraph property="text-sm font-medium">
              {"Evaluace je dostupná až po ukončení praxe"}
            </Paragraph>
          </Container>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Odbornost */}
          <div className="border-b pb-4">
            <label className="block font-semibold mb-2">{"Odbornost"}</label>
            <div className="flex items-center space-x-4">
              <input
                type="range"
                min="1"
                max="5"
                value={formData.expertise_rating}
                onChange={(e) => handleRatingChange("expertise_rating", e.target.value)}
                className="w-full accent-blue-600"
                disabled={!isEnded}
              />
              <span className="font-bold text-lg w-8">{formData.expertise_rating}</span>
            </div>
            <textarea
              name="expertise_comment"
              value={formData.expertise_comment}
              onChange={handleTextChange}
              placeholder={"Komentář k odbornosti"}
              rows={2}
              className="w-full mt-2 p-2 border rounded-md"
              disabled={!isEnded}
            />
          </div>

          {/* Komunikace */}
          <div className="border-b pb-4">
            <label className="block font-semibold mb-2">{"Komunikace"}</label>
            <div className="flex items-center space-x-4">
              <input
                type="range"
                min="1"
                max="5"
                value={formData.communication_rating}
                onChange={(e) => handleRatingChange("communication_rating", e.target.value)}
                className="w-full accent-blue-600"
                disabled={!isEnded}
              />
              <span className="font-bold text-lg w-8">{formData.communication_rating}</span>
            </div>
            <textarea
              name="communication_comment"
              value={formData.communication_comment}
              onChange={handleTextChange}
              placeholder={"Komentář ke komunikaci"}
              rows={2}
              className="w-full mt-2 p-2 border rounded-md"
              disabled={!isEnded}
            />
          </div>

          {/* Iniciativa */}
          <div className="border-b pb-4">
            <label className="block font-semibold mb-2">{"Iniciativa"}</label>
            <div className="flex items-center space-x-4">
              <input
                type="range"
                min="1"
                max="5"
                value={formData.initiative_rating}
                onChange={(e) => handleRatingChange("initiative_rating", e.target.value)}
                className="w-full accent-blue-600"
                disabled={!isEnded}
              />
              <span className="font-bold text-lg w-8">{formData.initiative_rating}</span>
            </div>
            <textarea
              name="initiative_comment"
              value={formData.initiative_comment}
              onChange={handleTextChange}
              placeholder={"Komentář k iniciativě"}
              rows={2}
              className="w-full mt-2 p-2 border rounded-md"
              disabled={!isEnded}
            />
          </div>

          {/* Celkový komentář */}
          <div>
            <label className="block font-semibold mb-2">{"Celkové hodnocení"}</label>
            <textarea
              name="overall_comment"
              value={formData.overall_comment}
              onChange={handleTextChange}
              placeholder={"Celkový komentář"}
              rows={3}
              className="w-full p-2 border rounded-md"
              disabled={!isEnded}
            />
          </div>

          {/* PDF Upload */}
          <div>
            <label htmlFor="evaluation-pdf-protocol" className="block font-semibold mb-2">
              {"Podepsaný hodnotící arch (PDF)"}
            </label>
            <input
              id="evaluation-pdf-protocol"
              type="file"
              accept=".pdf"
              onChange={handleFileChange}
              disabled={!isEnded}
              className="block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 disabled:opacity-50"
            />
            {pdfError && (
              <Paragraph property="text-red-600 text-sm mt-2">{pdfError}</Paragraph>
            )}
            {pdfFile && (
              <Paragraph property="text-green-700 text-sm mt-2">
                {"Vybrán soubor"}: {pdfFile.name}
              </Paragraph>
            )}
          </div>

          <div className="flex justify-end space-x-4 pt-4">
            <button
              type="submit"
              disabled={submitting || !isEnded || !!pdfError}
              className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {submitting ? "Odesílám..." : "Odeslat"}
            </button>
          </div>
        </form>
      </Container>
    </div>
  );
}
