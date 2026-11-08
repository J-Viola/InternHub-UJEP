import React, { useEffect, useRef } from "react";
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
    onSubmitText,
    onRejectText,
    variant = "gray",
    useCustomContainer = false,
    customContainer = null
}) {
    const dialogRef = useRef(null);
    const returnFocusRef = useRef(null);

    useEffect(() => {
        returnFocusRef.current = document.activeElement;
        const firstControl = dialogRef.current?.querySelector("button, input, textarea, select, [tabindex]:not([tabindex='-1'])");
        firstControl?.focus();
        const onKeyDown = (event) => {
            if (event.key === "Escape") {
                event.preventDefault();
                closePopUp();
            }
        };
        document.addEventListener("keydown", onKeyDown);
        return () => {
            document.removeEventListener("keydown", onKeyDown);
            returnFocusRef.current?.focus?.();
        };
    }, []);
    const closePopUp = () => {
        if (onClose) {
            onClose();
        }
    };

    const displaySubmitText = onSubmitText || "Ano";
    const displayRejectText = onRejectText || "Ne";

    // Custom container variant
    if (useCustomContainer) {
        return (
            <div role="dialog" aria-modal="true" aria-labelledby="popup-dialog-title" ref={dialogRef} className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
                {customContainer || (
                    <ContainerForEntity property={"w-1/2 max-w-2xl"} variant={variant}>
                        <Container property={"flex justify-between items-center mb-4"}>
                            <Headings id="popup-dialog-title" property={"ml-4"} sizeTag={"h5"}>{title}</Headings>
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

                        {/* BUTTONY */}
                        <Container property={"flex justify-between ml-4 mr-4 gap-4"}>
                            {onSubmit && <Button id="popup-confirm-button" property={"w-full"} onClick={onSubmit}>{displaySubmitText}</Button>}
                            {onReject && <Button id="popup-reject-button" variant={"red"} property={"w-full"} onClick={onReject}>{displayRejectText}</Button>}
                        </Container>
                    </ContainerForEntity>
                )}
            </div>
        );
    }

    // Standardní variant
    return(
        <div role="dialog" aria-modal="true" aria-labelledby="popup-dialog-title" ref={dialogRef} data-testid="popup-con" className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
            <ContainerForEntity property={"w-1/2 max-w-2xl"} variant={variant}>
                <Container property={"flex justify-between items-center mb-4"}>
                    <Headings id="popup-dialog-title" property={"ml-4"} sizeTag={"h5"}>{title}</Headings>
                    <Button variant={"red"} onClick={onClose} property={"px-2 py-1"}>
                        X
                    </Button>
                </Container>

                {/* TEXT BOXU */}
                <Container property={"mb-16 mt-16"}>
                    <Paragraph property={"text-center"}>{text ? text : ""}</Paragraph>
                </Container>

                {/* BUTTONY */}
                <Container property={"flex justify-between ml-4 mr-4 gap-4"}>
                    <Button id="popup-confirm-button" property={"w-full"} onClick={onSubmit}>{displaySubmitText}</Button>
                    <Button id="popup-reject-button" variant={"red"} property={"w-full"} onClick={onReject}>{displayRejectText}</Button>
                </Container>

                <Container property={"max-h-[80vh] overflow-y-auto"}>
                    {children}
                </Container>
            </ContainerForEntity>
        </div>
    )
}
