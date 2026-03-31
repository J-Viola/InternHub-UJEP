import React, { useState, useEffect } from "react"
import Container from "@core/Container/Container"
import ContainerForEntity from "@core/Container/ContainerForEntity"
import Paragraph from "@components/core/Text/Paragraph"
import Headings from "@components/core/Text/Headings"
import { Image } from "@components/core/Image"
import { useNavigate } from "react-router-dom"
import Button from "@components/core/Button/Button"
import Icon from "@components/core/Icon/Icon"
import { useUser } from "@hooks/UserProvider"
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI"
import { useTranslation } from "react-i18next"

export default function NabidkaEntity({ entity }) {
    const navigate = useNavigate();
    const { user, setUser } = useUser();
    const { toggleFavorite } = useNabidkaAPI();
    const [isFavorite, setIsFavorite] = useState(false);
    const { t } = useTranslation();

    useEffect(() => {
        if (user && user.favorite_practices && user.favorite_practices.includes(entity.practice_id)) {
            setIsFavorite(true);
        } else {
            setIsFavorite(false);
        }
    }, [user, entity.practice_id]);

    const handleHeartClick = async (e) => {
        e.stopPropagation();
        try {
            const result = await toggleFavorite(entity.practice_id);
            setIsFavorite(result.is_favorite);

             // Update global user state manually
            let newFavorites = [...(user.favorite_practices || [])];
            if (result.is_favorite) {
                if (!newFavorites.includes(entity.practice_id)) newFavorites.push(entity.practice_id);
            } else {
                newFavorites = newFavorites.filter(id => id !== entity.practice_id);
            }

            // Reconstruct user object to ensure UserObj class can re-hydrate
            const userData = {
                role: user.role,
                id: user.id,
                username: user.username,
                email: user.email,
                first_name: user.firstName,
                last_name: user.lastName,
                department: user.department,
                favorite_practices: newFavorites
            };
            setUser(userData);

        } catch (error) {
            console.error(error);
        }
    }

    const handleVariant = (approval_status, buttonType=false) => {
        switch (approval_status) {
            case 0: // PENDING
                return buttonType ? "yellowSmall" : "yellow";
            case 1: // APPROVED
                return buttonType ? "green" : "green";
            case 2: // REJECTED
                return buttonType ? "redSmall" : "red";
            default:
                return buttonType ? "gray" : "gray";
        }
    }

    const approvalTag = (approval_status) => {
        switch (approval_status) {
            case 0: // PENDING
                return t('status.PENDING');
            case 1: // APPROVED
                return t('status.APPROVED');
            case 2: // REJECTED
                return t('status.REJECTED');
            default:
                return;
        }
    }

    const handleClick = () => {
        navigate(`/nabidka/${entity.practice_id}`);
    }

    return(
        <ContainerForEntity
            id={entity.practice_id}
            variant="white"
            onClick={handleClick}
            property="p-6 mt-4 border border-black rounded-[10px] shadow-md hover:shadow-lg transition-all duration-200 relative"
        >
            <Container property="flex flex-row gap-8 items-start w-full">

                {/* LOGO */}
                <Container property="w-32 h-32 shrink-0 flex items-center justify-center">
                    <Image
                        src={entity.image_base64}
                        alt={entity.title}
                        className="w-full h-full"
                        objectFit="contain"
                    />
                </Container>

                {/* CONTENT BLOCK */}
                <Container property="flex flex-col gap-2 flex-grow min-w-0">

                    {/* TITLE */}
                    <Container property="flex justify-between items-start">
                        <Headings sizeTag="h4" property="text-black font-bold leading-tight">
                            {entity.title}
                        </Headings>

                        {/* ACTIONS (Heart / Status) */}
                        <Container property="flex gap-4 items-center shrink-0 ml-4">
                             {(user.isDepartmentMg() || user.isAdmin() || user.isOrganizationUser()) &&
                                <Button
                                    variant={handleVariant(entity.approval_status, true)}
                                    onClick={handleClick}
                                    hover={false}
                                    property="px-3 py-1 text-[10px] font-black uppercase tracking-widest border-black"
                                >
                                    {approvalTag(entity.approval_status)}
                                </Button>
                            }

                            {user.isStudent() && (
                                <Button
                                    icon={isFavorite ? "heart-filled" : "heart"}
                                    iconColor={isFavorite ? "text-red-500" : "text-gray-400"}
                                    onClick={handleHeartClick}
                                    noVariant={true}
                                    iconSize="28"
                                    hover={false}
                                />
                            )}
                        </Container>
                    </Container>

                    {/* DESCRIPTION */}
                    <Paragraph property="text-black text-base leading-relaxed mb-4 line-clamp-3">
                        {entity.description}
                    </Paragraph>

                    {/* TAGS ROW */}
                    <Container property="flex flex-wrap gap-3 mt-auto items-center">
                        {/* MÍSTO */}
                        <Container property="bg-[#93c5fd] text-white px-5 py-1.5 rounded-full font-medium text-sm shadow-sm whitespace-nowrap flex items-center gap-2">
                            <Icon name="location-dot" size={14} color="text-white" />
                            {t('offers.location')}: {entity.employer.address}
                        </Container>

                        {/* SKILLS */}
                        {entity.skills && Array.isArray(entity.skills) && entity.skills.map((skill, index) => (
                            <Container
                                key={index}
                                property="bg-[#93c5fd] text-white px-5 py-1.5 rounded-full font-medium text-sm shadow-sm whitespace-nowrap"
                            >
                                #{skill}
                            </Container>
                        ))}

                        {/* TERMÍN (Datum - Datum) */}
                        <Container property="flex items-center gap-4 ml-auto">
                            <Container property="bg-[#93c5fd] text-white px-5 py-1.5 rounded-full font-medium text-sm shadow-sm whitespace-nowrap flex items-center gap-2">
                                <Icon name="calendar" size={14} color="text-white" />
                                {entity.start_date} - {entity.end_date}
                            </Container>
                            <Button
                                variant="primary"
                                property="px-6 py-2 text-sm font-bold uppercase"
                                onClick={handleClick}
                            >
                                {t('common.view_detail')}
                            </Button>
                        </Container>
                    </Container>

                </Container>
            </Container>
        </ContainerForEntity>
    )
}
