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
import { useTranslation } from "react-i18next";
import { useApi } from "@hooks/useApi";
import { daysSinceCzechDate, isOlderThan } from "@utils/dateUtils";

export default function SpravaStaziPage() {
    const { t } = useTranslation();
    const [searchParams, setSearchParams] = useSearchParams();
    const [approved, setApproved] = useState([]);
    const [toApprove, setToApprove] = useState([]);
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

            try {
                const statsRes = await api.get('/dashboard/stats/');
                setStats(statsRes.data);
            } catch (sErr) {
                console.error("Chyba při načítání statistik dashboardu:", sErr);
            }
        } catch {
            setError(t('internships.error'));
            setApproved([]);
            setToApprove([]);
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async (format) => {
        try {
            const response = await api.get(`/export-data/?format=${format}`, {
                responseType: 'blob',
            });

            // HTTP 202 → async export se zpracovává.
            // Nestahujeme blob, jen informujeme; download přijde notifikací EXPORT_READY.
            if (response.status === 202) {
                addMessage(t('export.processing'), 'I');
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
                        addMessage(t('export.processing'), 'I');
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
            addMessage(t('export.success', { format: format.toUpperCase() }), 'S');
        } catch (err) {
            const msg = err?.response?.data?.error || t('common.error');
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
            const errorCode = error.code || "UNKNOWN_ERROR";
            addMessage(t(`api_errors.${errorCode}`, { defaultValue: t('common.error') }), "E");
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
            const errorCode = error.code || "UNKNOWN_ERROR";
            addMessage(t(`api_errors.${errorCode}`, { defaultValue: t('common.error') }), "E");
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
    }, []);

    const handleView = (type, entity) => {
        if (type === "approved_practices") {
            navigate(`/karta-praxe/${entity.student_practice_id}`)
        }
        if (type === "to_approve_practices") {
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

    // Filter approved practices based on URL state param
    const filteredApproved = useMemo(() => {
        if (activeFilter === "ALL") return approved;
        if (activeFilter === "AT_RISK") {
            // AT_RISK is computed from stats, but we don't have individual risk flags
            // on each entity in the list. For now, show all and let the KPI card
            // handle the at-risk panel.
            return approved;
        }
        if (activeFilter === "CONTRACT_PENDING") {
            return approved.filter(
                (e) => e.workflow_state === "PRELIMINARY_APPROVED" && !e.contract_received_date
            );
        }
        return approved.filter((e) => e.workflow_state === activeFilter);
    }, [approved, activeFilter]);

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
        { key: "ALL", label: t('internships.filter_all') },
        { key: "STARTED", label: t('internships.filter_started') },
        { key: "AWAITING_DOCUMENTS", label: t('internships.filter_awaiting_documents') },
        { key: "CONTRACT_PENDING", label: t('internships.filter_contract_pending') },
        { key: "AT_RISK", label: t('internships.filter_at_risk') },
    ];

    return(
        <>
            <BackButton/>

            {/* Dashboard Stats & Export Toolbar */}
            <Container property={"flex flex-col md:flex-row items-center justify-between mb-6 mt-4 gap-4"}>
                <Headings sizeTag={"h2"} property={"text-2xl font-bold"}>
                    {t('internships.ongoing_title')}
                </Headings>

                {/* Export Buttons */}
                <div className="flex space-x-2">
                    <button
                        onClick={() => handleExport('xlsx')}
                        className="bg-green-600 hover:bg-green-700 text-white text-xs px-3 py-2 rounded-md font-medium transition-colors"
                    >
                        Export XLSX
                    </button>
                    <button
                        onClick={() => handleExport('csv')}
                        className="bg-blue-600 hover:bg-blue-700 text-white text-xs px-3 py-2 rounded-md font-medium transition-colors"
                    >
                        Export CSV
                    </button>
                </div>
            </Container>

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
                <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4">
                    <h4 className="text-sm font-bold text-red-800 mb-2">⚠ Praxe vyžadující pozornost (Po termínu / Chybějící dokumenty):</h4>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                        {stats.at_risk_items.map((item) => (
                            <div key={item.student_practice_id} className="flex justify-between items-center bg-white p-2 rounded text-xs border border-red-100">
                                <div>
                                    <span className="font-semibold">{item.student_name}</span> — {item.practice_title} ({item.employer_name})
                                </div>
                                <span className="px-2 py-0.5 bg-red-100 text-red-700 rounded font-medium">{item.risk_reason}</span>
                            </div>
                        ))}
                    </div>
                </div>
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
                                    {t('internships.contract_pending_badge', { days: daysSinceCzechDate(item.updated_at) })}
                                </span>
                            </div>
                        ))}
                    </div>
                    <p className="text-xs text-orange-700 mt-2">{t('internships.contract_pending_escalation')}</p>
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
                <Paragraph property="text-center text-gray-500 py-8">{t('internships.loading')}</Paragraph>
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
                                    ? t('internships.no_approved')
                                    : t('internships.no_approved')}
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
                            {t('internships.approval_wheel')}
                        </Headings>
                    </Container>

                    <Container property={"mt-4 mb-8 space-y-4"}>
                        {toApprove.length === 0 ? (
                            <Paragraph property="text-center text-gray-500 py-8">
                                {t('internships.no_to_approve')}
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
                </>
            )}
            {showPop &&
                <PopUpCon
                    onClose={handleClosePop}
                    onSubmit={handleApprove}
                    onSubmitText={t('common.approve')}
                    onReject={handleReject}
                    onRejectText={t('common.reject')}
                    title={t('internships.change_status_confirm')}
                    text={t('internships.change_status_text', { title: selectedEntity?.title || "" })}
                />
            }
        </>
    )
}
