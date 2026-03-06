import React from "react";
import Button from "./Button";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";

export default function BackButton() {
    const { t } = useTranslation();
    const navigate = useNavigate()

    const handleBack = () => {
        navigate(-1);
    }

    return(
        <Button variant={"primarySmall"} property={"mb-2"} icon={"arrowLeft"} iconColor={"text-white"} onClick={() => handleBack()}>
            {t('common.back')}
        </Button>
    )
}
