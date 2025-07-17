import React, {useState, useEffect} from "react";
import Nav from "@core/Nav";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import PraxeEntity from "@components/Praxe/PraxeEntity";
import PopUpCon from "@core/Container/PopUpCon";
import { useNabidkaAPI } from "src/api/nabidka/nabidkaAPI";
import { useNavigate } from "react-router-dom";

export default function PraxePage() {

    const [ selectedEntity, setSelectedEntity ] = useState({});
    const nabidkaAPI  = useNabidkaAPI();
    const [ data, setData]  = useState(null);
    const [ popUp, setPopUp ] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        const initFetch = async() => {
            const res = await nabidkaAPI.getPracticeUserRelations();
            setData(res);
        }
        initFetch();
    }, [])

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

    // Pop Up render
    const renderPopUp = () => {
        return (
            <PopUpCon 
                title={selectedEntity.title} 
                onClose={handlePopUp} 
                text={"Opravdu si přejete zahájit tuto praxi?"}
                onSubmit={() => console.log("Submit")}
                onReject={handlePopUp}
            />
        )
    }

    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <Container property={"flex flex-col gap-2"}>
                    {/* render pro studenta */}
                    {!data ? (
                        <Paragraph>Načítání...</Paragraph>
                    ) : (
                        <>
                            <Headings sizeTag={"h4"} property={"mb-4"}>Podané přihlášky 
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
                            
                            <Headings sizeTag={"h4"} property={"mb-4 mt-4"}>Pozávnky od firem
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
            </Container>
            {popUp && renderPopUp()}
        </Container>
    )
}
