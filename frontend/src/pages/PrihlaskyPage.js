import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import Nav from "@components/core/Nav";
import { useParams } from "react-router-dom";
import { useStudentPracticeAPI } from "@api/student_practice/student_pracitceAPI";
import PrihlaskaEntity from "@components/Prihlasky/PrihlaskaEntity";
import PopUpCon from "@core/Container/PopUpCon";
import { useNavigate } from "react-router-dom";
import { useUser } from "@hooks/UserProvider";

export default function PrihlaskyPage() {
	const [data, setData] = useState([])
	const [showPopup, setShowPopup] = useState(false);
	const [selectedEntity, setSelectedEntity] = useState(null);
	const [selectedCompanies, setSelectedCompanies] = useState([]);
	const studentpracticeAPI = useStudentPracticeAPI();
	const navigate = useNavigate();
	const { user } = useUser();

	const onSettings = (en) => {
		setSelectedEntity(en);
		setShowPopup(true);
	}

	const onProfile = (en) => {
		console.log("Profil", en)
		navigate(`/profil/${en.user_id}`)
	}

	const handleClosePopup = () => {
		setShowPopup(false);
		setSelectedEntity(null);
	}

	const handleSubmit = async () => {
		if (!selectedEntity) return;
		try {
			await studentpracticeAPI.updateStudentPracticeStatus(selectedEntity.student_practice_id, "approve");
			setShowPopup(false);
			setSelectedEntity(null);
			// Refresh data
			const res = await studentpracticeAPI.getOrganizationApplications();
			setData(res);
		} catch (error) {
			// případně zobrazit error toast
		}
	}

	
	const handleReject = async () => {
		if (!selectedEntity) return;
		try {
			await studentpracticeAPI.updateStudentPracticeStatus(selectedEntity.student_practice_id, "reject");
			setShowPopup(false);
			setSelectedEntity(null);
			// Refresh data
			const res = await studentpracticeAPI.getOrganizationApplications();
			setData(res);
		} catch (error) {
			// případně zobrazit error toast
		}
	}

	// TO:DO - admin nemá vázanou organizaci na účtu, proto je nutné vytvořit separátní endpoint pro admina!
	useEffect(() => {
		const fetchData = async () => {
			if (user.isAdmin()) {
				const res = await studentpracticeAPI.getAdminPendingApplications();
				setData(res);
				console.log("Admin pending applications", res);
			}
			else {    
				try {
					const res = await studentpracticeAPI.getOrganizationApplications();
					setData(res);
				} catch (error) {
					setData([]);
				}
			}

		};
		fetchData();
	}, []);


	const toId = (name) => `firma-${(name || 'neznamy').toLowerCase().replace(/[^a-z0-9]+/g, '-')}`;

	// seskupení podle firmy
	const groupedByEmployer = (data || []).reduce((acc, item) => {
		const name = item.employer_name || "Neznámá firma";
		(acc[name] = acc[name] || []).push(item);
		return acc;
	}, {});

	// unikátní názvy firem
	const allCompanyNames = Object.keys(groupedByEmployer);
	// zobrazené firmy: pokud nejsou vybrané, zobrazíme všechny
	const displayCompanyNames = user.isAdmin()
		? (selectedCompanies.length ? selectedCompanies.filter((n) => allCompanyNames.includes(n)) : allCompanyNames)
		: [];

	// přidání/odebrání filtrů
	const onAddCompany = (e) => {
		const name = e.target.value;
		if (!name) return;
		if (!selectedCompanies.includes(name)) setSelectedCompanies([...selectedCompanies, name]);
		// resetnout select zpět na placeholder
		e.target.value = "";
	};
	const onRemoveCompany = (name) => setSelectedCompanies(selectedCompanies.filter((n) => n !== name));
	const availableOptions = allCompanyNames.filter((n) => !selectedCompanies.includes(n));

	return(
	<Container property="min-h-screen">
		<Nav/>
		<Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
			<BackButton/>
			<Container property={"flex items-center justify-between mb-6 mt-4"}>
				<Headings sizeTag={"h3"} property={"mt-2"}>
					Nevyřízené přihlášky
				</Headings>
			</Container>

			{user.isAdmin() && (
				<Container property={"flex flex-col gap-3 mb-6 mt-4"}>
					<Container property={"flex items-center gap-3"}>
						<select className={"py-1 px-2 text-black bg-facultyColLight rounded-lg border border-black"} defaultValue="" onChange={onAddCompany}>
							<option value="">Vyberte organizaci pro filtrování</option>
							{availableOptions.map((name) => (
								<option key={name} value={name}>{name}</option>
							))}
						</select>
						<Container property={"flex items-center flex-wrap gap-2"}>
							{selectedCompanies.map((name) => (
								<Button key={name} icon={"cross"} iconColor="text-black" variant="secondary" onClick={() => onRemoveCompany(name)}>
									{name}
								</Button>
							))}
						</Container>
					</Container>
				</Container>
			)}

			<Container property={"mt-4 rounded-lg"}>
				{!data ? (
					<Paragraph>Načítání...</Paragraph>
				) : user.isAdmin() ? (
					displayCompanyNames.length === 0 ? (
						<Paragraph property="text-center text-gray-500 py-8">
							Zatím nemáte žádné data k zobrazení.
						</Paragraph>
					) : (
						<Container property={"space-y-6"}>
							{displayCompanyNames.map((name) => (
								<Container id={toId(name)} key={name}>
									<Headings sizeTag={"h4"}>{name}</Headings>
									<Container property={"flex flex-wrap gap-4 mt-2"}>
										{groupedByEmployer[name].map((entity) => (
											<PrihlaskaEntity
												onClick={onProfile}
												key={entity.student_practice_id}
												entity={entity}
												onSettings={onSettings}
												onProfile={onProfile}
											/>
										))}
									</Container>
								</Container>
							))}
						</Container>
					)
				) : data.length === 0 ? (
					<Paragraph property="text-center text-gray-500 py-8">
						Zatím nemáte žádné data k zobrazení.
					</Paragraph>
				) : (
					<Container property={"grid grid-cols-1 gap-4"}>
						{data.map((entity) => (
							<PrihlaskaEntity
								onClick={onProfile}
								key={entity.student_practice_id}
								entity={entity}
								onSettings={onSettings}
								onProfile={onProfile}
							/>
						))}
					</Container>
				)}
			</Container>
		</Container>
		{showPopup && selectedEntity && (
			<PopUpCon
				onClose={handleClosePopup}
				title={"Změnit stav přihlášky"}
				text={`Opravdu si přejete změnit stav přihlášky studenta ${selectedEntity.student_full_name}?`}
				onSubmit={handleSubmit}
				onReject={handleReject}
				variant="gray"
			/>
		)}
	</Container>
	)
}