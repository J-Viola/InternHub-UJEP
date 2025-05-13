import React, {useState} from "react";
import Nav from "@core/Nav";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import PraxeEntity from "@components/Praxe/PraxeEntity";
import PopUpCon from "@core/Container/PopUpCon";

export default function PraxePage() {

    const [selectedEntity, setSelectedEntity] = useState({});

    const entity = {
        title: "IOS Developer",
        logo: "LOGO",
        administration_date: "23. 10. 2025",
        status: "Pozvánka"

    }

    const entity2 = {
        title: "IOS Developer",
        logo: "LOGO",
        administration_date: "23. 10. 2025",
        status: "Probíhající stáž"

    }

    const entity3 = {
        title: "IOS Developer",
        logo: "LOGO",
        administration_date: "23. 10. 2025",
        status: "Zrušená přihláška"

    }

    // hook na entitu
    const handleClick = (entity) => {
        console.log("clicked praxe:", entity);
        setSelectedEntity(entity); 
    }

    const handleView = (entity) => {
        console.log("Redirect na id entity:", entity.title)
    }

    // Pop Up render
    const renderPopUp = () => {
        return (
            <PopUpCon 
                title={selectedEntity.title} 
                onClose={() => handleClick({})} 
                text={"Opravdu si přejete zahájit tuto praxi?"}
                onSubmit={() => console.log("Submit")}
                onReject={() => handleClick({})}
            />
        )
    }

    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <Headings sizeTag={"h4"} property={"mb-4"}>Praxe</Headings>
                <Container property={"flex flex-col gap-2"}>
                    <PraxeEntity entity={entity} onClick={() => handleClick(entity)} onView={() => handleView(entity)}/>
                    <PraxeEntity entity={entity2} onClick={() => handleClick(entity2)} onView={() => handleView(entity2)}/>
                    <PraxeEntity entity={entity3} onClick={() => handleClick(entity3)} onView={() => handleView(entity3)}/>
                </Container>
            </Container>
            {Object.keys(selectedEntity).length > 0 && renderPopUp()}
        </Container>
    )
}
