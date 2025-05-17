import React, {useState, useCallback} from "react";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { cs } from "date-fns/locale";
import Container from "@core/Container/Container";
import Button from "@core/Button/Button";
import Paragraph from "@components/core/Text/Paragraph";
import { format } from "date-fns";

export default function CustomDatePicker({ id, property, value, required=false, label, onChange, children }) {
    const [date, setDate] = useState(value ? new Date(value) : null);
    const labelEntity = label ? <Paragraph>{label}</Paragraph> : null;
    const requiredLabel = <Paragraph property={"text-red-600 ml-1"}>*</Paragraph>

    const handleDateChange = useCallback((newDate) => {
        setDate(newDate);
        
        if (onChange) {
            const formattedDate = newDate ? format(newDate, 'dd.MM.yyyy') : null;
            onChange({ [id]: formattedDate });
        }
    }, [id, onChange]);

    return (
        <Container property={"w-full"}>
            <Container property="flex items-center w-full">
                {labelEntity}
                {required && requiredLabel}
            </Container>
            <Container property="relative">
                <DatePicker
                    selected={date}
                    onChange={handleDateChange}
                    locale={cs}
                    dateFormat="dd.MM.yyyy"
                    placeholderText="Vyberte datum"
                    className="w-full px-2 py-1 text-base text-gray-900 bg-gray-100 rounded-lg border-2 pl-10"
                />
                <Container property="absolute left-3 top-1/2 transform -translate-y-1/2">
                    <Button icon={"calendar"} pointer={false} noVariant={true} iconColor={"text-gray-900"} />
                </Container>
            </Container>
        </Container>
    );
}