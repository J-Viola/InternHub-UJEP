import React from "react";
import Nav from "@core/Nav";
import Container from "@core/Container/Container";
import UserEntity from "@components/User/UserEntity";
import Headings from "@core/Text/Headings";
import Paragraph from "@components/core/Text/Paragraph";
import BackButton from "@core/Button/BackButton";
import SearchBar from "@components/Filter/SearchBar";


export default function StudentPage() {
    const entities = [
        {
            name: "Pavel",
            surname: "Mareš",
            titles: {
                before: "RNDr",
                after: "Dis."
            },
            field: "INF",
            school: "UJEP"
        },
        {
            name: "Adam",
            surname: "Novák",
            titles: {
                before: "RNDr",
                after: "Dis."
            },
            field: "INF"
        }
    ]

    const btnLayout = [
        {
            icon: "eye",
            btnfunction: () => console.log("Profil")
        },
        {
            icon: "user",
            btnfunction: () => console.log("Karta")
        }
    ]

    const attributes = {
        "Obor": "field", 
        "Škola": "school"
    }

    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <BackButton/>
                <Container property={"flex items-center justify-between mb-6 mt-4"}>
                    <Headings sizeTag={"h3"} property={"mt-2"}>
                        Studenti
                    </Headings>

                </Container>
                <Container property={"mt-auto"}>
                    <SearchBar
                        placeholder={"Hledat podle jména..."}
                    
                    />
                </Container>
                <Container property={"mt-4"}>
                    {entities.map(entity => (
                        <UserEntity
                            key={entity.name + entity.surname}
                            entity={entity}
                            attributes={attributes}
                            buttons={btnLayout}
                        />
                    ))}
                </Container>
            </Container>
        </Container>
    )
}