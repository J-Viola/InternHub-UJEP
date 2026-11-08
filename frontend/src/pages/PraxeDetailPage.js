import React, { useState, useEffect, useRef } from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import BackButton from "@core/Button/BackButton";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import { useParams } from "react-router-dom";
import Button from "@core/Button/Button";
import StateBadge from "@core/StateBadge";
import DocsPanel from "@components/Nabidka/DocsPanel";
import PopUpCon from "@core/Container/PopUpCon";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI";
import { useUser } from "@hooks/UserProvider";
import { Image } from "@components/core/Image";
import { useMessage } from "@hooks/MessageContext";
import ProgressPanel from "@components/Nabidka/ProgressBar";
import { useDocumentsAPI } from "@api/documents/documentsAPI";
import { useStudentPracticeAPI } from "@api/student_practice/student_practiceAPI";
import { buildFormData } from "@utils/formDataUtils";
import { getApiErrorMessage } from "@utils/apiErrorUtils";
import {
  isCancellationPending,
  canRequestCancellation,
  canResolveCancellation,
  canReviewResubmittedDocuments,
  canTerminalReject,
} from "@utils/spWorkflowUtils";
import LoadingState from "@components/core/Feedback/LoadingState";
import ErrorState from "@components/core/Feedback/ErrorState";
import Timeline from "@components/Student/Timeline";
import usePolling, { POLLING_INTERVAL_MS } from "@hooks/usePolling";

export default function PraxeDetailPage() {
  const { id } = useParams();
  const [popUp, setPopUp] = useState(false);
  const [docsPopUp, setDocsPopUp] = useState(false);
  const [rejectPopUp, setRejectPopUp] = useState(false);
  const [withdrawPopUp, setWithdrawPopUp] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  // A-12: storno studentem + vzetí na vědomí (garant/admin)
  const [cancelPopUp, setCancelPopUp] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  // C19-B/T2c: review-pending DOCUMENTS_RESUBMITTED — rozhodnutí review
  const [repairPopUp, setRepairPopUp] = useState(false);
  const [repairDecision, setRepairDecision] = useState(null);
  const [repairReason, setRepairReason] = useState("");
  const [entity, setEntity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(false);
  const [timelineRefreshKey, setTimelineRefreshKey] = useState(0);
  const fetchSequence = useRef(0);
  const inFlightFetch = useRef(null);
  const loadingRequest = useRef(null);
  const nabidkaAPI = useNabidkaAPI();
  const studentpraticeAPI = useStudentPracticeAPI();
  const documentAPI = useDocumentsAPI();
  const { user } = useUser();
  const { addMessage } = useMessage();

  const [docs, setDocs] = useState([]);

  const fetchData = async ({ silent = false } = {}) => {
    const current = inFlightFetch.current;
    if (current?.id === id && (silent || !current.silent)) {
      // Refresh triggers (poll/focus/visibility) must not supersede foreground
      // requests or each other. A foreground caller reuses only a foreground
      // fetch: a silent one may have started before a mutation and carry stale data.
      return current.promise;
    }

    const sequence = ++fetchSequence.current;
    const request = {};
    inFlightFetch.current = { id, request, silent };
    if (!silent) {
      loadingRequest.current = request;
      setLoading(true);
      setLoadError(false);
    }
    const promise = (async () => {
      try {
        const result = await studentpraticeAPI.getStudentPracticeCard(id);
        if (sequence !== fetchSequence.current) return;
        setEntity(result);
        setDocs(result.student_practice_documents || []);
        setTimelineRefreshKey((key) => key + 1);
      } catch (error) {
        if (sequence !== fetchSequence.current) return;
        if (!silent) {
          addMessage("Chyba při načítání karty praxe", "E");
          setLoadError(true);
        }
      } finally {
        if (inFlightFetch.current?.request === request) inFlightFetch.current = null;
        if (loadingRequest.current === request) {
          loadingRequest.current = null;
          setLoading(false);
        }
      }
    })();
    inFlightFetch.current.promise = promise;
    return promise;
  };

  useEffect(() => {
    if (id) {
      fetchData();
    }
  }, [id]);

  usePolling(() => fetchData({ silent: true }), POLLING_INTERVAL_MS);

  useEffect(() => {
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") fetchData({ silent: true });
    };
    window.addEventListener("focus", refreshWhenVisible);
    document.addEventListener("visibilitychange", refreshWhenVisible);
    return () => {
      window.removeEventListener("focus", refreshWhenVisible);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, [id]);

  const handleDownload = async (documentId) => {
    try {
      const blob = await documentAPI.downloadDocument(documentId);
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `dokument_${documentId}.docx`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
    } catch (error) {
      addMessage("Chyba při stahování dokumentu", "E");
    }
  };

  const handleUpload = async (documentId) => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = ".doc,.docx";
    input.onchange = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const formData = buildFormData({ document: file });
      try {
        await documentAPI.uploadDocument(documentId, formData);
        addMessage("Dokument úspěšně nahrán", "S");
        fetchData();
      } catch (error) {
        addMessage("Chyba při nahrávání dokumentu", "E");
      }
    };
    input.click();
  };

  const handleReview = async (documentId, status) => {
    // Simple prompt for note if rejecting, or just approve
    let note = "";
    if (status === 2) {
      // REJECTED
      note = prompt("Zadejte důvod vrácení dokumentu:") || "";
    }

    try {
      await documentAPI.reviewDocument(documentId, status, note);
      addMessage("Dokument byl úspěšně zkontrolován", "S");
      fetchData();
    } catch (error) {
      addMessage("Chyba při kontrole dokumentu", "E");
    }
  };

  // Generate and download a contract/content/report/feedback .docx
  const handleGenerateDocument = async (docType, displayName) => {
    try {
      const blob = await studentpraticeAPI.downloadGeneratedDocument(
        id,
        docType,
      );
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", `${docType}_${id}.docx`);
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
      addMessage("Dokument byl úspěšně vygenerován", "S");
    } catch (error) {
      addMessage("Chyba při generování dokumentu", "E");
    }
  };

  const handlePopUp = () => {
    setPopUp(!popUp);
  };

  const handleDocsPopUp = () => {
    setDocsPopUp(!docsPopUp);
  };

  const handleApply = async () => {
    try {
      const res = await nabidkaAPI.applyNabidka({
        practice: id,
      });
      if (res) {
        addMessage("Žádost byla úspěšně odeslána", "S");
        handlePopUp();
        fetchData();
      }
    } catch (error) {
      console.error(error);
      // kapacita (CAPACITY_FULL) i ostatní serverové chyby se zobrazí čistě
      addMessage(getApiErrorMessage(error, "Došlo k chybě při podání přihlášky."), "E");
    }
  };

  const handleApprove = async () => {
    try {
      await studentpraticeAPI.updateStudentPracticeStatus(id, "approve", {
        workflowStatus: entity?.student_practice_status?.workflow_status,
      });
      addMessage("Přihláška schválena", "S");
      fetchData();
      setPopUp(false);
    } catch (error) {
      addMessage(getApiErrorMessage(error, "Chyba při schvalování"), "E");
    }
  };

  const handleReject = () => {
    setRejectReason("");
    setRejectPopUp(true);
    setPopUp(false);
  };

  const handleRejectWithReason = async () => {
    if (rejectReason.trim().length < 10) {
      addMessage(rejectReason.trim() ? "Důvod zamítnutí musí mít alespoň 10 znaků" : "Důvod zamítnutí je povinný", "E");
      return;
    }
    try {
      await studentpraticeAPI.updateStudentPracticeStatus(id, "reject", {
        reason: rejectReason.trim(),
        workflowStatus: entity?.student_practice_status?.workflow_status,
      });
      addMessage("Přihláška zamítnuta", "S");
      fetchData();
      setRejectPopUp(false);
      setRejectReason("");
    } catch (error) {
      addMessage(getApiErrorMessage(error, "Chyba při zamítání"), "E");
    }
  };

  const handleConfirmContract = async () => {
    try {
      // T2b: potvrzení je idempotentní (opakování stejné osy = 200 no-op);
      // UI nabízí akci jen ve stavu AWAITING_CONTRACT, kde by jinde 400.
      await studentpraticeAPI.confirmContract(id);
      addMessage("Přijetí smlouvy bylo úspěšně potvrzeno", "S");
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, "Chyba při potvrzování přijetí smlouvy"), "E");
    }
  };

  const handleResubmit = async () => {
    try {
      await studentpraticeAPI.updateStudentPracticeStatus(id, "resubmit", {
        workflowStatus: entity?.student_practice_status?.workflow_status,
      });
      addMessage("Praxe byla znovu odeslána ke schválení", "S");
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, "Chyba při opětovném odesílání praxe"), "E");
    }
  };

  const handleWithdraw = async () => {
    try {
      await studentpraticeAPI.withdrawApplication(id);
      addMessage("Úspěšně jste se odhlásili z praxe", "S");
      setWithdrawPopUp(false);
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, "Chyba při odhlašování z praxe"), "E");
    }
  };

  // --- A-12: okamžité storno studentem (vlastní přihláška) ---
  const handleRequestCancellation = async () => {
    if (!cancelReason.trim()) {
      addMessage("Důvod storno je povinný", "E");
      return;
    }
    try {
      await studentpraticeAPI.requestCancellation(id, cancelReason.trim());
      addMessage("Praxe byla stornována", "S");
      setCancelPopUp(false);
      setCancelReason("");
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, "Praxi se nepodařilo stornovat"), "E");
    }
  };

  // --- A-12: garant/admin bere storno studenta na vědomí ---
  const handleResolveCancellation = async () => {
    try {
      await studentpraticeAPI.resolveCancellation(id);
      addMessage("Storno bylo vzato na vědomí", "S");
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, "Storno se nepodařilo vzít na vědomí"), "E");
    }
  };

  // --- FE-007: dokončení ENDED → COMPLETED (server vynucuje Evaluation +
  // schválený FEEDBACK dokument, jinak 400 s čitelnou hláškou) ---
  const handleComplete = async () => {
    try {
      await studentpraticeAPI.transitionStudentPractice(id, 6, "");
      addMessage("Praxe byla dokončena (Splněno)", "S");
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, "Chyba při dokončování praxe"), "E");
    }
  };

  // --- C19-B/T2c: review rozhoduje o DOCUMENTS_RESUBMITTED ---
  const handleRepairApprove = async (targetState) => {
    try {
      await studentpraticeAPI.transitionStudentPractice(id, targetState, "");
      addMessage("Rozhodnutí o dokumentech bylo zaznamenáno", "S");
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, "Chyba při rozhodování o dokumentech"), "E");
    }
  };

  const openRepairPopup = (decision) => {
    setRepairDecision(decision);
    setRepairReason("");
    setRepairPopUp(true);
  };

  const handleRepairDecision = async () => {
    if (repairReason.trim().length < 10) {
      addMessage("Důvod zamítnutí musí mít alespoň 10 znaků", "E");
      return;
    }
    // 'reject' → DOCUMENTS_REJECTED (smyčka pokračuje);
    // 'terminal' → REJECTED (jen admin + důvod, T2c/R44)
    const targetState = repairDecision === "terminal" ? 2 : 9;
    try {
      await studentpraticeAPI.transitionStudentPractice(id, targetState, repairReason.trim());
      addMessage("Rozhodnutí o dokumentech bylo zaznamenáno", "S");
      setRepairPopUp(false);
      setRepairDecision("");
      setRepairReason("");
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, "Chyba při rozhodování o dokumentech"), "E");
    }
  };

  return (
    <>
      <BackButton />

      {loading && <LoadingState message={"Načítání..."} />}

      {!loading && loadError && (
        <ErrorState
          description={"Chyba při načítání karty praxe"}
          onRetry={fetchData}
        />
      )}

      {!loading && !loadError && entity && (
        <>
          {/* INFORMACE O STUDENTOVI */}
          <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8 mb-2 mt-4"}>
            <Container property="flex justify-between items-start">
              <Container>
                <Headings sizeTag={"h3"} property={""}>
                  {"Student"}
                </Headings>
                <Paragraph property={"mt-2"}>
                  {entity?.student_practice_status?.student_info?.full_name}
                </Paragraph>
                <Paragraph>
                  {`Osobní číslo: ${entity?.student_practice_status?.student_info?.os_cislo || "Není uvedeno"}`}
                </Paragraph>
                <Paragraph>
                  {`Email: ${entity?.student_practice_status?.student_info?.email}`}
                </Paragraph>
              </Container>

              {/* DUAL APPROVAL STATUS FOR PROFESSORS */}
              {user &&
                user.isProfessor() &&
                entity?.student_practice_status && (
                  <Container property="flex flex-col gap-2 items-end">
                    <Container property="flex items-center gap-2">
                      <Paragraph property="text-sm font-medium">
                        {"Schválení školou"}:
                      </Paragraph>
                      <Button
                        variant={
                          entity.student_practice_status.school_approved
                            ? "greenSmall"
                            : "yellowSmall"
                        }
                        pointer={false}
                      >
                        {entity.student_practice_status.school_approved
                          ? "Schváleno"
                          : "Čeká"}
                      </Button>
                    </Container>
                    <Container property="flex items-center gap-2">
                      <Paragraph property="text-sm font-medium">
                        {"Schválení firmou"}:
                      </Paragraph>
                      <Button
                        variant={
                          entity.student_practice_status.employer_approved
                            ? "greenSmall"
                            : "yellowSmall"
                        }
                        pointer={false}
                      >
                        {entity.student_practice_status.employer_approved
                          ? "Schváleno"
                          : "Čeká"}
                      </Button>
                    </Container>
                  </Container>
                )}
            </Container>
          </ContainerForEntity>

          {/* REJECTED / DOCUMENTS_REJECTED BANNER - Show rejection reason */}
          {entity?.student_practice_status?.workflow_status &&
            ["REJECTED", "DOCUMENTS_REJECTED"].includes(
              entity.student_practice_status.workflow_status,
            ) &&
            entity?.student_practice_status?.rejection_reason && (
              <ContainerForEntity property="pl-8 pr-8 pt-4 pb-4 mb-2">
                <Container property="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-lg shadow-sm">
                  <Paragraph property="text-red-800 font-semibold text-sm">
                    {"Přihláška na praxi byla zamítnuta"}
                  </Paragraph>
                  <Paragraph property="text-red-700 text-sm mt-1">
                    {entity.student_practice_status.rejection_reason}
                  </Paragraph>
                </Container>
              </ContainerForEntity>
            )}

          {/* CONTENT_REJECTED BANNER - Student can see rejection reason and resubmit */}
          {user &&
            user.isStudent() &&
            entity?.student_practice_status?.workflow_status === "CONTENT_REJECTED" && (
              <ContainerForEntity property="pl-8 pr-8 pt-4 pb-4 mb-2">
                <Container property="bg-red-50 border-l-4 border-red-400 p-4 rounded-r-lg shadow-sm flex flex-col gap-3">
                  <Paragraph property="text-red-800 font-medium">
                    {`Obsah praxe byl zamítnut. Důvod: ${entity.student_practice_status.rejection_reason ||
                        "Není uvedeno"}`}
                  </Paragraph>
                  <Button variant="primary" onClick={handleResubmit} property="w-fit">
                    {"Upravit a znovu odeslat"}
                  </Button>
                </Container>
              </ContainerForEntity>
            )}

          {/* DOCUMENTS_REJECTED BANNER - C19-B/T2c repair loop: student replaces documents */}
          {user &&
            user.isStudent() &&
            entity?.student_practice_status?.workflow_status === "DOCUMENTS_REJECTED" && (
              <ContainerForEntity property="pl-8 pr-8 pt-4 pb-4 mb-2">
                <Container property="bg-red-50 border-l-4 border-red-400 p-4 rounded-r-lg shadow-sm flex flex-col gap-2">
                  <Paragraph property="text-red-800 font-medium">
                    {"Dokumenty byly zamítnuty. Nahraďte opravené soubory v panelu dokumentů níže — po nahrání odejdou ke kontrole garantovi."}
                  </Paragraph>
                  {entity?.student_practice_status?.rejection_reason && (
                    <Paragraph property="text-red-700 text-sm">
                      {entity.student_practice_status.rejection_reason}
                    </Paragraph>
                  )}
                </Container>
              </ContainerForEntity>
            )}

          {/* DOCUMENTS_RESUBMITTED BANNER - C19-B: upload ≠ approval, čeká na review */}
          {entity?.student_practice_status?.workflow_status === "DOCUMENTS_RESUBMITTED" && (
            <ContainerForEntity property="pl-8 pr-8 pt-4 pb-4 mb-2">
              <Container property="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-r-lg shadow-sm">
                <Paragraph property="text-yellow-800 font-medium">
                  {"Opravené dokumenty byly nahrány a čekají na kontrolu garantem. Schválení provede garant nebo škola."}
                </Paragraph>
              </Container>
            </ContainerForEntity>
          )}

          {/* DOCS PANEL - show for anyone except REJECTED, or show always for professors */}
          {entity?.student_practice_status?.workflow_status &&
            ((user.isProfessor() &&
              entity.student_practice_status.workflow_status !== "REJECTED") ||
              !["PENDING", "REJECTED"].includes(
                entity.student_practice_status.workflow_status,
              )) && (
              <DocsPanel
                entity={entity}
                docData={docs}
                handleDownload={handleDownload}
                handleUpload={handleUpload}
                handleManage={handleDocsPopUp}
                handleReview={handleReview}
              />
            )}

          {/* Document generation buttons — Professor/Admin/Employer */}
          {entity?.student_practice_status?.workflow_status &&
            !["PENDING", "REJECTED"].includes(
              entity.student_practice_status.workflow_status,
            ) &&
            (user.isDepartmentUser() ||
              user.isOrganizationUser() ||
              user.isAdmin()) && (
              <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-4"}>
                <Headings sizeTag="h4" property="mb-3">
                  {"Kontrola dokumentů"}
                </Headings>
                <Container property="flex flex-wrap gap-2">
                  <Button
                    variant="blueSmall"
                    property="text-sm"
                    onClick={() =>
                      handleGenerateDocument(
                        "contract",
                        "Generovat smlouvu",
                      )
                    }
                  >
                    {"Generovat smlouvu"}
                  </Button>
                  <Button
                    variant="blueSmall"
                    property="text-sm"
                    onClick={() =>
                      handleGenerateDocument(
                        "content",
                        "Generovat pracovní náplň",
                      )
                    }
                  >
                    {"Generovat pracovní náplň"}
                  </Button>
                  <Button
                    variant="blueSmall"
                    property="text-sm"
                    onClick={() =>
                      handleGenerateDocument(
                        "report",
                        "Generovat výkaz",
                      )
                    }
                  >
                    {"Generovat výkaz"}
                  </Button>
                  <Button
                    variant="blueSmall"
                    property="text-sm"
                    onClick={() =>
                      handleGenerateDocument(
                        "feedback",
                        "Generovat hodnocení",
                      )
                    }
                  >
                    {"Generovat hodnocení"}
                  </Button>
                </Container>
              </ContainerForEntity>
            )}

          <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
            <Container property="grid grid-cols-[auto,1fr] gap-4 mt-2 mb-4">
              {/* LOGO */}
              <Container property="w-32 h-32 rounded-lg p-4 flex items-center justify-center">
                <Image
                  src={entity?.image_base64}
                  alt={entity?.title}
                  objectFit="cover"
                />
              </Container>

              {/* TITLE */}
              <Container>
                <Headings sizeTag={"h4"} property={""}>
                  {entity?.title}
                </Headings>
                {entity?.student_practice_status?.workflow_status && (
                  <Container property="mt-2">
                    <StateBadge
                      status={entity.student_practice_status.workflow_status}
                    />
                  </Container>
                )}
                <Container property={"flex flex-row gap-2 mt-2"}>
                  <Button
                    variant="blueSmallNoHover"
                    pointer={false}
                    property="w-fit"
                  >
                    {"Místo konání"}:{" "}
                    {entity?.employer?.address || "Není uvedeno"}
                  </Button>
                  <Button
                    variant="blueSmallNoHover"
                    pointer={false}
                    property="w-fit"
                  >
                    {entity?.start_date} - {entity?.end_date}
                  </Button>
                </Container>
              </Container>
            </Container>
            {/* DESCRIPTION */}
            <Container property={"editor-content mt-2"}>
              <Headings sizeTag="h3" property="mb-2">
                {"Popis pozice"}
              </Headings>
              <Paragraph>{entity?.description}</Paragraph>
            </Container>

            {/* RESPONSIBILITY */}
            <Container property={"editor-content mt-4"}>
              <Headings sizeTag="h3" property="mb-2">
                {"Náplň práce"}
              </Headings>
              <Paragraph>{entity?.responsibilities}</Paragraph>
            </Container>

            {/* CONTACT USER INFO */}
            {entity && entity.contact_user_info && (
              <Container property={"editor-content mt-2"}>
                <Headings sizeTag="h3" property="mb-4">
                  {"Kontaktní osoba"}
                </Headings>
                {entity.contact_user_info.username && (
                  <Paragraph property="mb-2">
                    {"Uživatelské jméno"}:{" "}
                    {entity.contact_user_info.username}
                  </Paragraph>
                )}
                {(entity.contact_user_info.first_name ||
                  entity.contact_user_info.last_name) && (
                  <Paragraph property="mb-2">
                    {"Správce inzerátu"}:{" "}
                    {`${entity.contact_user_info.first_name || ""} ${entity.contact_user_info.last_name || ""}`.trim()}
                  </Paragraph>
                )}
                {entity.contact_user_info.email && (
                  <Paragraph property="mb-2">
                    {"Email"}: {entity.contact_user_info.email}
                  </Paragraph>
                )}
                {entity.contact_user_info.phone && (
                  <Paragraph property="mb-2">
                    {"Telefonní číslo"}: {entity.contact_user_info.phone}
                  </Paragraph>
                )}
              </Container>
            )}
            <Container property={"grid grid-cols-1 gap-8 mt-4"}>
              {/* TLAČÍTKO PRO PODÁNÍ PŘIHLÁŠKY */}
              {user && user.isStudent() && !entity?.student_practice_status && (
                <Button
                  property="col-start-1 justify-self-end w-full"
                  onClick={handlePopUp}
                >
                  {"Podat přihlášku"}
                </Button>
              )}

              {/* TLAČÍTKA PRO SPRÁVU */}
              {user && entity?.can_approve && entity?.student_practice_status?.workflow_status !== "UNKNOWN" && (
                <Container property="flex gap-4 justify-end">
                  <Button
                    variant={"primary"}
                    icon={"gear"}
                    onClick={handlePopUp}
                  >
                    {"Spravovat"}
                  </Button>
                </Container>
              )}

              {/* STAŽENÍ ŽÁDOSTI - student ve stavu APPLIED nebo PRELIMINARY_APPROVED */}
              {user &&
                user.isStudent() &&
                entity?.student_practice_status &&
                ["APPLIED", "PRELIMINARY_APPROVED"].includes(
                  entity.student_practice_status.workflow_status,
                ) && (
                  <Container property="flex justify-end">
                    <Button
                      variant="red"
                      property="px-4 py-2 text-sm font-medium"
                      onClick={() => setWithdrawPopUp(true)}
                    >
                      {"Odhlásit se z praxe"}
                    </Button>
                  </Container>
                )}

              {/* STORNO - vlastník-student z aktivního stavu, okamžité a nevratné (A-12) */}
              {canRequestCancellation(entity, user) && (
                <Container property="flex justify-end">
                  <Button
                    variant="red"
                    property="px-4 py-2 text-sm font-medium"
                    onClick={() => {
                      setCancelReason("");
                      setCancelPopUp(true);
                    }}
                  >
                    {"Stornovat praxi"}
                  </Button>
                </Container>
              )}

              {/* STORNO STUDENTEM - blokuje novou žádost, dokud ho garant nevezme na vědomí (A-12) */}
              {entity?.student_practice_status && isCancellationPending(entity) && (
                <Container property="flex flex-col gap-3 items-end">
                  <Container property="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-r-lg shadow-sm w-full">
                    <Paragraph property="text-yellow-800 font-medium text-sm">
                      {canResolveCancellation(user)
                        ? "Student tuto praxi stornoval. Vezměte storno na vědomí:"
                        : "Praxe je stornována. Novou žádost o praxi můžete podat, až garant storno vezme na vědomí."}
                    </Paragraph>
                    {entity?.cancellation_reason && (
                      <Paragraph property="text-yellow-700 text-sm mt-1">
                        {`Důvod studenta: ${entity.cancellation_reason}`}
                      </Paragraph>
                    )}
                  </Container>
                  {/* VZETÍ NA VĚDOMÍ - jen garant (VY/VK) / admin (A-12) */}
                  {canResolveCancellation(user) && (
                    <Container property="flex gap-4 justify-end">
                      <Button variant="greenSmall" onClick={handleResolveCancellation}>
                        {"Vzít na vědomí"}
                      </Button>
                    </Container>
                  )}
                </Container>
              )}

              {/* REVIEW OPRAVNÝCH DOKUMENTŮ - DOCUMENTS_RESUBMITTED (C19-B/T2c) */}
              {entity?.student_practice_status?.workflow_status ===
                "DOCUMENTS_RESUBMITTED" &&
                canReviewResubmittedDocuments(user) && (
                  <Container property="flex flex-wrap gap-4 justify-end">
                    <Button
                      variant="greenSmall"
                      onClick={() => handleRepairApprove(5)}
                    >
                      {"Schválit opravu (Ukončeno)"}
                    </Button>
                    <Button
                      variant="blueSmall"
                      onClick={() => handleRepairApprove(8)}
                    >
                      {"Schválit opravu (kontrola dokumentů)"}
                    </Button>
                    <Button
                      variant="red"
                      onClick={() => openRepairPopup("reject")}
                    >
                      {"Zamítnout opravu"}
                    </Button>
                    {canTerminalReject(user) && (
                      <Button
                        variant="red"
                        onClick={() => openRepairPopup("terminal")}
                      >
                        {"Trvale zamítnout (REJECTED)"}
                      </Button>
                    )}
                  </Container>
                )}

              {/* FEEDBACK REVIEW - garant/škola schvaluje hodnotící podklad (FE-007) */}
              {["ENDED", "DOCUMENTS_REJECTED", "DOCUMENTS_RESUBMITTED"].includes(entity?.student_practice_status?.workflow_status) &&
                canReviewResubmittedDocuments(user) &&
                docs.find((d) => d.type === "feedback") && (
                  <Container property="flex flex-wrap gap-4 justify-end items-center">
                    <Paragraph property="text-sm font-medium">
                      {"Zpětná vazba"}
                    </Paragraph>
                    <Button
                      variant="greenSmall"
                      disabled={docs.find((d) => d.type === "feedback").status === 1}
                      onClick={() =>
                        handleReview(docs.find((d) => d.type === "feedback").id, 1)
                      }
                    >
                      {"Schválit"}
                    </Button>
                    <Button
                      variant="red"
                      disabled={docs.find((d) => d.type === "feedback").status === 2}
                      onClick={() =>
                        handleReview(docs.find((d) => d.type === "feedback").id, 2)
                      }
                    >
                      {"Zamítnout"}
                    </Button>
                  </Container>
                )}

              {/* DOKONČENÍ - ENDED → COMPLETED jen se schválenými podklady (FE-007/RF-15) */}
              {entity?.student_practice_status?.workflow_status === "ENDED" &&
                (user.isDepartmentUser() || user.isAdmin()) && (
                  <Container property="flex justify-end">
                    <Button variant="greenSmall" onClick={handleComplete}>
                      {"Udělit zápočet (Splněno)"}
                    </Button>
                  </Container>
                )}

              {/* Potvrzení smlouvy organizací nebo jejího přijetí studentem. */}
              {user &&
                (user.isOrganizationUser() || user.isStudent() || user.isProfessor() || user.isDepartmentUser() || user.isAdmin()) &&
                // D-1: u individuální (externí) praxe se smlouva potvrzuje i z „Obsah praxe schválen“.
                ([
                  "AWAITING_CONTRACT",
                  "AWAITING_DOCUMENTS",
                  ...(entity?.is_external ? ["CONTENT_APPROVED"] : []),
                ].includes(entity?.student_practice_status?.workflow_status)) && (
                  <Container property="flex gap-4 justify-end">
                    <Button
                      variant="greenSmall"
                      onClick={handleConfirmContract}
                    >
                      {"Potvrdit přijetí smlouvy"}
                    </Button>
                  </Container>
                )}
            </Container>
          </ContainerForEntity>

          {/* TIMELINE - historie změn stavu */}
          {entity?.student_practice_status && (
            <ContainerForEntity property="pl-8 pr-8 pt-4 pb-8 mt-2">
              <Headings sizeTag="h4" property="mb-4">
                {"Historie praxe"}
              </Headings>
              <Timeline
                studentPracticeId={id}
                currentStatus={entity.student_practice_status.workflow_status}
                refreshKey={timelineRefreshKey}
              />
            </ContainerForEntity>
          )}

          {entity?.student_practice_status?.workflow_status &&
            !["PENDING", "REJECTED"].includes(
              entity.student_practice_status.workflow_status,
            ) && (
              <Container property={"mt-2"}>
                <ProgressPanel
                  subject={entity.subject?.subject_code}
                  goalValueSingle={entity.subject?.hours_required}
                  currentValueSingle={
                    entity.student_practice_status?.hours_completed
                  }
                />
              </Container>
            )}

          {/* PODÁNÍ PŘIHLÁŠKY - STUDENT */}
          {popUp && user && user.isStudent() && (
            <PopUpCon
              useCustomContainer={true}
              onClose={handlePopUp}
              title={"Přihlášky"}
              text={"Opravdu chcete podat přihlášku na tuto praxi?"}
              onSubmit={handleApply}
              onSubmitText={"Podat"}
              onReject={handlePopUp}
              onRejectText={"Zrušit"}
            />
          )}

          {/* SCHVALOVÁNÍ PŘIHLÁŠKY - UČITEL/ORGANIZACE/ADMIN */}
          {popUp &&
            user &&
            (user.isDepartmentUser() ||
              user.isOrganizationUser() ||
              user.isAdmin()) && (
              <PopUpCon
                onClose={handlePopUp}
                title={"Správa přihlášky"}
                text={`Chcete schválit nebo zamítnout přihlášku studenta ${entity?.student_practice_status?.student_info
                    ?.full_name}?`}
                onSubmit={handleApprove}
                onSubmitText={"Schválit"}
                onReject={handleReject}
                onRejectText={"Zamítnout"}
              />
            )}

          {/* KONTROLA DOKUMENTŮ */}
          {docsPopUp && (
            <PopUpCon
              useCustomContainer={true}
              onClose={handleDocsPopUp}
              title={"Kontrola dokumentů"}
              text={"Proces není definován"}
            />
          )}

          {/* REJECT MODAL S DŮVODEM */}
          {rejectPopUp && (
            <PopUpCon
              onClose={() => {
                setRejectPopUp(false);
                setRejectReason("");
              }}
              title={"Důvod zamítnutí"}
              text={"Zadejte důvod zamítnutí obsahu praxe. Tento důvod uvidí student."}
              onSubmit={handleRejectWithReason}
              onSubmitText={"Zamítnout"}
              onReject={() => {
                setRejectPopUp(false);
                setRejectReason("");
              }}
              onRejectText={"Zrušit"}
            >
              <Container property="mt-4 mb-4 px-4">
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder={"Minimálně 10 znaků..."}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px] resize-none text-sm"
                />
                {rejectReason.trim().length > 0 && rejectReason.trim().length < 10 && (
                  <Paragraph property="text-red-500 text-xs mt-2">
                    {"Důvod zamítnutí musí mít alespoň 10 znaků"}
                  </Paragraph>
                )}
              </Container>
            </PopUpCon>
          )}

          {/* WITHDRAW MODAL */}
          {withdrawPopUp && (
            <PopUpCon
              onClose={() => setWithdrawPopUp(false)}
              title={"Odhlášení z praxe"}
              text={"Opravdu si přejete odstoupit z praxe?"}
              onSubmit={handleWithdraw}
              onSubmitText={"Odstoupit"}
              onReject={() => setWithdrawPopUp(false)}
              onRejectText={"Zrušit"}
            />
          )}

          {/* STORNO MODAL (A-12) */}
          {cancelPopUp && (
            <PopUpCon
              onClose={() => {
                setCancelPopUp(false);
                setCancelReason("");
              }}
              title={"Stornovat praxi"}
              text={"Praxe bude okamžitě stornována a storno je nevratné. Důvod je povinný."}
              onSubmit={handleRequestCancellation}
              onSubmitText={"Odeslat"}
              onReject={() => {
                setCancelPopUp(false);
                setCancelReason("");
              }}
              onRejectText={"Zrušit"}
            >
              <Container property="mt-4 mb-4 px-4">
                <textarea
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder={"Důvod ukončení"}
                  aria-label={"Důvod ukončení"}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px] resize-none text-sm"
                />
                {cancelReason.trim().length === 0 && (
                  <Paragraph property="text-red-500 text-xs mt-2">
                    {"Důvod storno je povinný"}
                  </Paragraph>
                )}
              </Container>
            </PopUpCon>
          )}

          {/* REVIEW ROZHODNUTÍ O OPRAVNÝCH DOKUMENTECH MODAL (C19-B/T2c) */}
          {repairPopUp && (
            <PopUpCon
              onClose={() => {
                setRepairPopUp(false);
                setRepairDecision(null);
                setRepairReason("");
              }}
              title={
                repairDecision === "terminal"
                  ? "Trvalé zamítnutí přihlášky"
                  : "Kontrola opravných dokumentů"
              }
              text={
                repairDecision === "terminal"
                  ? "Tato akce je nevratná a je vyhrazena administrátorovi. Zadejte důvod zamítnutí."
                  : "Rozhodněte o nahrazených dokumentech. Zamítnutí vrátí praxi studentovi k další opravě."
              }
              onSubmit={handleRepairDecision}
              onSubmitText={"Zamítnout"}
              onReject={() => {
                setRepairPopUp(false);
                setRepairDecision(null);
                setRepairReason("");
              }}
              onRejectText={"Zrušit"}
            >
              <Container property="mt-4 mb-4 px-4">
                <textarea
                  value={repairReason}
                  onChange={(e) => setRepairReason(e.target.value)}
                  placeholder={"Minimálně 10 znaků..."}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px] resize-none text-sm"
                />
                {repairReason.trim().length > 0 && repairReason.trim().length < 10 && (
                  <Paragraph property="text-red-500 text-xs mt-2">
                    {"Důvod zamítnutí musí mít alespoň 10 znaků"}
                  </Paragraph>
                )}
              </Container>
            </PopUpCon>
          )}
        </>
      )}
    </>
  );
}
