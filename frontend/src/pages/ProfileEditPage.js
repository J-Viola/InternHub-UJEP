import React, {useState} from "react";
import Container from "@core/Container/Container";
import TextField from "@core/Form/TextField";
import DropDown from "@core/Form/DropDown";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@components/core/Text/Paragraph";
import TextBox from "@core/Form/TextBox";
import Nav from "@components/core/Nav";
import CustomDatePicker from "@core/Form/DatePicker";
import Button from "@components/core/Button/Button";
import UserForm from "@components/Forms/UserForm";
import { useParams } from "react-router-dom";


export default function ProfileEditPage() {
    const { id } = useParams();

    return(

        <Container property={"min-h-screen"}>
        <Nav/>
        <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <BackButton></BackButton>
            <Paragraph>{id ? id : "nemám id"}</Paragraph>
            <Container property={"bg-gray-50 mt-2 p-4 rounded-lg"}>
                <UserForm/> {/* Formulář pro uživatele */}
            </Container>
        </Container>
    </Container>

    );
       
}