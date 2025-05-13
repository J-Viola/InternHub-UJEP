import React from "react";
import Nav from "@core/Nav";
import Container from "@core/Container/Container";
import UserEntity from "@components/Users/UserEntity";
import Paragraph from "@components/core/Text/Paragraph";

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
            btnfunction: () => console.log("Hello")
        },
        {
            icon: "edit",
            btnfunction: () => console.log("Upravit")
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
                <Container property={"w-full flex-row gap-2 mt-2"}>
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