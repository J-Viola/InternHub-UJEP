import React from "react";
import ContainerForEntity from "./ContainerForEntity";
import Container from "./Container";
import Button from "@core/Button/Button";
import Headings from "@core/Text/Headings";
import Paragraph from "../Text/Paragraph";
import { useTranslation } from "react-i18next";

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
    const { t } = useTranslation();
    const closePopUp = () => {
        if (onClose) {
            onClose();
        }
    };

    const displaySubmitText = onSubmitText || t('common.yes');
    const displayRejectText = onRejectText || t('common.no');

    // Custom container variant
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
                                {text || t('practice_detail.docs_check_not_defined')}
                            </Paragraph>
                        </Container>

                        {/* BUTTONY */}
                        <Container property={"flex justify-between ml-4 mr-4 gap-4"}>
                            {onSubmit && <Button id="popup-confirm-button" property={"w-full"} onClick={onSubmit}>{displaySubmitText}</Button>}
                            {onReject && <Button id="popup-reject-button" variant={"red"} property={"w-full"} onClick={onReject}>{displayRejectText}</Button>}
                        </Container>
                    </ContainerForEntity>
                )}
            </Container>
        );
    }

    // Standardní variant
    return(
        <Container data-testid="popup-con" property={"fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"}>
            <ContainerForEntity property={"w-1/2 max-w-2xl"} variant={variant}>
                <Container property={"flex justify-between items-center mb-4"}>
                    <Headings property={"ml-4"} sizeTag={"h5"}>{title}</Headings>
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
        </Container>
    )
}
