import React, {useState, useEffect} from "react";
import Nav from "@core/Nav";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import PraxeEntity from "@components/Praxe/PraxeEntity";
import PopUpCon from "@core/Container/PopUpCon";
import Button from "@core/Button/Button";
import { useNabidkaAPI } from "src/api/nabidka/nabidkaAPI";
import { useNavigate } from "react-router-dom";
import { useStudentPracticeAPI } from "src/api/student_practice/student_pracitceAPI";
import { useUser } from "@hooks/UserProvider";
import BackButton from "@components/core/Button/BackButton";

export default function PraxePage() {

    const [ selectedEntity, setSelectedEntity ] = useState({});
    const nabidkaAPI  = useNabidkaAPI();
    const studentPraciceAPI = useStudentPracticeAPI();
    const [ data, setData]  = useState(null);
    const [ popUp, setPopUp ] = useState(false);
    const navigate = useNavigate();
    const { user } = useUser();


    useEffect(() => {
        const initFetch = async() => {
            if (user.isOrganizationUser()) {
                console.log("Jsem organizace")
                try {
                    const res = await nabidkaAPI.getOrganizationPractices();
                    setData(res);
                } catch (error) {
                    console.error("Chyba při načítání praxí organizace:", error);
                }
            }
            if (user.isStudent()) {
                const res = await nabidkaAPI.getPracticeUserRelations();
                setData(res);
            }
    
        }
        initFetch();
    }, [user])

    const handlePopUp = () => {
        setPopUp(false);
        setSelectedEntity({});
    }

    // hook na entitu podle typu
    const handleClick = (entity, type) => {
        console.log("clicked entity:", entity, "type:", type);
        
        if (type === "employer_invitations") {
            // Pro pozvánky - zobrazit popup pro přijetí/zamítnutí + načtu data
            setSelectedEntity({
                ...entity,
                type: "invitation",
                title: entity.practice_title,
                action: "respond_to_invitation"
            });
            setPopUp(true);
        } else if (type === "student_practices") {
            // tady handle

        } else if (type === "organization_practices") {
            // Pro organizace - zobrazit detail praxe
            navigate(`/upravit-nabidku/${entity.practice_id}`);
        }
    }

    const handleView = (entity, type) => {
        console.log("View entity:", entity, "type:", type);
        
        if (type === "employer_invitations") {
            navigate(`/nabidka/${entity.practice_id}`);
        } else if (type === "student_practices") {
            navigate(`/nabidka/${entity.practice_id}`);
        }
    }

    const handleInvivtaion = async (action) => {
        if (action) {
            const res = await studentPraciceAPI.manageEmployerInvitation(selectedEntity.invitation_id, action);
            handlePopUp();
        }
        
    }

    // Pop Up render
    const renderPopUp = () => {
        return (
            <PopUpCon 
                title={selectedEntity.title} 
                onClose={handlePopUp} 
                text={"Opravdu si přejete zahájit tuto praxi?"}
                onSubmit={() => handleInvivtaion("accept")}
                onReject={() => handleInvivtaion("reject")}
            />
        )
    }

    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                {user.isOrganizationUser() ? (
                    // Render pro organizaci
                    <>
                        <BackButton/>
                        <Container property={"flex items-center justify-between mb-6 mt-4"}>
                            <Headings sizeTag={"h3"} property={"mt-2"}>
                                Vytvořené stáže
                            </Headings>
                        </Container>

                        <Container>
                            <Button 
                                onClick={() => navigate('/vytvorit-nabidku')}
                                icon={"plus"}
                            >
                                Založit stáž
                            </Button>
                        </Container>

                        {/* Obsah */}
                        <Container property={"mt-4 rounded-lg"}>
                            {!data ? (
                                <Paragraph>Načítání...</Paragraph>
                            ) : data.length === 0 ? (
                                <Paragraph property="text-center text-gray-500 py-8">
                                    Zatím nemáte žádné vytvořené stáže.
                                </Paragraph>
                            ) : (
                                <Container property={"grid grid-cols-1 gap-4"}>
                                    {data?.map(entity => (
                                        <PraxeEntity
                                            type={"organization_practices"}
                                            key={`practice-${entity.practice_id}`}
                                            entity={entity}
                                            onClick={() => handleClick(entity, "organization_practices")}
                                            onView={() =>
                                                entity.approval_status !== 0
                                                    ? navigate(`/students/${entity.practice_id}`)
                                                    : navigate(`/nabidka/${entity.practice_id}`)
                                            }
                                        />
                                    ))}
                                </Container>
                            )}
                        </Container>
                    </>
                ) : (
                    // Render pro studenta - původní kód
                    <>  
                        <BackButton/>
                        <Container property={"flex flex-col gap-2"}>
                            {!data ? (
                                <Paragraph>Načítání...</Paragraph>
                            ) : (
                                <>
                                    <Headings sizeTag={"h3"} property={"mt-2 mb-2"}>Podané přihlášky 
                                        {data.student_practices ? (" " + `(${data.student_practices.length})`) : ""}
                                    </Headings>
                                    {/* Student Practices */}
                                    {data.student_practices?.map(entity => (
                                        <PraxeEntity
                                            type={"student_practices"}
                                            key={`practice-${entity.practice_title}-${entity.application_date}`}
                                            entity={entity}
                                            onClick={() => handleClick(entity, "student_practices")}
                                            onView={() => handleView(entity, "student_practices")}
                                        />
                                    ))}
                                    
                                    <Headings sizeTag={"h3"} property={"mt-2 mb-2"}>Pozvánky od firem
                                        {data.employer_invitations ? (" " + `(${data.employer_invitations.length})`) : ""}
                                    </Headings>
                                    {/* Employer Invitations */}
                                    {data.employer_invitations?.map(entity => (
                                        <PraxeEntity
                                            type={"employer_invitations"}
                                            key={`invitation-${entity.practice_title}-${entity.submission_date}`}
                                            entity={{
                                                ...entity,
                                                application_date: entity.submission_date,
                                                status: "Pozvánka" // Special status for invitations
                                            }}
                                            onClick={() => handleClick(entity, "employer_invitations")}
                                            onView={() => handleView(entity, "employer_invitations")}
                                        />
                                    ))}
                                </>
                            )}
                        </Container>
                    </>
                )}
            </Container>
            {popUp && renderPopUp()}
        </Container>
    )
}
