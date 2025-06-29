import React, {useState, useEffect} from "react";
import Nav from "@core/Nav";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import PraxeEntity from "@components/Praxe/PraxeEntity";
import PopUpCon from "@core/Container/PopUpCon";
import { usePrihlaskaAPI } from "@api/prihlaska/prihlaskaAPI";
import { useUser } from "@hooks/UserProvider";


export default function PraxePage() {
    const [selectedEntity, setSelectedEntity] = useState({});
    const [practices, setPractices] = useState([]);
    const [loading, setLoading] = useState(true);
    const prihlaskaAPI = usePrihlaskaAPI();
    const { user } = useUser();


    const fetchPractices = async () => {
        try {
            if (user && user.id) {
                setLoading(true);
                const result = await prihlaskaAPI.getStudentPractices(user.id);
                setPractices(result.data);
            }
        } catch (error) {
            console.error("Chyba při načítání praxí:", error);
        } finally {
            setLoading(false);
        }
    };


    useEffect(() => {
        fetchPractices();
    }, [user]);

    const handleClick = (entity) => {
        console.log("clicked praxe:", entity);
        setSelectedEntity(entity); 
    }

    const handleView = (entity) => {
        console.log("Redirect na id entity:", entity.id)
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
                    {loading ? (
                        <Paragraph>Načítání praxí...</Paragraph>
                    ) : practices.length > 0 ? (
                        practices.map((entity) => (
                            <PraxeEntity 
                                key={entity.id}
                                entity={entity} 
                                onClick={() => handleClick(entity)} 
                                onView={() => handleView(entity)}
                            />
                        ))
                    ) : (
                        <Paragraph>Žádné praxe nebyly nalezeny...</Paragraph>
                    )}
                </Container>
            </Container>
            {Object.keys(selectedEntity).length > 0 && renderPopUp()}
        </Container>
    )
}
