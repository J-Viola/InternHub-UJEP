import React from "react";
import Container from "@core/Container/Container";
import Button from "@core/Button/Button";
import { useTranslation } from "react-i18next";

export default function SearchBar({ id = "title", value, placeholder, onChange, onClear }) {
    const { t } = useTranslation();
    const inputClass = `w-full py-1 px-2 text-black bg-facultyColLight rounded-lg border border-black placeholder-gray-800`;

    return (
        <Container property="relative inline-block w-full items-center justify-center">
            <input
                type={"text"}
                id={id}
                className={inputClass}
                placeholder={placeholder ? placeholder : t('common.search')}
                value={value || ""}
                onChange={onChange}
            />
            <Container property="absolute right-2 top-1/2 -translate-y-1/2">
                {value !== "" && <Button noVariant={true} icon={"cross"} iconColor="text-black" onClick={onClear}/>}
            </Container>
        </Container>
    )
}
