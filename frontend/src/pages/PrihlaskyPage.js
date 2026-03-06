import React, { useState, useEffect } from "react";
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
import { useTranslation } from "react-i18next";
import { useMessage } from "@hooks/MessageContext";

export default function PrihlaskyPage() {
	const { t } = useTranslation();
	const { addMessage } = useMessage();
	const [data, setData] = useState([])
	const [showPopup, setShowPopup] = useState(false);
	const [selectedEntity, setSelectedEntity] = useState(null);
	const [selectedCompanies, setSelectedCompanies] = useState([]);
	const [searchQuery, setSearchQuery] = useState("");
	const [companySelectValue, setCompanySelectValue] = useState("");
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
	}

	const onProfile = (en) => {
		navigate(`/profil/${en.user_id}`)
	}

	const handleSubmit = async () => {
		try {
			const res = await studentpracticeAPI.updateStudentPracticeStatus(selectedEntity.student_practice_id, "approve");

			// Show detailed message based on backend response
			if (res.school_approved && res.employer_approved) {
				addMessage(t('applications.approve_success_full'), "S");
			} else {
				addMessage(t('applications.approve_success_partial'), "S");
			}

			setShowPopup(false);
			setSelectedEntity(null);
			await fetchData();
		} catch (error) {
			console.error(error);
			addMessage(error.response?.data?.detail || t('applications.approve_error'), "E");
		}
	}

	const handleReject = async () => {
		try {
			await studentpracticeAPI.updateStudentPracticeStatus(selectedEntity.student_practice_id, "reject");
			addMessage(t('applications.reject_success'), "S");
			setShowPopup(false);
			setSelectedEntity(null);
			await fetchData();
		} catch (error) {
			console.error(error);
			addMessage(error.response?.data?.detail || t('applications.reject_error'), "E");
		}
	}

	const fetchData = async () => {
		try {
			let res = [];
			if (user.isAdmin()) {
				res = await studentpracticeAPI.getAdminPendingApplications();
			} else if (user.isDepartmentUser()) {
				res = await studentpracticeAPI.getProfessorApplications();
			} else if (user.isOrganizationUser()) {
				res = await studentpracticeAPI.getOrganizationApplications();
			}
			setData(res || []);
		} catch (error) {
			console.error(t('applications.load_error'), error);
			setData([]);
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
		const name = item.employer_name || t('users.unknown_company');
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
					{t('applications.title')}
				</Headings>
			</Container>

			{(user.isAdmin() || user.isDepartmentUser()) && (
				<Container property={"flex flex-col gap-3 mb-6 mt-4"}>
					<SearchBar
						id="search"
						value={searchQuery}
						placeholder={t('applications.search_placeholder')}
						onChange={(e) => setSearchQuery(e.target.value)}
						onClear={() => setSearchQuery("")}
					/>
					<Container property="flex flex-wrap gap-2">
						<DropDown
							id="company"
							variant="facultyGreen"
							placeholder={t('users.select_company')}
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
				{!data ? (
					<Paragraph>{t('common.loading')}</Paragraph>
				) : (user.isAdmin() || user.isDepartmentUser()) ? (
					displayCompanyNames.length === 0 ? (
						<Paragraph property="text-center text-gray-500 py-8">
							{t('users.no_results')}
						</Paragraph>
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
												onPopup={() => handleOpenPopup(entity)}
											/>
										))}
									</Container>
								</Container>
							))}
						</Container>
					)
				) : data.length === 0 ? (
					<Paragraph property="text-center text-gray-500 py-8">
						{t('applications.no_data')}
					</Paragraph>
				) : (
					<Container property={"grid grid-cols-1 gap-4"}>
						{searchFiltered.length === 0 ? (
							<Paragraph property="text-center text-gray-500 py-8">{t('users.no_results')}</Paragraph>
						) : (
							searchFiltered.map((entity) => (
								<PrihlaskaEntity
									key={entity.student_practice_id}
									entity={entity}
									onProfile={() => onProfile(entity)}
									onPopup={() => handleOpenPopup(entity)}
								/>
							))
						)}
					</Container>
				)}
			</Container>

			{showPopup && selectedEntity && (
				<PopUpCon
					onClose={handleClosePopup}
					title={t('applications.change_status_title')}
					text={t('applications.change_status_text', { name: selectedEntity.student_full_name })}
					onSubmit={handleSubmit}
					onReject={handleReject}
					variant="gray"
					submitText={t('common.approve')}
					rejectText={t('common.reject')}
				/>
			)}
		</>
	);
}
