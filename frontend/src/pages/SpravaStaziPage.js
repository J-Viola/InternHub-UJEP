import React, { useState, useEffect, useMemo } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import PopUpCon from "@core/Container/PopUpCon";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI";
import { useNavigate, useSearchParams } from "react-router-dom";
import PraxeDepartmentEntity from "@components/Praxe/PraxeDepartmentEntity";
import { useUser } from "@hooks/UserProvider";
import { useMessage } from "@hooks/MessageContext";
import { useApi } from "@hooks/useApi";
import { daysSinceCzechDate, isOlderThan } from "@utils/dateUtils";
import { useSubjectAPI } from "@api/subject/subjectAPI";
import { getStateLabel } from "@core/StateBadge/StateBadge";

import getApiErrorMessage from "@utils/apiErrorUtils";
// Číselná mapa StateBadge obsahuje všech 14 stavů StudentPractice, nikoli stavy nabídek.
const exportWorkflowStates = Array.from({ length: 14 }, (_, value) => value);

const riskStyles = {
    APPROVAL_STALLED: { label: "Zdlouhavé schvalování", classes: 'bg-amber-100 text-amber-900 border-amber-300' },
    ENDED_NO_CREDIT: { label: "Ukončeno bez zápočtu déle než 14 dní", classes: 'bg-orange-100 text-orange-900 border-orange-300' },
    OVERDUE_END: { label: "Po termínu ukončení", classes: 'bg-red-100 text-red-900 border-red-300' },
};
const neutralRiskStyle = { label: "Jiné upozornění", classes: 'bg-gray-100 text-gray-800 border-gray-300' };

export default function SpravaStaziPage() {
    const [searchParams] = useSearchParams();
    const [approved, setApproved] = useState([]);
    const [toApprove, setToApprove] = useState([]);
    const [activeOffers, setActiveOffers] = useState([]);
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const nabidkaAPI = useNabidkaAPI();
    const navigate = useNavigate();
    const [showPop, setPop] = useState(false);
    const [selectedEntity, setSelectedEntity] = useState(null);
    const { user } = useUser();
    const { addMessage } = useMessage();
    const api = useApi();
    const subjectAPI = useSubjectAPI();
    const [exportFilters, setExportFilters] = useState({ year: '', workflow_state: '', subject_id: '', institution: '' });
    const [subjects, setSubjects] = useState([]);
    const [subjectsLoading, setSubjectsLoading] = useState(true);
    const [subjectsError, setSubjectsError] = useState(false);

    const activeFilter = searchParams.get("state") || "ALL";

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = user.isAdmin()
                ? await nabidkaAPI.getAdminPractices()
                : await nabidkaAPI.getNabidkyByUserDepartment();
            setApproved(res.approved_practices || []);
            setToApprove(res.to_approve_practices || []);
            // FE-004: schválené (automaticky aktivované) nabídky zůstávají viditelné.
            setActiveOffers(res.active_offers || []);

            try {
                const statsRes = await api.get('/dashboard/stats/');
                setStats(statsRes.data);
            } catch (sErr) {
                console.error("Chyba při načítání statistik dashboardu:", sErr);
            }
        } catch {
            setError("Nepodařilo se načíst stáže. Zkuste to prosím znovu.");
            setApproved([]);
            setToApprove([]);
            setActiveOffers([]);
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async (format) => {
        try {
            const params = { format };
            Object.entries(exportFilters).forEach(([key, value]) => {
                const trimmed = value.trim();
                if (trimmed) params[key] = trimmed;
            });
            const response = await api.get('/export-data/', {
                params,
                responseType: 'blob',
            });

            // HTTP 202 → async export se zpracovává.
            // Nestahujeme blob, jen informujeme; download přijde notifikací EXPORT_READY.
            if (response.status === 202) {
                addMessage("Export se zpracovává. Budete notifikováni po dokončení.", 'I');
                return;
            }

            // Obranná větev: někteří BE vrací 200 s JSON tělem pro async export
            // (transitional stav). Nestahujme poškozený soubor — JSON detekujeme
            // podle content-type a přítomnosti export_id/task_id.
            const contentType = response.headers?.['content-type'] || '';
            if (contentType.includes('application/json')) {
                try {
                    const text = await response.data.text();
                    const payload = JSON.parse(text);
                    if (payload && (payload.export_id || payload.task_id)) {
                        addMessage("Export se zpracovává. Budete notifikováni po dokončení.", 'I');
                        return;
                    }
                } catch {
                    // Není validní JSON — pokračuj jako soubor
                }
            }

            // Create a download link from the blob response
            const blob = new Blob([response.data]);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `praxe_export.${format}`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(url);
            addMessage(`Export ${format.toUpperCase()} byl úspěšně vygenerován.`, 'S');
        } catch (err) {
            const msg = err?.response?.data?.error || "Něco se pokazilo";
            addMessage(msg, 'E');
        }
    };

    const handleApprove = async () => {
        if (!selectedEntity) return;
        try {
            await nabidkaAPI.changeStatus(selectedEntity.practice_id, { "approval_status": 1 });
            setPop(false);
            setSelectedEntity(null);
            fetchData();
        } catch (error) {
            addMessage(getApiErrorMessage(error, "Něco se pokazilo"), "E");
            setPop(false);
            setSelectedEntity(null);
        }
    };

    const handleReject = async () => {
        if (!selectedEntity) return;
        try {
            await nabidkaAPI.changeStatus(selectedEntity.practice_id, { "approval_status": 2 });
            setPop(false);
            setSelectedEntity(null);
            fetchData();
        } catch (error) {
            addMessage(getApiErrorMessage(error, "Něco se pokazilo"), "E");
            setPop(false);
            setSelectedEntity(null);
        }
    };

    const handleClosePop = () => {
        setPop(false);
        setSelectedEntity(null);
    };

    useEffect(() => {
        fetchData();
        let cancelled = false;
        const loadSubjects = async () => {
            try {
                const result = user.isAdmin()
                    ? await subjectAPI.getAllSubjects()
                    : await subjectAPI.getDepartmentSubjects();
                if (!cancelled) setSubjects(Array.isArray(result) ? result : result.results || []);
            } catch {
                if (!cancelled) setSubjectsError(true);
            } finally {
                if (!cancelled) setSubjectsLoading(false);
            }
        };
        loadSubjects();
        return () => { cancelled = true; };
    }, []);

    const handleView = (type, entity) => {
        if (type === "approved_practices") {
            navigate(`/karta-praxe/${entity.student_practice_id}`)
        }
        if (type === "to_approve_practices" || type === "active_offers") {
            navigate(`/nabidka/${entity.practice_id}`)
        }
    }

    const handleClick = (type, entity = null) => {
        if (type === "to_approve_practices") {
            setSelectedEntity(entity);
            setPop(true);
        }
        if (type === "approved_practices") {
            navigate(`/students/${entity?.practice_id}`);
        }
    };

    // ID rizikových přihlášek přicházejí ve statistikách; seznam je používá pro filtr.
    const atRiskIds = useMemo(
        () => new Set((stats?.at_risk_items || []).map((item) => item.student_practice_id)),
        [stats]
    );

    // Filter approved practices based on URL state param
    const filteredApproved = useMemo(() => {
        if (activeFilter === "ALL") return approved;
        if (activeFilter === "AT_RISK") {
            return approved.filter((e) => atRiskIds.has(e.student_practice_id));
        }
        if (activeFilter === "CONTRACT_PENDING") {
            return approved.filter(
                (e) => e.workflow_state === "PRELIMINARY_APPROVED" && !e.contract_received_date
            );
        }
        return approved.filter((e) => e.workflow_state === activeFilter);
    }, [approved, activeFilter, atRiskIds]);

    // Escalation: practices in PRELIMINARY_APPROVED > 7 days without contract
    const escalatedPractices = useMemo(() => {
        return approved.filter((e) => {
            if (e.workflow_state !== "PRELIMINARY_APPROVED" || e.contract_received_date) return false;
            if (!e.updated_at) return false;
            return isOlderThan(e.updated_at, 7);
        });
    }, [approved]);

    const setFilter = (filter) => {
        if (filter === "ALL") {
            navigate('/sprava-stazi');
        } else {
            navigate(`/sprava-stazi?state=${filter}`);
        }
    };

    const filterTabs = [
        { key: "ALL", label: "Všechny" },
        { key: "STARTED", label: "Probíhá" },
        { key: "AWAITING_DOCUMENTS", label: "Čeká na dokumenty" },
        { key: "CONTRACT_PENDING", label: "Čeká na zasmluvnění" },
        { key: "AT_RISK", label: "Rizikové" },
    ];

    return(
        <>
            <BackButton/>

            {/* Dashboard Stats & Export Toolbar */}
            <Container property={"flex flex-col md:flex-row items-center justify-between mb-6 mt-4 gap-4"}>
                <Headings sizeTag={"h2"} property={"text-2xl font-bold"}>
                    {"Probíhající stáže"}
                </Headings>

            </Container>

            <form aria-label={"Filtry exportu"} onSubmit={(event) => {
                event.preventDefault();
                handleExport('xlsx');
            }} className="mb-6 rounded-lg border border-gray-200 bg-white p-4">
                <fieldset>
                    <legend className="text-sm font-semibold text-gray-900">{"Filtry exportu"}</legend>
                    <p className="mt-1 mb-3 text-xs text-gray-600">{"Filtry platí pouze pro export. Prázdná pole výběr neomezují."}</p>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
                        <label className="text-xs font-medium text-gray-700" htmlFor="export-year">
                            {"Rok"}
                            <input id="export-year" name="year" type="number" min="1" max="9999" step="1" value={exportFilters.year}
                                onChange={(event) => setExportFilters({ ...exportFilters, year: event.target.value })}
                                className="mt-1 block w-full rounded-md border border-gray-300 p-2 text-sm focus-visible:outline-blue-600" />
                        </label>
                        <label className="text-xs font-medium text-gray-700" htmlFor="export-state">
                            {"Stav praxe"}
                            <select id="export-state" name="workflow_state" value={exportFilters.workflow_state}
                                onChange={(event) => setExportFilters({ ...exportFilters, workflow_state: event.target.value })}
                                className="mt-1 block w-full rounded-md border border-gray-300 bg-white p-2 text-sm focus-visible:outline-blue-600">
                                <option value="">{"Všechny stavy"}</option>
                                {exportWorkflowStates.map((state) => <option key={state} value={state}>{getStateLabel(state)}</option>)}
                            </select>
                        </label>
                        <label className="text-xs font-medium text-gray-700" htmlFor="export-subject">
                            {"Předmět"}
                            <select id="export-subject" name="subject_id" value={exportFilters.subject_id} disabled={subjectsLoading || subjectsError}
                                aria-describedby={subjectsError ? 'export-subject-error' : undefined}
                                onChange={(event) => setExportFilters({ ...exportFilters, subject_id: event.target.value })}
                                className="mt-1 block w-full rounded-md border border-gray-300 bg-white p-2 text-sm focus-visible:outline-blue-600 disabled:bg-gray-100">
                                <option value="">{subjectsLoading ? "Načítání předmětů…" : "Všechny předměty"}</option>
                                {subjects.map((subject) => <option key={subject.subject_id} value={subject.subject_id}>{subject.subject_name}</option>)}
                            </select>
                        </label>
                        <label className="text-xs font-medium text-gray-700" htmlFor="export-institution">
                            {"Instituce"}
                            <input id="export-institution" name="institution" type="text" value={exportFilters.institution}
                                placeholder={"Část názvu firmy"}
                                onChange={(event) => setExportFilters({ ...exportFilters, institution: event.target.value })}
                                className="mt-1 block w-full rounded-md border border-gray-300 p-2 text-sm focus-visible:outline-blue-600" />
                        </label>
                    </div>
                    {subjectsError && <p id="export-subject-error" role="status" className="mt-2 text-xs text-red-700">{"Předměty se nepodařilo načíst. Export je dostupný bez filtru předmětu."}</p>}
                </fieldset>
                <div className="mt-3 flex flex-wrap justify-end gap-2">
                    <button
                        type="submit" value="xlsx"
                        className="bg-green-600 hover:bg-green-700 text-white text-xs px-3 py-2 rounded-md font-medium transition-colors"
                    >
                        {"Export XLSX"}
                    </button>
                    <button
                        type="button" onClick={(event) => {
                            if (event.currentTarget.form.reportValidity()) handleExport('csv');
                        }}
                        className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-3 py-2 rounded-md font-medium transition-colors"
                    >
                        {"Export CSV"}
                    </button>
                </div>
            </form>

            {/* Dashboard KPI Cards */}
            {stats && (
                <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
                    <div
                        className={`bg-white p-4 rounded-lg shadow-sm border cursor-pointer hover:shadow-md transition-shadow ${activeFilter === "ALL" ? 'ring-2 ring-blue-400 border-blue-400' : 'border-gray-100'}`}
                        onClick={() => setFilter('ALL')}
                    >
                        <p className="text-xs text-gray-500 font-medium">Aktivní přihlášky</p>
                        <p className="text-2xl font-bold text-blue-600">{stats.total_active}</p>
                    </div>
                    <div
                        className={`bg-white p-4 rounded-lg shadow-sm border cursor-pointer hover:shadow-md transition-shadow ${activeFilter === "STARTED" ? 'ring-2 ring-green-400 border-green-400' : 'border-gray-100'}`}
                        onClick={() => setFilter('STARTED')}
                    >
                        <p className="text-xs text-gray-500 font-medium">Probíhá (STARTED)</p>
                        <p className="text-2xl font-bold text-green-600">{stats.state_counts?.STARTED || 0}</p>
                    </div>
                    <div
                        className={`bg-white p-4 rounded-lg shadow-sm border cursor-pointer hover:shadow-md transition-shadow ${activeFilter === "AWAITING_DOCUMENTS" ? 'ring-2 ring-amber-400 border-amber-400' : 'border-gray-100'}`}
                        onClick={() => setFilter('AWAITING_DOCUMENTS')}
                    >
                        <p className="text-xs text-gray-500 font-medium">Čeká na dokumenty</p>
                        <p className="text-2xl font-bold text-amber-600">{stats.state_counts?.AWAITING_DOCUMENTS || 0}</p>
                    </div>
                    <div
                        className={`bg-white p-4 rounded-lg shadow-sm border cursor-pointer hover:shadow-md transition-shadow ${activeFilter === "CONTRACT_PENDING" ? 'ring-2 ring-orange-400 border-orange-400' : 'border-gray-100'}`}
                        onClick={() => setFilter('CONTRACT_PENDING')}
                    >
                        <p className="text-xs text-gray-500 font-medium">Čeká na zasmluvnění</p>
                        <p className="text-2xl font-bold text-orange-600">{stats.contract_pending_count || 0}</p>
                    </div>
                    <div
                        className={`bg-white p-4 rounded-lg shadow-sm border cursor-pointer hover:shadow-md transition-shadow ${activeFilter === "AT_RISK" ? 'ring-2 ring-red-400 border-red-400' : 'border-red-200 bg-red-50'}`}
                        onClick={() => setFilter('AT_RISK')}
                    >
                        <p className="text-xs text-red-600 font-medium">Rizikové praxe (At Risk)</p>
                        <p className="text-2xl font-bold text-red-600">{stats.at_risk_count}</p>
                    </div>
                </div>
            )}

            {/* At Risk Alert Panel */}
            {stats && stats.at_risk_items && stats.at_risk_items.length > 0 && (
                <section aria-labelledby="at-risk-heading" className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
                    <h3 id="at-risk-heading" className="text-sm font-bold text-red-900 mb-2">
                        <span aria-hidden="true">⚠ </span>{"Praxe vyžadující pozornost"}
                    </h3>
                    {stats.at_risk_count > stats.at_risk_items.length && (
                        <p className="text-xs text-gray-700 mb-3">
                            {`Zobrazeno ${stats.at_risk_items.length} z ${stats.at_risk_count}`}
                        </p>
                    )}
                    {/* Posuvná oblast musí být dostupná i z klávesnice. */}
                    {/* eslint-disable-next-line jsx-a11y/no-noninteractive-tabindex */}
                    <ul aria-label={"Praxe vyžadující pozornost"} tabIndex={0} className="space-y-2 max-h-64 overflow-y-auto rounded focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-600">
                        {stats.at_risk_items.map((item) => {
                            const style = Object.prototype.hasOwnProperty.call(riskStyles, item.risk_type)
                                ? riskStyles[item.risk_type] : neutralRiskStyle;
                            return (
                                <li key={item.student_practice_id} className="flex flex-col sm:flex-row sm:justify-between sm:items-center gap-2 bg-white p-3 rounded text-sm text-gray-900 border border-gray-200">
                                    <div className="min-w-0 break-words">
                                        <span className="font-semibold">{item.student_name}</span> — {item.practice_title} ({item.employer_name})
                                        <p className="text-xs text-gray-700 mt-1">{item.risk_reason}</p>
                                    </div>
                                    <span className={`self-start sm:self-center shrink-0 inline-flex items-center gap-1 px-2 py-1 border rounded text-xs font-semibold ${style.classes}`}>
                                        <span aria-hidden="true">{style === neutralRiskStyle ? 'ⓘ' : '⚠'}</span>
                                        {style.label}
                                    </span>
                                </li>
                            );
                        })}
                    </ul>
                </section>
            )}

            {/* Contract Pending Escalation Panel */}
            {escalatedPractices.length > 0 && (
                <div className="mb-6 bg-orange-50 border border-orange-200 rounded-lg p-4">
                    <h4 className="text-sm font-bold text-orange-800 mb-2">⏳ Praxe čekající na smlouvu déle než 7 dní:</h4>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                        {escalatedPractices.map((item) => (
                            <div key={item.student_practice_id} className="flex justify-between items-center bg-white p-2 rounded text-xs border border-orange-100">
                                <div>
                                    <span className="font-semibold">{item.student_full_name || "N/A"}</span> — {item.practice_title || item.title || "N/A"}
                                </div>
                                <span className="px-2 py-0.5 bg-orange-100 text-orange-700 rounded font-medium">
                                    {`Čeká na smlouvu — ${daysSinceCzechDate(item.updated_at)} dní`}
                                </span>
                            </div>
                        ))}
                    </div>
                    <p className="text-xs text-orange-700 mt-2">{"Tato praxe čeká na zasmluvnění déle než 7 dní. Doporučujeme urychleně kontaktovat studenta nebo zaměstnavatele."}</p>
                </div>
            )}

            {/* Filter Tabs */}
            <div className="flex flex-wrap gap-2 mb-6">
                {filterTabs.map((tab) => (
                    <button
                        key={tab.key}
                        onClick={() => setFilter(tab.key)}
                        className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                            activeFilter === tab.key
                                ? 'bg-blue-600 text-white shadow-md'
                                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                        }`}
                    >
                        {tab.label}
                    </button>
                ))}
            </div>

            {loading && (
                <Paragraph property="text-center text-gray-500 py-8">{"Načítání stáží..."}</Paragraph>
            )}

            {!loading && error && (
                <Paragraph property="text-center text-red-500 py-8">{error}</Paragraph>
            )}

            {!loading && !error && (
                <>
                    <Container property={"mb-8 space-y-4"}>
                        {filteredApproved.length === 0 ? (
                            <Paragraph property="text-center text-gray-500 py-8">
                                {activeFilter === "ALL"
                                    ? "Žádné schválené stáže."
                                    : "Žádné schválené stáže."}
                            </Paragraph>
                        ) : (
                            filteredApproved.map((entity) => (
                                <PraxeDepartmentEntity
                                    key={entity.student_practice_id || entity.practice_id}
                                    entity={entity}
                                    type="approved"
                                    onView={() => handleView("approved_practices", entity)}
                                    onClick={() => handleClick("approved_practices", entity)}
                                />
                            ))
                        )}
                    </Container>

                    <Container property={"flex items-center justify-between mb-6 mt-4"}>
                        <Headings sizeTag={"h3"} property={"mt-2"}>
                            {"Schvalovací kolečko"}
                        </Headings>
                    </Container>

                    <Container property={"mt-4 mb-8 space-y-4"}>
                        {toApprove.length === 0 ? (
                            <Paragraph property="text-center text-gray-500 py-8">
                                {"Žádné stáže čekající na schválení."}
                            </Paragraph>
                        ) : (
                            toApprove.map((entity) => (
                                <PraxeDepartmentEntity
                                    key={entity.practice_id}
                                    entity={entity}
                                    onView={() => handleView("to_approve_practices", entity)}
                                    onClick={() => handleClick("to_approve_practices", entity)}
                                    type="to_approve"
                                />
                            ))
                        )}
                    </Container>

                    {/* FE-004: schválené nabídky jsou po automatické aktivaci stále
                        viditelné a spravovatelné (SRS analysis.txt:2248) */}
                    <Container property={"flex items-center justify-between mb-6 mt-4"}>
                        <Headings sizeTag={"h3"} property={"mt-2"}>
                            {"Aktivní nabídky"}
                        </Headings>
                    </Container>

                    <Container property={"mt-4 mb-8 space-y-4"}>
                        {activeOffers.length === 0 ? (
                            <Paragraph property="text-center text-gray-500 py-8">
                                {"Žádné aktivní nabídky."}
                            </Paragraph>
                        ) : (
                            activeOffers.map((entity) => (
                                <PraxeDepartmentEntity
                                    key={entity.practice_id}
                                    entity={entity}
                                    onView={() => handleView("active_offers", entity)}
                                    type="active_offers"
                                />
                            ))
                        )}
                    </Container>
                </>
            )}
            {showPop &&
                <PopUpCon
                    onClose={handleClosePop}
                    onSubmit={handleApprove}
                    onSubmitText={"Schválit"}
                    onReject={handleReject}
                    onRejectText={"Zamítnout"}
                    title={"Opravdu chcete změnit stav nabídky?"}
                    text={`Chcete změnit stav nabídky: ${selectedEntity?.title || ""}?`}
                />
            }
        </>
    )
}
