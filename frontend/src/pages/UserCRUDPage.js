import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import Nav from "@components/core/Nav";
import LoginForm from "@login/LoginForm";
import { STAGLogin, getParams } from "@auth/STAGLogin";
import { useAuth } from "@auth/Auth";
import UserEntity from "@components/User/UserEntity";
import { useParams } from "react-router-dom";
import { useUserAPI } from "@api/user/userAPI";


export default function UserCRUDPage() {
    const [data, setData] = useState([])
    const { type } = useParams("type")
    const userAPI = useUserAPI();

    const rolesTranslator = {"OWNER" : "Jednatel firmy", "INSERTER" : "Správce inzerátů"}
    const headings = {"org":"Uživatelské účty organizace"}

    const translateRoles = (dataArr) => {
        return dataArr.map(entity => ({
            ...entity,
            roleText: rolesTranslator[entity.role] || entity.role
        }));
    }

    useEffect(() => {
        const initFetch = async() => {
            const res = await userAPI.getOrganizationUsers(false)
            if (res) {
                setData(translateRoles(res));
            }
        }
        initFetch();
    },[])

    // useEffect pro překlad už není potřeba

    
    return(
    <Container property="min-h-screen">
        <Nav/>
        <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
            <BackButton/>
            <Container property={"flex items-center justify-between mb-6 mt-4"}>
                <Headings sizeTag={"h3"} property={"mt-2"}>
                    {type ? (headings[type]) : ("nemám param")}
                </Headings>
            </Container>

            <Container>
                <Button 
                    onClick={() => console.log("Handle na vytvoření")}
                    icon={"plus"}
                >
                    Založit uživatele
                </Button>
            </Container>

            <Container property={"mt-4 rounded-lg"}>
                {!data ? (
                    <Paragraph>Načítání...</Paragraph>
                ) : data.length === 0 ? (
                    <Paragraph property="text-center text-gray-500 py-8">
                        Zatím nemáte žádné data kzobrazení.
                    </Paragraph>
                ) : (
                    <Container property={"grid grid-cols-1 gap-4"}>
                        {data?.map(entity => (
                            <UserEntity
                                key={entity.id}
                                entity={entity}
                                attributes={{"Role": "roleText"}}
                                buttons={[
                                    {
                                        icon: "edit",
                                        btnfunction: () => console.log("Upravit uživatele", entity.id)
                                    }
                                ]}
                            />
                        ))}
                    </Container>
                )}
            </Container>
        </Container>
    </Container>
    )
}