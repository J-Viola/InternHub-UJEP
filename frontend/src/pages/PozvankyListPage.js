import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import { useNavigate } from "react-router-dom";
import PozvankyEntity from "@components/Pozvanky/PozvankyEntity";
import PopUpCon from "@core/Container/PopUpCon";
import { usePozvankyAPI } from "@api/pozvanky/pozvankyAPI";
import { useUser } from "@hooks/UserProvider";
import SearchBar from "@components/Filter/SearchBar";
import DropDown from "@components/core/Form/DropDown";
import { useTranslation } from "react-i18next";

export default function PozvankyListPage() {
	const navigate = useNavigate();
	const { t } = useTranslation();
	const { getPozvankyList, getPozvankyAdminList, deleteInvitation } = usePozvankyAPI();
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
            await deleteInvitation(selectedEntity.id);
			setData(prevData => prevData.filter(item => item.id !== selectedEntity.id));
			setShowPopup(false);
			setSelectedEntity(null);
		} catch (error) {
			console.error(t('invitations.cancel_error'), error);
		}
	}

	const handleClosePopup = () => {
		setShowPopup(false);
		setSelectedEntity(null);
	}

	const handleViewProfile = (userId) => {
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
				console.error(t('invitations.load_error'), error);
			} finally {
				setLoading(false);
			}
		};

		initFetch();
	}, [user, getPozvankyAdminList, getPozvankyList, t]);

	const toId = (name) => `firma-${(name || 'neznamy').toLowerCase()}`;

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

	const groupedByEmployer = (searchFiltered || []).reduce((acc, item) => {
		const name = item.employer_name || t('users.unknown_company');
		(acc[name] = acc[name] || []).push(item);
		return acc;
	}, {});

	const allCompanyNames = Object.keys(groupedByEmployer);
	const displayCompanyNames = user.isAdmin()
		? (selectedCompanies.length ? selectedCompanies.filter((n) => allCompanyNames.includes(n)) : allCompanyNames)
		: [];

	const onCompanySelect = (dict) => {
		const name = dict?.company;
		if (!name) return;
		if (!selectedCompanies.includes(name)) setSelectedCompanies([...selectedCompanies, name]);
		setCompanySelectValue("");
	};
	const onRemoveCompany = (name) => setSelectedCompanies(selectedCompanies.filter((n) => n !== name));
	const availableOptions = allCompanyNames.filter((n) => !selectedCompanies.includes(n));

	const filteredData = (user.isAdmin() && selectedCompanies.length > 0)
		? searchFiltered.filter((n) => selectedCompanies.includes(n.employer_name))
		: searchFiltered;

	    return(
	        <>
	            <BackButton/>
	            <Container property={"flex items-center justify-between mb-6 mt-4"}>
	                <Headings sizeTag={"h3"} property={"mt-2"}>
	                    {t('invitations.sent_title')}
	                </Headings>
	            </Container>

	            {/*Filtrace */}
	            {user.isAdmin() && (
	            <Container property={"flex flex-col gap-3 mb-6 mt-4"}>
	                <SearchBar
	                    id="search"
	                    value={searchQuery}
	                    placeholder={t('invitations.search_placeholder')}
	                    onChange={(e) => setSearchQuery(e.target.value)}
	                    onClear={() => setSearchQuery("")}
	                />
	                <Container property={"flex items-center gap-3"}>
	                    <DropDown
	                        id="company"
	                        variant="facultyGreen"
	                        placeholder={t('users.select_company')}
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
	                    <Paragraph>{t('common.loading')}</Paragraph>
	                ) : data.length === 0 ? (
	                    <Paragraph property="text-center text-gray-500 py-8">
	                        {t('invitations.no_invitations')}
	                    </Paragraph>
	                ) : (
	                    user.isAdmin() ? (
	                        displayCompanyNames.length === 0 ? (
	                            <Paragraph property="text-center text-gray-500 py-8">
	                                {t('users.no_results')}
	                            </Paragraph>
	                        ) : (
	                            <Container property={"space-y-6"}>
	                                {displayCompanyNames.map((name) => (
	                                    <Container id={toId(name)} key={name}>
	                                        <Headings sizeTag={"h4"}>{`${t('invitations.company_label')}: ${name}`}</Headings>
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

	            {/* Popup pro potvrzení zrušení pozvánky */}
	            {showPopup && (
	                <PopUpCon
	                    title={t('invitations.cancel_confirm_title')}
	                    text={t('invitations.cancel_confirm_text', { name: selectedEntity?.recipient_name, project: selectedEntity?.project_title })}
	                    onSubmit={handleConfirmCancel}
	                    onReject={handleClosePopup}
	                    onClose={handleClosePopup}
	                    onSubmitText={t('common.yes')}
	                    onRejectText={t('common.no')}
	                />
	            )}
	        </>
	    )
	}
