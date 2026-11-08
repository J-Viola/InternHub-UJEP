import React, { useState, useEffect, useRef } from "react";
import Container from "@components/core/Container/Container";
import Headings from "@components/core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import ContainerForEntity from "@components/core/Container/ContainerForEntity";
import BackButton from "@components/core/Button/BackButton";
import PopUpCon from "@components/core/Container/PopUpCon";
import PrihlaskaEntity from "@components/Prihlasky/PrihlaskaEntity";
import { useStudentPracticeAPI } from "@api/student_practice/student_practiceAPI";
import { useNavigate } from "react-router-dom";
import { useUser } from "@hooks/UserProvider";
import SearchBar from "@components/Filter/SearchBar";
import DropDown from "@components/core/Form/DropDown";
import { useMessage } from "@hooks/MessageContext";
import { getApiErrorMessage } from "@utils/apiErrorUtils";
import EmptyState from "@core/Feedback/EmptyState";

export default function PrihlaskyPage() {
	const { addMessage } = useMessage();
 const [data, setData] = useState([])
 const [loadError, setLoadError] = useState(false);
 const requestSequence = useRef(0);
 const submittingRef = useRef(false);
	const [showPopup, setShowPopup] = useState(false);
	const [selectedEntity, setSelectedEntity] = useState(null);
	const [selectedCompanies, setSelectedCompanies] = useState([]);
	const [searchQuery, setSearchQuery] = useState("");
	const [companySelectValue, setCompanySelectValue] = useState("");
	const [rejectReason, setRejectReason] = useState("");
	const studentpracticeAPI = useStudentPracticeAPI();

	const navigate = useNavigate();
	const { user } = useUser();

	const handleOpenPopup = (en) => {
		setSelectedEntity(en);
		setShowPopup(true);
	}

	const handleClosePopup = () => {
		setShowPopup(false);
		setSelectedEntity(null);
		setRejectReason("");
	}

	const onProfile = (en) => {
		navigate(`/profil/${en.user_id}`)
	}

	const handleSubmit = async () => {
		if (submittingRef.current) return;
		submittingRef.current = true;
		try {
			// FE-002: žádný PATCH /status/ (neexistuje) — explicitní transition
			// s cílem podle aktuální fáze přihlášky.
			const res = await studentpracticeAPI.updateStudentPracticeStatus(
				selectedEntity.student_practice_id,
				"approve",
				{ workflowStatus: selectedEntity.workflow_status }
			);

			// Show detailed message based on backend response
			if (res && res.workflow_status && res.workflow_status !== "APPLIED") {
				addMessage("Přihláška byla plně schválena", "S");
			} else {
				addMessage("Přihláška byla částečně schválena", "S");
			}

			setShowPopup(false);
			setSelectedEntity(null);
			setRejectReason("");
			await fetchData();
		} catch (error) {
			console.error(error);
			addMessage(getApiErrorMessage(error, "Chyba při schvalování přihlášky"), "E");
		} finally {
			submittingRef.current = false;
		}
	}

	const handleReject = async () => {
		if (rejectReason.trim().length < 10) {
			addMessage(rejectReason.trim() ? "Důvod zamítnutí musí mít alespoň 10 znaků" : "Důvod zamítnutí je povinný", "E");
			return;
		}
		try {
			await studentpracticeAPI.updateStudentPracticeStatus(
				selectedEntity.student_practice_id,
				"reject",
				{ reason: rejectReason.trim(), workflowStatus: selectedEntity.workflow_status }
			);
			addMessage("Přihláška byla zamítnuta", "S");
			setShowPopup(false);
			setSelectedEntity(null);
			setRejectReason("");
			await fetchData();
		} catch (error) {
			console.error(error);
			addMessage(getApiErrorMessage(error, "Chyba při zamítnutí přihlášky"), "E");
		}
	}

	const fetchData = async () => {
		const sequence = ++requestSequence.current;
		setLoadError(false);
		try {
			let res = [];
			if (user.isAdmin()) {
				res = await studentpracticeAPI.getAdminPendingApplications();
			} else if (user.isDepartmentUser()) {
				res = await studentpracticeAPI.getProfessorApplications();
			} else if (user.isOrganizationUser()) {
				res = await studentpracticeAPI.getOrganizationApplications();
			}
			if (sequence === requestSequence.current) setData(res || []);
		} catch (error) {
			if (sequence !== requestSequence.current) return;
			console.error("Chyba při načítání přihlášek", error);
			setLoadError(true);
		}
	};

	useEffect(() => {
		fetchData();
	}, [user]);


	const toId = (name) => `firma-${(name || 'neznamy').toLowerCase()}`;

	const searchFiltered = searchQuery
		? (data || []).filter((n) => {
			const q = searchQuery.toLowerCase();
			return (
				n.student_full_name?.toLowerCase().includes(q) ||
				n.practice_title?.toLowerCase().includes(q) ||
				n.employer_name?.toLowerCase().includes(q) ||
				n.department_name?.toLowerCase().includes(q)
			);
		})
		: (data || []);

	const groupedByEmployer = (searchFiltered || []).reduce((acc, item) => {
		const name = item.employer_name || "Neznámá firma";
		(acc[name] = acc[name] || []).push(item);
		return acc;
	}, {});

	const allCompanyNames = Object.keys(groupedByEmployer);
	const displayCompanyNames = (user.isAdmin() || user.isDepartmentUser())
		? (selectedCompanies.length ? selectedCompanies.filter((n) => allCompanyNames.includes(n)) : allCompanyNames)
		: [];

	const onCompanySelect = (dict) => {
		const name = dict?.company;
		if (!name) return;
		if (!selectedCompanies.includes(name)) {
			setSelectedCompanies([...selectedCompanies, name]);
		}
		setCompanySelectValue("");
	};

	const removeCompanyFilter = (name) => {
		setSelectedCompanies(selectedCompanies.filter((c) => c !== name));
	};

	const availableOptions = allCompanyNames.filter((name) => !selectedCompanies.includes(name));

	return (
		<>
			<BackButton/>
			<Container property={"flex items-center justify-between mb-6 mt-4"}>
				<Headings sizeTag={"h3"} property={"mt-2"}>
					{"Nevyřízené přihlášky"}
				</Headings>
			</Container>

			{loadError ? (
				<Container role="alert"><Paragraph>{"Chyba při načítání přihlášek"}</Paragraph></Container>
			) : (user.isAdmin() || user.isDepartmentUser()) && (
				<Container property={"flex flex-col gap-3 mb-6 mt-4"}>
					<SearchBar
						id="search"
						value={searchQuery}
						placeholder={"Hledat podle studenta, katedry, firmy nebo názvu praxe..."}
						onChange={(e) => setSearchQuery(e.target.value)}
						onClear={() => setSearchQuery("")}
					/>
					<Container property="flex flex-wrap gap-2">
						<DropDown
							id="company"
							variant="facultyGreen"
							placeholder={"Vyberte organizaci pro filtrování"}
							value={companySelectValue}
							onChange={onCompanySelect}
							options={availableOptions.map((name) => ({ label: name, value: name }))}
						/>
					</Container>
					<Container property="flex flex-wrap gap-2">
						{selectedCompanies.map((name) => (
							<span
								key={name}
								className="bg-faculty-green text-white px-3 py-1 rounded-full text-sm flex items-center gap-2 cursor-pointer hover:bg-opacity-80 transition"
								onClick={() => removeCompanyFilter(name)}
							>
								{name} ×
							</span>
						))}
					</Container>
				</Container>
			)}

			<Container property={"mt-4 rounded-lg"}>
				{loadError ? null : !data ? (
					<Paragraph>{"Načítání..."}</Paragraph>
				) : (user.isAdmin() || user.isDepartmentUser()) ? (
					displayCompanyNames.length === 0 ? (
						<EmptyState
							title={"Žádné výsledky."}
							description={"Zkuste změnit vyhledávací dotaz."}
							icon="search"
						/>
					) : (
						<Container property={"space-y-6"}>
							{displayCompanyNames.map((companyName) => (
								<Container key={companyName} id={toId(companyName)}>
									<Headings sizeTag="h4" property="mb-3 border-b pb-2 text-faculty-green">
										{companyName}
									</Headings>
									<Container property="grid grid-cols-1 gap-4">
										{groupedByEmployer[companyName].map((entity) => (
											<PrihlaskaEntity
												key={entity.student_practice_id}
												entity={entity}
												onProfile={() => onProfile(entity)}
												onSettings={() => handleOpenPopup(entity)}
											/>
										))}
									</Container>
								</Container>
							))}
						</Container>
					)
				) : data.length === 0 ? (
					<EmptyState
						title={"Zatím nemáte žádné data k zobrazení."}
						description={"Všechny přihlášky byly vyřízeny."}
						icon="file-circle-check"
					/>
				) : (
					<Container property={"grid grid-cols-1 gap-4"}>
						{searchFiltered.length === 0 ? (
							<EmptyState
								title={"Žádné výsledky."}
								description={"Zkuste změnit vyhledávací dotaz."}
								icon="search"
							/>
						) : (
							searchFiltered.map((entity) => (
								<PrihlaskaEntity
									key={entity.student_practice_id}
									entity={entity}
									onProfile={() => onProfile(entity)}
									onSettings={() => handleOpenPopup(entity)}
								/>
							))
						)}
					</Container>
				)}
			</Container>

			{showPopup && selectedEntity && (
				<PopUpCon
					onClose={handleClosePopup}
					title={"Změnit stav přihlášky"}
					text={`Opravdu si přejete změnit stav přihlášky studenta ${selectedEntity.student_full_name}?`}
					onSubmit={handleSubmit}
					onReject={handleReject}
					variant="gray"
					onSubmitText={"Schválit"}
					onRejectText={"Zamítnout"}
				>
					<Container property="mt-4 mb-4 px-4">
						<Paragraph property="text-sm font-medium mb-2">
							{"Důvod zamítnutí"}
						</Paragraph>
						<textarea
							value={rejectReason}
							onChange={(e) => setRejectReason(e.target.value)}
							placeholder={"Minimálně 10 znaků..."}
							aria-label={"Důvod zamítnutí"}
							className="w-full p-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[80px] resize-none text-sm"
						/>
						{rejectReason.trim().length > 0 && rejectReason.trim().length < 10 && (
							<Paragraph property="text-red-500 text-xs mt-2">
								{"Důvod zamítnutí musí mít alespoň 10 znaků"}
							</Paragraph>
						)}
					</Container>
				</PopUpCon>
			)}
		</>
	);
}
