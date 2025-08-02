import React from "react";
import ContainerForEntity from "./ContainerForEntity";
import Container from "./Container";
import Button from "@core/Button/Button";
import Headings from "@core/Text/Headings";
import Paragraph from "../Text/Paragraph";

export default function PopUpCon({
    children, 
    onClose, 
    title, 
    text, 
    onSubmit, 
    onReject, 
    onSubmitText = "Ano", 
    onRejectText = "Ne", 
    variant = "gray",
    useCustomContainer = false,
    customContainer = null
}) {
    const closePopUp = () => {
        if (onClose) {
            onClose();
        }
    };

    // Custom container variant s 3 tlačítky - tam kde není definovaný proces => předělat pouze přes {children}
    if (useCustomContainer) {
        return (
            <Container property={"fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"}>
                {customContainer || (
                    <ContainerForEntity property={"w-1/2 max-w-2xl"} variant={variant}>
                        <Container property={"flex justify-between items-center mb-4"}>
                            <Headings property={"ml-4"} sizeTag={"h5"}>{title}</Headings>
                            <Button variant={"red"} onClick={closePopUp} property={"px-2 py-1"}>
                                X
                            </Button>
                        </Container>

                        {/* TEXT BOXU */}
                        <Container property={"mb-8 mt-8"}>
                            <Paragraph property={"text-center"}>
                                {text || "Proces není definován"}
                            </Paragraph>
                        </Container>

                        {/* 3 TLAČÍTKA */}
                        <Container property={"flex flex-col gap-4 ml-4 mr-4 mb-4"}>
                            <Button 
                                property={"w-full"} 
                                onClick={closePopUp}
                                variant="primary"
                            >
                                Tlačítko 1
                            </Button>
                            <Button 
                                property={"w-full"} 
                                onClick={closePopUp}
                                variant="blue"
                            >
                                Tlačítko 2
                            </Button>
                            <Button 
                                property={"w-full"} 
                                onClick={closePopUp}
                                variant="red"
                            >
                                Tlačítko 3
                            </Button>
                        </Container>
                    </ContainerForEntity>
                )}
            </Container>
        );
    }

    // Standardní variant
    return(
        <Container property={"fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"}>
            <ContainerForEntity property={"w-1/2 max-w-2xl"} variant={variant}>
                <Container property={"flex justify-between items-center mb-4"}>
                    <Headings property={"ml-4"} sizeTag={"h5"}>{title}</Headings>
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
                    <Button property={"w-full"} onClick={onSubmit}>{onSubmitText}</Button>
                    <Button variant={"red"} property={"w-full"} onClick={onReject}>{onRejectText}</Button>
                </Container>

                <Container property={"max-h-[80vh] overflow-y-auto"}>
                    {children}
                </Container>
            </ContainerForEntity>
        </Container>
    )
}