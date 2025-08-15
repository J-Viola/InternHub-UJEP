import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import Nav from "@components/core/Nav";
import { useParams, useNavigate } from "react-router-dom";
import PozvankyEntity from "@components/Pozvanky/PozvankyEntity";
import PopUpCon from "@core/Container/PopUpCon";
import { usePozvankyAPI } from "@api/pozvanky/pozvankyAPI";
import { useUser } from "@hooks/UserProvider";
import SearchBar from "@components/Filter/SearchBar";
import DropDown from "@components/core/Form/DropDown";

export default function PozvankyListPage() {
	const navigate = useNavigate();
	const { getPozvankyList, getPozvankyAdminList } = usePozvankyAPI();
	const [showPopup, setShowPopup] = useState(false);
	const [selectedEntity, setSelectedEntity] = useState(null);
	const [selectedCompanies, setSelectedCompanies] = useState([]);
	const [data, setData] = useState([]);
	const [loading, setLoading] = useState(true);
	const [searchQuery, setSearchQuery] = useState("");
	const [companySelectValue, setCompanySelectValue] = useState("");
	const { user } = useUser();


	const handleCancelInvitation = (entity) => {
		setSelectedEntity(entity);
		setShowPopup(true);
	}

	const handleConfirmCancel = async () => {
		if (!selectedEntity) return;
		try {
			// TODO: Implementovat API volání pro zrušení pozvánky
			console.log('Zrušit pozvánku:', selectedEntity);
			
			// Odebrat z listu
			setData(prevData => prevData.filter(item => item.id !== selectedEntity.id));
			
			setShowPopup(false);
			setSelectedEntity(null);
		} catch (error) {
			console.error('Chyba při zrušení pozvánky:', error);
		}
	}

	const handleClosePopup = () => {
		setShowPopup(false);
		setSelectedEntity(null);
	}

	const handleViewProfile = (userId) => {
		console.log('Zobrazit profil uživatele:', userId);
		navigate(`/profil/${userId}`);
	}

	useEffect(() => {
		const initFetch = async () => {
			try {
				setLoading(true);

				if (user.isAdmin()) {
					await getPozvankyAdminList().then((res) => setData(res));
				} else {
					await getPozvankyList().then((res) => setData(res));
				} 

			} catch (error) {
				console.error('Chyba při načítání pozvánek:', error);
			} finally {
				setLoading(false);
			}
		};

		initFetch();
	}, []);

	// group by pro admina
	const toId = (name) => `firma-${(name || 'neznamy').toLowerCase()}`;

	// vyhledávání
	const searchFiltered = searchQuery
		? (data || []).filter((n) => {
			const q = searchQuery.toLowerCase();
			return (
				(n.project_title || "").toLowerCase().includes(q) ||
				(n.recipient_name || "").toLowerCase().includes(q) ||
				(n.employer_name || "").toLowerCase().includes(q) ||
				(n.department || "").toLowerCase().includes(q)
			);
		})
		: (data || []);

	// seskupení podle firmy (po vyhledávání)
	const groupedByEmployer = (searchFiltered || []).reduce((acc, item) => {
		const name = item.employer_name || "Neznámá firma";
		(acc[name] = acc[name] || []).push(item);
		return acc;
	}, {});

	// unikátní názvy firem dle vyhledávání
	const allCompanyNames = Object.keys(groupedByEmployer);
	// zobrazené firmy: pokud nejsou vybrané, zobrazím všechny
	const displayCompanyNames = user.isAdmin()
		? (selectedCompanies.length ? selectedCompanies.filter((n) => allCompanyNames.includes(n)) : allCompanyNames)
		: [];

	// přidání/odebrání filtrů
	const onCompanySelect = (dict) => {
		const name = dict?.company;
		if (!name) return;
		if (!selectedCompanies.includes(name)) setSelectedCompanies([...selectedCompanies, name]);
		setCompanySelectValue("");
	};
	const onRemoveCompany = (name) => setSelectedCompanies(selectedCompanies.filter((n) => n !== name));
	const availableOptions = allCompanyNames.filter((n) => !selectedCompanies.includes(n));

	// data zobrazená v seznamu (pokud je admin a má vybraný filtr, omezíme data) po vyhledávání
	const filteredData = (user.isAdmin() && selectedCompanies.length > 0)
		? searchFiltered.filter((n) => selectedCompanies.includes(n.employer_name))
		: searchFiltered;

	return(
		<Container property="min-h-screen">
			<Nav/>
			<Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
				<BackButton/>
				<Container property={"flex items-center justify-between mb-6 mt-4"}>
					<Headings sizeTag={"h3"} property={"mt-2"}>
						Zaslané pozvánky
					</Headings>
				</Container>
				<Paragraph property={"text-red-500"}>Tato stránka obsahuje pouze dummy data.</Paragraph>

				{/*Filtrace */}
				{user.isAdmin() && (
				<Container property={"flex flex-col gap-3 mb-6 mt-4"}>
					<SearchBar
						id="search"
						value={searchQuery}
						placeholder="Hledat podle projektu, jména, firmy nebo katedry..."
						onChange={(e) => setSearchQuery(e.target.value)}
						onClear={() => setSearchQuery("")}
					/>
					<Container property={"flex items-center gap-3"}>
						<DropDown
							id="company"
							variant="facultyGreen"
							placeholder="Vyberte organizaci pro filtrování"
							value={companySelectValue}
							onChange={onCompanySelect}
							options={availableOptions.map((name) => ({ label: name, value: name }))}
						/>
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
					{loading ? (
						<Paragraph>Načítání...</Paragraph>
					) : data.length === 0 ? (
						<Paragraph property="text-center text-gray-500 py-8">
							Zatím nemáte žádné zaslané pozvánky.
						</Paragraph>
					) : (
						user.isAdmin() ? (
							displayCompanyNames.length === 0 ? (
								<Paragraph property="text-center text-gray-500 py-8">
									Žádné výsledky.
								</Paragraph>
							) : (
								<Container property={"space-y-6"}>
									{displayCompanyNames.map((name) => (
										<Container id={toId(name)} key={name}>
											<Headings sizeTag={"h4"}>{`Firma: ${name}`}</Headings>
											<Container property={"flex flex-wrap gap-4 mt-2"}>
												{(groupedByEmployer[name] || []).map((entity) => (
													<PozvankyEntity
														key={entity.id}
														entity={entity}
														onCancel={handleCancelInvitation}
														onView={handleViewProfile}
													/>
												))}
											</Container>
										</Container>
									))}
								</Container>
							)
						) : (
							<Container property={"grid grid-cols-1 gap-4"}>
								{filteredData.map((entity) => (
									<PozvankyEntity
										key={entity.id}
										entity={entity}
										onCancel={handleCancelInvitation}
										onView={handleViewProfile}
									/>
								))}
							</Container>
						)
					)}
				</Container>
			</Container>

			{/* Popup pro potvrzení zrušení pozvánky */}
			{showPopup && (
				<PopUpCon
					title="Potvrzení zrušení pozvánky"
					text={`Opravdu chcete zrušit pozvánku pro ${selectedEntity?.recipient_name} na projekt "${selectedEntity?.project_title}"?`}
					onSubmit={handleConfirmCancel}
					onReject={handleClosePopup}
					onClose={handleClosePopup}
					onSubmitText="Ano"
					onRejectText="Ne"
				/>
			)}
		</Container>
	)
}
