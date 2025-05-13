import React from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import Headings from "@core/Text/Headings";
import Nav from "@core/Nav";
import Paragraph from "@components/core/Text/Paragraph";

export default function ProfilPage() {
    return(
        <Container property="min-h-screen">
            <Nav/>
            <Container property={"max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8"}>
                <ContainerForEntity property={"pl-8 pr-8 pt-4 pb-8"}>
                    <BackButton/>
                    <Container property="grid grid-cols-[auto,1fr] gap-4 mt-2 mb-8">
                        
                        {/* PROFILE PIC */}
                        <Container property="w-md bg-blue-600 rounded-lg p-4 flex items-center justify-center">
                            <Headings sizeTag="h4" property="text-white">
                                {"PROFILE PIC"}
                            </Headings>
                        </Container>

                        {/* USER NAME */}
                        <Headings sizeTag={"h2"} property={"mt-2"}>Profil uživatele</Headings>

                    </Container>

                    <Container property={"w-full mt-2 grid-cols-1"}>

                        {/* NĚCO O MĚ */}
                        <Container property="p-1 space-y-1 mb-4">
                            <Headings sizeTag={"h4"}>Něco o mě</Headings>
                            <Paragraph>
                            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer ut dolor semper, congue lacus malesuada, gravida ipsum. Aenean porta porttitor risus at aliquet. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Integer leo ante, gravida ac ipsum vel, rhoncus congue felis. Sed rhoncus ornare scelerisque.
                            </Paragraph>
                        </Container>

                        {/* OSOBNÍ ÚDAJE */}
                        <Container property="p-1 space-y-1">
                            <Headings sizeTag={"h4"}>Osobní údaje</Headings>
                            <Paragraph>
                            Lorem ipsum dolor sit amet, consectetur adipiscing elit. Integer ut dolor semper, congue lacus malesuada, gravida ipsum. Aenean porta porttitor risus at aliquet. Class aptent taciti sociosqu ad litora torquent per conubia nostra, per inceptos himenaeos. Integer leo ante, gravida ac ipsum vel, rhoncus congue felis. Sed rhoncus ornare scelerisque.
                            </Paragraph>
                        </Container>

                        {/* SKILLS */}
                        <Container property="p-1 space-y-1">
                            <Headings sizeTag={"h4"}>Skills</Headings>
                            <Container property={"flex flex-wrap gap-2"}>

                                <Button pointer={false} variant="blueSmallNoHover">
                                    {"Skill 1"}
                                </Button>

                                <Button pointer={false} variant="blueSmallNoHover">
                                    {"Skill 2"}
                                </Button>
                                
                            </Container>
                        </Container>

                        <Container property="p-1 space-y-1">
                            <Headings sizeTag={"h4"}>CV</Headings>
                            <Button icon="download">Stáhnout</Button>
                        </Container>

                    </Container>

                </ContainerForEntity>
            </Container>

        </Container>
    )
}