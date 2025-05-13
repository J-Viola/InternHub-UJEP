import React, { useState } from "react";
import Container from "@core/Container/Container";
import Nav from "@components/core/Nav";
import Headings from "@core/Text/Headings";
import BackButton from "@core/Button/BackButton";
import Button from "@core/Button/Button";
import UserEntity from "@components/Users/UserEntity";

export default function VytvorenePraxe() {

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
            icon: "users",
            btnfunction: () => console.log("Uživatelé")
        },
        {
            icon: "edit",
            btnfunction: () => console.log("Upravit")
        }
    ]

    const attributes = {
        "Obor":"field",
        "Škola":"school"

    }

    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <BackButton/>
                <Headings property={"mt-2 mb-2"}>Vytvořené stáže</Headings>
                <Button
                    variant={"primarySmall"}
                    icon={"plus"}
                    onClick={() => console.log("Vytvořit stáž")}
                    text={"Založit stáž"}
                >
                </Button>

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