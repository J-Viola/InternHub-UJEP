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
import { useTranslation } from "react-i18next";
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
  const { t } = useTranslation();
  const { id } = useParams();
  const [popUp, setPopUp] = useState(false);
  const [docsPopUp, setDocsPopUp] = useState(false);
  const [rejectPopUp, setRejectPopUp] = useState(false);
  const [withdrawPopUp, setWithdrawPopUp] = useState(false);
  const [rejectReason, setRejectReason] = useState("");
  // C02-A/T2d: žádost o storno (student) + rozhodnutí (garant/admin)
  const [cancelPopUp, setCancelPopUp] = useState(false);
  const [cancelReason, setCancelReason] = useState("");
  const [resolvePopUp, setResolvePopUp] = useState(false);
  const [resolveDecision, setResolveDecision] = useState(null);
  const [resolveReason, setResolveReason] = useState("");
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
          addMessage(t("practice_detail.card_load_error"), "E");
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
      addMessage(t("practice_detail.download_error"), "E");
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
        addMessage(t("practice_detail.upload_success"), "S");
        fetchData();
      } catch (error) {
        addMessage(t("practice_detail.upload_error"), "E");
      }
    };
    input.click();
  };

  const handleReview = async (documentId, status) => {
    // Simple prompt for note if rejecting, or just approve
    let note = "";
    if (status === 2) {
      // REJECTED
      note = prompt(t("docs.reject_note_prompt")) || "";
    }

    try {
      await documentAPI.reviewDocument(documentId, status, note);
      addMessage(t("docs.review_success"), "S");
      fetchData();
    } catch (error) {
      addMessage(t("docs.review_error"), "E");
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
      addMessage(t("practice_detail.generate_success"), "S");
    } catch (error) {
      addMessage(t("practice_detail.generate_error"), "E");
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
        addMessage(t("practice_detail.apply_success"), "S");
        handlePopUp();
        fetchData();
      }
    } catch (error) {
      console.error(error);
      // kapacita (CAPACITY_FULL) i ostatní serverové chyby se zobrazí čistě
      addMessage(getApiErrorMessage(error, t, "practice_detail.apply_error"), "E");
    }
  };

  const handleApprove = async () => {
    try {
      await studentpraticeAPI.updateStudentPracticeStatus(id, "approve", {
        workflowStatus: entity?.student_practice_status?.workflow_status,
      });
      addMessage(t("practice_detail.approve_success"), "S");
      fetchData();
      setPopUp(false);
    } catch (error) {
      addMessage(getApiErrorMessage(error, t, "practice_detail.approve_error"), "E");
    }
  };

  const handleReject = () => {
    setRejectReason("");
    setRejectPopUp(true);
    setPopUp(false);
  };

  const handleRejectWithReason = async () => {
    if (rejectReason.trim().length < 10) {
      addMessage(t("practice_detail.reject_reason_required"), "E");
      return;
    }
    try {
      await studentpraticeAPI.updateStudentPracticeStatus(id, "reject", {
        reason: rejectReason.trim(),
        workflowStatus: entity?.student_practice_status?.workflow_status,
      });
      addMessage(t("practice_detail.reject_success"), "S");
      fetchData();
      setRejectPopUp(false);
      setRejectReason("");
    } catch (error) {
      addMessage(getApiErrorMessage(error, t, "practice_detail.reject_error"), "E");
    }
  };

  const handleConfirmContract = async () => {
    try {
      // T2b: potvrzení je idempotentní (opakování stejné osy = 200 no-op);
      // UI nabízí akci jen ve stavu AWAITING_CONTRACT, kde by jinde 400.
      await studentpraticeAPI.confirmContract(id);
      addMessage(t("practice_detail.confirm_contract_success"), "S");
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, t, "practice_detail.confirm_contract_error"), "E");
    }
  };

  const handleResubmit = async () => {
    try {
      await studentpraticeAPI.updateStudentPracticeStatus(id, "resubmit", {
        workflowStatus: entity?.student_practice_status?.workflow_status,
      });
      addMessage(t("practice_detail.resubmit_success"), "S");
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, t, "practice_detail.resubmit_error"), "E");
    }
  };

  const handleWithdraw = async () => {
    try {
      await studentpraticeAPI.withdrawApplication(id);
      addMessage(t("practice_detail.withdraw_success"), "S");
      setWithdrawPopUp(false);
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, t, "practice_detail.withdraw_error"), "E");
    }
  };

  // --- C02-A: žádost o storno (student, vlastní přihláška) ---
  const handleRequestCancellation = async () => {
    if (!cancelReason.trim()) {
      addMessage(t("practice_detail.cancel_request_reason_required"), "E");
      return;
    }
    try {
      await studentpraticeAPI.requestCancellation(id, cancelReason.trim());
      addMessage(t("practice_detail.cancel_request_success"), "S");
      setCancelPopUp(false);
      setCancelReason("");
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, t, "practice_detail.cancel_request_error"), "E");
    }
  };

  const openResolvePopup = (decision) => {
    setResolveDecision(decision);
    setResolveReason("");
    setResolvePopUp(true);
  };

  // --- T2d: rozhodnutí garanta/admina o žádosti o storno ---
  const handleResolveCancellation = async () => {
    if (!resolveDecision) return;
    if (resolveReason.trim().length < 10) {
      addMessage(t("practice_detail.reject_reason_required"), "E");
      return;
    }
    try {
      await studentpraticeAPI.resolveCancellation(id, resolveDecision, resolveReason.trim());
      addMessage(t("practice_detail.cancellation_resolve_success"), "S");
      setResolvePopUp(false);
      setResolveDecision(null);
      setResolveReason("");
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, t, "practice_detail.cancellation_resolve_error"), "E");
    }
  };

  // --- FE-007: dokončení ENDED → COMPLETED (server vynucuje Evaluation +
  // schválený FEEDBACK dokument, jinak 400 s čitelnou hláškou) ---
  const handleComplete = async () => {
    try {
      await studentpraticeAPI.transitionStudentPractice(id, 6, "");
      addMessage(t("practice_detail.complete_success"), "S");
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, t, "practice_detail.complete_error"), "E");
    }
  };

  // --- C19-B/T2c: review rozhoduje o DOCUMENTS_RESUBMITTED ---
  const handleRepairApprove = async (targetState) => {
    try {
      await studentpraticeAPI.transitionStudentPractice(id, targetState, "");
      addMessage(t("practice_detail.repair_action_success"), "S");
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, t, "practice_detail.repair_action_error"), "E");
    }
  };

  const openRepairPopup = (decision) => {
    setRepairDecision(decision);
    setRepairReason("");
    setRepairPopUp(true);
  };

  const handleRepairDecision = async () => {
    if (repairReason.trim().length < 10) {
      addMessage(t("practice_detail.reject_reason_required"), "E");
      return;
    }
    // 'reject' → DOCUMENTS_REJECTED (smyčka pokračuje);
    // 'terminal' → REJECTED (jen admin + důvod, T2c/R44)
    const targetState = repairDecision === "terminal" ? 2 : 9;
    try {
      await studentpraticeAPI.transitionStudentPractice(id, targetState, repairReason.trim());
      addMessage(t("practice_detail.repair_action_success"), "S");
      setRepairPopUp(false);
      setRepairDecision("");
      setRepairReason("");
      fetchData();
    } catch (error) {
      addMessage(getApiErrorMessage(error, t, "practice_detail.repair_action_error"), "E");
    }
  };

  return (
    <>
      <BackButton />

      {loading && <LoadingState message={t("common.loading")} />}

      {!loading && loadError && (
        <ErrorState
          description={t("practice_detail.card_load_error")}
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
                  {t("practice_detail.student_title")}
                </Headings>
                <Paragraph property={"mt-2"}>
                  {entity?.student_practice_status?.student_info?.full_name}
                </Paragraph>
                <Paragraph>
                  {`${t("students.personal_number")}: ${entity?.student_practice_status?.student_info?.os_cislo}`}
                </Paragraph>
                <Paragraph>
                  {`${t("profile.email")}: ${entity?.student_practice_status?.student_info?.email}`}
                </Paragraph>
              </Container>

              {/* DUAL APPROVAL STATUS FOR PROFESSORS */}
              {user &&
                user.isProfessor() &&
                entity?.student_practice_status && (
                  <Container property="flex flex-col gap-2 items-end">
                    <Container property="flex items-center gap-2">
                      <Paragraph property="text-sm font-medium">
                        {t("practice_detail.school_approval")}:
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
                          ? t("practice_detail.approved")
                          : t("practice_detail.pending")}
                      </Button>
                    </Container>
                    <Container property="flex items-center gap-2">
                      <Paragraph property="text-sm font-medium">
                        {t("practice_detail.employer_approval")}:
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
                          ? t("practice_detail.approved")
                          : t("practice_detail.pending")}
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
                    {t("practice_detail.rejected_banner")}
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
                    {t("practice_detail.content_rejected_banner", {
                      reason:
                        entity.student_practice_status.rejection_reason ||
                        t("common.not_specified"),
                    })}
                  </Paragraph>
                  <Button variant="primary" onClick={handleResubmit} property="w-fit">
                    {t("practice_detail.resubmit_button")}
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
                    {t("practice_detail.documents_rejected_banner")}
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
                  {t("practice_detail.documents_resubmitted_banner")}
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
                  {t("practice_detail.docs_check_title")}
                </Headings>
                <Container property="flex flex-wrap gap-2">
                  <Button
                    variant="blueSmall"
                    property="text-sm"
                    onClick={() =>
                      handleGenerateDocument(
                        "contract",
                        t("practice_detail.generate_contract"),
                      )
                    }
                  >
                    {t("practice_detail.generate_contract")}
                  </Button>
                  <Button
                    variant="blueSmall"
                    property="text-sm"
                    onClick={() =>
                      handleGenerateDocument(
                        "content",
                        t("practice_detail.generate_content"),
                      )
                    }
                  >
                    {t("practice_detail.generate_content")}
                  </Button>
                  <Button
                    variant="blueSmall"
                    property="text-sm"
                    onClick={() =>
                      handleGenerateDocument(
                        "report",
                        t("practice_detail.generate_report"),
                      )
                    }
                  >
                    {t("practice_detail.generate_report")}
                  </Button>
                  <Button
                    variant="blueSmall"
                    property="text-sm"
                    onClick={() =>
                      handleGenerateDocument(
                        "feedback",
                        t("practice_detail.generate_feedback"),
                      )
                    }
                  >
                    {t("practice_detail.generate_feedback")}
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
                    {t("offers.location")}:{" "}
                    {entity?.employer?.address || t("common.not_specified")}
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
                {t("offers.responsibilities")}
              </Headings>
              <Paragraph>{entity?.description}</Paragraph>
            </Container>

            {/* RESPONSIBILITY */}
            <Container property={"editor-content mt-4"}>
              <Headings sizeTag="h3" property="mb-2">
                {t("offers.requirements")}
              </Headings>
              <Paragraph>{entity?.responsibilities}</Paragraph>
            </Container>

            {/* CONTACT USER INFO */}
            {entity && entity.contact_user_info && (
              <Container property={"editor-content mt-2"}>
                <Headings sizeTag="h3" property="mb-4">
                  {t("offers.contact_person")}
                </Headings>
                {entity.contact_user_info.username && (
                  <Paragraph property="mb-2">
                    {t("practice_detail.username_label")}:{" "}
                    {entity.contact_user_info.username}
                  </Paragraph>
                )}
                {(entity.contact_user_info.first_name ||
                  entity.contact_user_info.last_name) && (
                  <Paragraph property="mb-2">
                    {t("form.contact_user")}:{" "}
                    {`${entity.contact_user_info.first_name || ""} ${entity.contact_user_info.last_name || ""}`.trim()}
                  </Paragraph>
                )}
                {entity.contact_user_info.email && (
                  <Paragraph property="mb-2">
                    {t("profile.email")}: {entity.contact_user_info.email}
                  </Paragraph>
                )}
                {entity.contact_user_info.phone && (
                  <Paragraph property="mb-2">
                    {t("profile.phone")}: {entity.contact_user_info.phone}
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
                  {t("offers.apply")}
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
                    {t("common.manage")}
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
                      {t("practice_detail.withdraw_button")}
                    </Button>
                  </Container>
                )}

              {/* ŽÁDOST O STORNO - vlastník-student ze stavu CONTRACTED (C02-A) */}
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
                    {t("practice_detail.cancel_request_button")}
                  </Button>
                </Container>
              )}

              {/* PENDING ŽÁDOST O STORNO - stav se nemění, dokud resolver nerozhodne */}
              {entity?.student_practice_status && isCancellationPending(entity) && (
                <Container property="flex flex-col gap-3 items-end">
                  <Container property="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-r-lg shadow-sm w-full">
                    <Paragraph property="text-yellow-800 font-medium text-sm">
                      {canResolveCancellation(user)
                        ? t("practice_detail.cancellation_pending_resolver")
                        : t("practice_detail.cancellation_pending_student")}
                    </Paragraph>
                    {entity?.cancellation_reason && (
                      <Paragraph property="text-yellow-700 text-sm mt-1">
                        {`${t("practice_detail.cancellation_reason_label")}: ${entity.cancellation_reason}`}
                      </Paragraph>
                    )}
                  </Container>
                  {/* ROZHODNUTÍ RESOLVERA - jen garant (VY/VK) / admin (T2d) */}
                  {canResolveCancellation(user) && (
                    <Container property="flex gap-4 justify-end">
                      <Button
                        variant="greenSmall"
                        onClick={() => openResolvePopup("approve")}
                      >
                        {t("practice_detail.cancellation_approve")}
                      </Button>
                      <Button
                        variant="red"
                        onClick={() => openResolvePopup("reject")}
                      >
                        {t("practice_detail.cancellation_reject")}
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
                      {t("practice_detail.repair_approve")}
                    </Button>
                    <Button
                      variant="blueSmall"
                      onClick={() => handleRepairApprove(8)}
                    >
                      {t("practice_detail.repair_approve_continue")}
                    </Button>
                    <Button
                      variant="red"
                      onClick={() => openRepairPopup("reject")}
                    >
                      {t("practice_detail.repair_reject")}
                    </Button>
                    {canTerminalReject(user) && (
                      <Button
                        variant="red"
                        onClick={() => openRepairPopup("terminal")}
                      >
                        {t("practice_detail.terminal_reject")}
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
                      {t("docs.feedback")}
                    </Paragraph>
                    <Button
                      variant="greenSmall"
                      disabled={docs.find((d) => d.type === "feedback").status === 1}
                      onClick={() =>
                        handleReview(docs.find((d) => d.type === "feedback").id, 1)
                      }
                    >
                      {t("common.approve")}
                    </Button>
                    <Button
                      variant="red"
                      disabled={docs.find((d) => d.type === "feedback").status === 2}
                      onClick={() =>
                        handleReview(docs.find((d) => d.type === "feedback").id, 2)
                      }
                    >
                      {t("common.reject")}
                    </Button>
                  </Container>
                )}

              {/* DOKONČENÍ - ENDED → COMPLETED jen se schválenými podklady (FE-007/RF-15) */}
              {entity?.student_practice_status?.workflow_status === "ENDED" &&
                (user.isDepartmentUser() || user.isAdmin()) && (
                  <Container property="flex justify-end">
                    <Button variant="greenSmall" onClick={handleComplete}>
                      {t("practice_detail.complete_button")}
                    </Button>
                  </Container>
                )}

              {/* Potvrzení smlouvy organizací nebo jejího přijetí studentem. */}
              {user &&
                (user.isOrganizationUser() || user.isStudent() || user.isProfessor() || user.isDepartmentUser() || user.isAdmin()) &&
                entity?.student_practice_status?.workflow_status === "AWAITING_CONTRACT" && (
                  <Container property="flex gap-4 justify-end">
                    <Button
                      variant="greenSmall"
                      onClick={handleConfirmContract}
                    >
                      {t("practice_detail.confirm_contract")}
                    </Button>
                  </Container>
                )}
            </Container>
          </ContainerForEntity>

          {/* TIMELINE - historie změn stavu */}
          {entity?.student_practice_status && (
            <ContainerForEntity property="pl-8 pr-8 pt-4 pb-8 mt-2">
              <Headings sizeTag="h4" property="mb-4">
                {t("practice_detail.timeline_title")}
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
              title={t("nav.applications")}
              text={t("internships.start_practice_confirm")}
              onSubmit={handleApply}
              onSubmitText={t("practice_detail.apply_button")}
              onReject={handlePopUp}
              onRejectText={t("common.cancel")}
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
                title={t("practice_detail.manage_app")}
                text={t("practice_detail.confirm_app_text", {
                  name: entity?.student_practice_status?.student_info
                    ?.full_name,
                })}
                onSubmit={handleApprove}
                onSubmitText={t("common.approve")}
                onReject={handleReject}
                onRejectText={t("common.reject")}
              />
            )}

          {/* KONTROLA DOKUMENTŮ */}
          {docsPopUp && (
            <PopUpCon
              useCustomContainer={true}
              onClose={handleDocsPopUp}
              title={t("practice_detail.docs_check_title")}
              text={t("practice_detail.docs_check_not_defined")}
            />
          )}

          {/* REJECT MODAL S DŮVODEM */}
          {rejectPopUp && (
            <PopUpCon
              onClose={() => {
                setRejectPopUp(false);
                setRejectReason("");
              }}
              title={t("practice_detail.reject_reason_title")}
              text={t("practice_detail.reject_reason_text")}
              onSubmit={handleRejectWithReason}
              onSubmitText={t("common.reject")}
              onReject={() => {
                setRejectPopUp(false);
                setRejectReason("");
              }}
              onRejectText={t("common.cancel")}
            >
              <Container property="mt-4 mb-4 px-4">
                <textarea
                  value={rejectReason}
                  onChange={(e) => setRejectReason(e.target.value)}
                  placeholder={t("practice_detail.reject_reason_placeholder")}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px] resize-none text-sm"
                />
                {rejectReason.trim().length > 0 && rejectReason.trim().length < 10 && (
                  <Paragraph property="text-red-500 text-xs mt-2">
                    {t("practice_detail.reject_reason_required")}
                  </Paragraph>
                )}
              </Container>
            </PopUpCon>
          )}

          {/* WITHDRAW MODAL */}
          {withdrawPopUp && (
            <PopUpCon
              onClose={() => setWithdrawPopUp(false)}
              title={t("practice_detail.withdraw_title")}
              text={t("practice_detail.withdraw_text")}
              onSubmit={handleWithdraw}
              onSubmitText={t("practice_detail.withdraw_confirm")}
              onReject={() => setWithdrawPopUp(false)}
              onRejectText={t("common.cancel")}
            />
          )}

          {/* ŽÁDOST O STORNO MODAL (C02-A) */}
          {cancelPopUp && (
            <PopUpCon
              onClose={() => {
                setCancelPopUp(false);
                setCancelReason("");
              }}
              title={t("practice_detail.cancel_request_title")}
              text={t("practice_detail.cancel_request_text")}
              onSubmit={handleRequestCancellation}
              onSubmitText={t("practice_detail.cancel_request_confirm")}
              onReject={() => {
                setCancelPopUp(false);
                setCancelReason("");
              }}
              onRejectText={t("common.cancel")}
            >
              <Container property="mt-4 mb-4 px-4">
                <textarea
                  value={cancelReason}
                  onChange={(e) => setCancelReason(e.target.value)}
                  placeholder={t("practice_detail.cancel_request_placeholder")}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px] resize-none text-sm"
                />
                {cancelReason.trim().length === 0 && (
                  <Paragraph property="text-red-500 text-xs mt-2">
                    {t("practice_detail.cancel_request_reason_required")}
                  </Paragraph>
                )}
              </Container>
            </PopUpCon>
          )}

          {/* ROZHODNUTÍ O ŽÁDOSTI O STORNO MODAL (T2d) */}
          {resolvePopUp && (
            <PopUpCon
              onClose={() => {
                setResolvePopUp(false);
                setResolveDecision(null);
                setResolveReason("");
              }}
              title={t("practice_detail.cancel_request_title")}
              text={
                resolveDecision === "approve"
                  ? t("practice_detail.cancellation_approve")
                  : t("practice_detail.cancellation_reject")
              }
              onSubmit={handleResolveCancellation}
              onSubmitText={t("common.approve")}
              onReject={() => {
                setResolvePopUp(false);
                setResolveDecision(null);
                setResolveReason("");
              }}
              onRejectText={t("common.cancel")}
            >
              <Container property="mt-4 mb-4 px-4">
                <textarea
                  value={resolveReason}
                  onChange={(e) => setResolveReason(e.target.value)}
                  placeholder={t("practice_detail.reject_reason_placeholder")}
                  aria-label={t("practice_detail.reject_reason_title")}
                  className="w-full p-3 border border-gray-300 rounded-lg min-h-[100px] resize-none text-sm"
                />
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
                  ? t("practice_detail.terminal_reject_title")
                  : t("practice_detail.repair_review_title")
              }
              text={
                repairDecision === "terminal"
                  ? t("practice_detail.terminal_reject_text")
                  : t("practice_detail.repair_review_text")
              }
              onSubmit={handleRepairDecision}
              onSubmitText={t("common.reject")}
              onReject={() => {
                setRepairPopUp(false);
                setRepairDecision(null);
                setRepairReason("");
              }}
              onRejectText={t("common.cancel")}
            >
              <Container property="mt-4 mb-4 px-4">
                <textarea
                  value={repairReason}
                  onChange={(e) => setRepairReason(e.target.value)}
                  placeholder={t("practice_detail.reject_reason_placeholder")}
                  className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[100px] resize-none text-sm"
                />
                {repairReason.trim().length > 0 && repairReason.trim().length < 10 && (
                  <Paragraph property="text-red-500 text-xs mt-2">
                    {t("practice_detail.reject_reason_required")}
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
