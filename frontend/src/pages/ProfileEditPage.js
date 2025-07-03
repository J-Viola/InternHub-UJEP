import React, {useState, useEffect} from "react";
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
import { useUser } from "@hooks/UserProvider";
import { useNavigate } from "react-router-dom";
import { useParams } from "react-router-dom";
import { useStudentAPI } from "@api/student/studentAPI";


export default function ProfileEditPage() {
    const { id } = useParams();
    const { user } = useUser();
    const navigate = useNavigate();
    const students = useStudentAPI();
    const  [ userProfile, setUserProfile ] = useState({});

    const fetchUser = async() => {
        if (id) {
            const res = await students.getStudentById(id)
            console.log("res", res);
            setUserProfile(res);
        } if (user && user.id) {
            const res = await students.getStudentById(user.id)
            console.log("res", res);
            setUserProfile(res);
        }
    }


    const handleFormChange = (data) => {
        const [fieldName, value] = Object.entries(data)[0];
        
        setUserProfile(prev => ({
            ...prev,
            [fieldName]: value
        }));
    };

    const handleFileChange = (file) => {
        console.log("File changed:", file);
        setUserProfile(prev => ({
            ...prev,
            profile_picture: file
        }));
    }

    const handlePushChanges = async () => {
        try {
            if (userProfile) {
                // await apiCallToEditProfile(userProfile) - DODĚLAT;
                console.log("Pushuju na neexistující endpoint!")
                console.log(userProfile);
            }
        } catch (err) {
            throw new Error(err);
        }
    }

    useEffect(() => {
        console.log("Profile", userProfile);
    }, [userProfile])


    useEffect(() => {
        fetchUser();
    }, [id, user])

    return(
        <Container property={"min-h-screen"}>
        <Nav/>
        <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
            <BackButton></BackButton>
            <Paragraph>{id ? id : "nemám id"}</Paragraph>
            <Container property={"bg-gray-50 mt-2 p-4 rounded-lg"}>
                <UserForm 
                    userProfile={userProfile}
                    handleChange={handleFormChange}
                    handleFileChange={handleFileChange}
                    handleSubmit={handlePushChanges}
                />
            </Container>
        </Container>
    </Container>

    );
       
}