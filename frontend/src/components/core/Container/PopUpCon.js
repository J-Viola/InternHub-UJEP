import React from "react";
import ContainerForEntity from "./ContainerForEntity";
import Container from "./Container";
import Button from "@core/Button/Button";
import Headings from "@core/Text/Headings";
import Paragraph from "../Text/Paragraph";

export default function PopUpCon({children, onClose, title, text, onSubmit, onReject, variant = "gray"}) {
    return(
        <Container property={"fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"}>
            <ContainerForEntity property={"w-1/2 max-w-2xl"} variant={variant}>
                <Container property={"flex justify-between items-center mb-4"}>
                    <Headings sizeTag={"h5-bold"}>{title}</Headings>
                    <Button variant={"red"} onClick={onClose} property={"px-2 py-1"}>
                        X
                    </Button>
                </Container>

                {/* TEXT BOXU */}
                <Container property={"mb-16 mt-16"}>
                    <Paragraph property={"text-center"}>{text ? text : "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."}</Paragraph>
                </Container>

                {/* BUTTONY */}
                <Container property={"flex justify-between ml-4 mr-4 gap-4"}>
                    <Button property={"w-full"} onClick={onSubmit}>Ano</Button>
                    <Button variant={"red"} property={"w-full"} onClick={onReject}>Ne</Button>
                </Container>


                <Container property={"max-h-[80vh] overflow-y-auto"}>
                    {children}
                </Container>
            </ContainerForEntity>
        </Container>
    )
}