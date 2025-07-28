import React, {useState, useCallback, useEffect} from "react";
import DatePicker from "react-datepicker";
import "react-datepicker/dist/react-datepicker.css";
import { cs } from "date-fns/locale";
import Container from "@core/Container/Container";
import Button from "@core/Button/Button";
import Paragraph from "@components/core/Text/Paragraph";
import { format } from "date-fns";

export default function CustomDatePicker({ id, property, value, required=false, label, onChange, children, locked=false }) {
    const [date, setDate] = useState(null);
    const labelEntity = label ? <Paragraph>{label}</Paragraph> : null;
    const requiredLabel = <Paragraph property={"text-red-600 ml-1"}>*</Paragraph>

    // Synchronizace date state s value prop
    useEffect(() => {
        if (value) {
            let newDate = null;
            
            // český formát dd.MM.yyyy na Date objekt
            if (typeof value === 'string' && value.includes('.')) {
                const parts = value.split('.');
                if (parts.length === 3) {
                    const day = parseInt(parts[0], 10);
                    const month = parseInt(parts[1], 10) - 1; // měsíce jsou 0-11
                    const year = parseInt(parts[2], 10);
                    
                    newDate = new Date(year, month, day);
                    
                    // Ověření, že datum je validní
                    if (!isNaN(newDate.getTime()) && 
                        newDate.getDate() === day && 
                        newDate.getMonth() === month && 
                        newDate.getFullYear() === year) {
                        setDate(newDate);
                        return;
                    }
                }
            }

            // Pokus o standardní parsování
            newDate = new Date(value);
            if (!isNaN(newDate.getTime())) {
                setDate(newDate);
            } else {
                setDate(null);
            }
        } else {
            setDate(null);
        }
    }, [value]);

    const handleDateChange = useCallback((newDate) => {
        setDate(newDate);
        
        if (onChange) {
            const formattedDate = newDate && !isNaN(newDate.getTime()) ? format(newDate, 'dd.MM.yyyy') : null;
            onChange({ [id]: formattedDate });
        }
    }, [id, onChange]);

    if (locked) {
        return (
            <Container property={"w-full"}>
                <Container property="flex items-center w-full">
                    {labelEntity}
                    {required && requiredLabel}
                </Container>
                <Container property="relative">
                    <input
                        type="text"
                        value={date && !isNaN(date.getTime()) ? format(date, 'dd.MM.yyyy') : ''}
                        readOnly
                        disabled
                        className="w-full px-2 py-1 text-base text-gray-900 bg-gray-100 rounded-lg border-2 pl-10 opacity-60 cursor-not-allowed"
                    />
                    <Container property="absolute left-3 top-1/2 transform -translate-y-1/2">
                        <Button icon={"calendar"} hover={false} pointer={false} noVariant={true} iconColor={"text-gray-900"} />
                    </Container>
                </Container>
            </Container>
        );
    }

    return (
        <Container property={"w-full"}>
            <Container property="flex items-center w-full">
                {labelEntity}
                {required && requiredLabel}
            </Container>
            <Container property="relative">
                <DatePicker
                    selected={date && !isNaN(date.getTime()) ? date : null}
                    onChange={handleDateChange}
                    locale={cs}
                    dateFormat="dd.MM.yyyy"
                    placeholderText="Vyberte datum"
                    className="w-full px-2 py-1 text-base text-gray-900 bg-gray-100 rounded-lg border-2 pl-10"
                />
                <Container property="absolute left-3 top-1/2 transform -translate-y-1/2">
                    <Button icon={"calendar"} hover={false} pointer={false} noVariant={true} iconColor={"text-gray-900"} />
                </Container>
            </Container>
        </Container>
    );
}