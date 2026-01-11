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

export default function NabidkaEntity({ entity }) {
    const navigate = useNavigate();
    const { user, setUser } = useUser();
    const { toggleFavorite } = useNabidkaAPI();
    const [isFavorite, setIsFavorite] = useState(false);

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
                return "Čeká ke schválení";
            case 1: // APPROVED
                return "Probíhající stáž";
            case 2: // REJECTED
                return "Zrušená stáž";
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
            <Container property="grid grid-cols-[150px,1fr] gap-6">
                {/* OBRÁZEK PRAXE */}
                <Container property="w-full h-32 rounded-lg overflow-hidden bg-gray-100 flex items-center justify-center">
                    <Image
                        src={entity.image_base64}
                        alt={entity.title}
                        className="w-full h-full"
                        objectFit="cover"
                        fallbackSrc="https://via.placeholder.com/150x150/3B82F6/FFFFFF?text=P"
                    />
                </Container>

                <Container property="grid grid-cols-1 content-between">
                    {/* HLAVIČKA */}
                    <Container>
                        <Container property="flex items-start justify-between">
                            <Headings sizeTag="h4-bold" property="text-black mb-1">
                                {entity.title}
                            </Headings>
                            
                            {/* Akční tlačítka / Statusy */}
                            <Container property="flex gap-2 items-center">
                                {(user.isDepartmentMg() || user.isAdmin() || user.isOrganizationUser()) && (
                                    <Button
                                        variant={handleVariant(entity.approval_status, true)}
                                        onClick={handleClick}
                                        hover={false}
                                        property="text-xs px-2 py-1"
                                    >
                                        {approvalTag(entity.approval_status)}
                                    </Button>
                                )}

                                {user.isStudent() && (
                                    <Button
                                        icon={isFavorite ? "heart-filled" : "heart"}
                                        iconColor={isFavorite ? "text-red-500" : "text-gray-400"}
                                        onClick={handleHeartClick}
                                        noVariant={true}
                                        iconSize="24"
                                        hover={false}
                                    />
                                )}
                            </Container>
                        </Container>
                        
                        {/* Tagy */}
                        <Container property="flex flex-wrap gap-2 mb-2">
                             {entity.subject && (
                                <span className="bg-purple-100 text-purple-800 text-xs font-semibold px-2.5 py-0.5 rounded">
                                    {entity.subject.subject_code || "Předmět"}
                                </span>
                            )}
                            {entity.contract_type && (
                                <span className="bg-gray-100 text-gray-800 text-xs font-semibold px-2.5 py-0.5 rounded border border-gray-500">
                                    {entity.contract_type}
                                </span>
                            )}
                        </Container>

                        {/* ANOTACE */}
                        <Paragraph variant="base" property="text-gray-600 line-clamp-2 mb-2">
                            {entity.description}
                        </Paragraph>
                    </Container>
                    
                    {/* SPODNÍ LIŠTA */}
                    <Container property="flex flex-wrap justify-between items-end gap-2 mt-2">
                         <Container property="flex gap-2">
                            <Container property="bg-blue-50 px-3 py-1 rounded-md flex items-center gap-1 border border-blue-100">
                                <span className="text-blue-500 text-sm">📍</span>
                                <Paragraph variant="small" property="text-blue-700 font-medium">
                                    {entity.employer.address}
                                </Paragraph>
                            </Container>
                            {entity.start_date && entity.end_date && (
                                <Container property="bg-green-50 px-3 py-1 rounded-md flex items-center gap-1 border border-green-100">
                                    <span className="text-green-500 text-sm">📅</span>
                                    <Paragraph variant="small" property="text-green-700 font-medium">
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