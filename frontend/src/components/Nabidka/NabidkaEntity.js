import React, { useState, useEffect } from "react"
import Container from "@core/Container/Container"
import ContainerForEntity from "@core/Container/ContainerForEntity"
import Paragraph from "@components/core/Text/Paragraph"
import Headings from "@components/core/Text/Headings"
import { Image } from "@components/core/Image"
import { useNavigate } from "react-router-dom"
import Button from "@components/core/Button/Button"
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
            variant={user.isDepartmentUser() || user.isOrganizationUser() || user.isAdmin() ? handleVariant(entity.approval_status) : "gray"}
            onClick={handleClick}
            property="hover:shadow-lg transition-shadow duration-200"
        >
            <Container property="grid grid-cols-[auto,1fr] gap-4">
                {/* OBRÁZEK PRAXE */}
                <Container property="w-24 h-24 rounded-lg overflow-hidden">
                    <Image
                        src={entity.image_base64}
                        alt={entity.title}
                        className="w-full h-full"
                        objectFit="cover"
                        fallbackSrc="https://via.placeholder.com/96x96/3B82F6/FFFFFF?text=P"
                    />
                </Container>

                <Container property="grid grid-cols-1">
                    {/* TITULEK */}
                    <Container property="flex inline-block p-1 space-y-1 items-center">
                        <Headings sizeTag="h5-bold" property="text-black">
                            {entity.title}
                        </Headings>

                        {(user.isDepartmentMg() || user.isAdmin() || user.isOrganizationUser()) &&
                        (<Container property={"justify-end ml-auto"}>
                            <Button
                                variant={handleVariant(entity.approval_status, true)}
                                onClick={handleClick}
                                hover={false}
                            >
                                {approvalTag(entity.approval_status)}
                            </Button>
                        </Container>)
                        }

                        {user.isStudent() && (
                            <Container property={"justify-end ml-auto"}>
                                <Button
                                    icon={isFavorite ? "heart-filled" : "heart"}
                                    iconColor={isFavorite ? "text-red-500" : "text-gray-400"}
                                    onClick={handleHeartClick}
                                    noVariant={true}
                                    iconSize="20"
                                    hover={false}
                                />
                            </Container>
                        )}

                    </Container>

                    {/* ANOTACE */}
                    <Container property="p-1 space-y-1">
                        <Container property="space-y-1">
                            <Paragraph variant="base" property="text-gray-600 line-clamp-3">
                                {entity.description}
                            </Paragraph>
                        </Container>

                        {/* MÍSTO KONÁNÍ + TERMÍN */}
                        <Container property="flex flex-wrap justify-between items-center gap-2">
                            <Container property="bg-blue-400 px-2 p-1 rounded-lg">
                                <Paragraph variant="small" property="text-white">
                                    {entity.employer.address}
                                </Paragraph>
                            </Container>
                            {entity.start_date && entity.end_date && (
                                <Container property="bg-blue-100 px-2 p-1 rounded-lg">
                                    <Paragraph variant="small" property="text-blue-700">
                                        {entity.start_date} - {entity.end_date}
                                    </Paragraph>
                                </Container>
                            )}
                        </Container>
                    </Container>
                </Container>
            </Container>
        </ContainerForEntity>
    )
}
