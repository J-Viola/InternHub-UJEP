import React, {useState, useCallback} from "react";
import Container from "@core/Container/Container";
import Button from "@core/Button/Button";
import Headings from "@components/core/Text/Headings";
import LoginSwitch from "@login/LoginSwitch";
import Paragraph from "@components/core/Text/Paragraph";
import TextField from "@core/Form/TextField";
import { useNavigate } from "react-router-dom";

export default function LoginForm({handleSTAGLogin, handleOrganizationLogin}) {
    const [loginAccess, setLoginAccess] = useState({});
    const [studentId, setStudentId] = useState("");
    const [teacherId, setTeacherId] = useState("");
    const navigate = useNavigate();

    const handleAccess = useCallback((newValues) => {
        setLoginAccess(prevState => ({
            ...prevState,
            ...newValues
        }));

    }, []);

    const handleStudentIdChange = (values) => {
        setStudentId(values.studentId);
    };

    const handleTeacherIdChange = (values) => {
        setTeacherId(values.teacherId);
    };

    const handleMockStudentLogin = () => {
        const ticket = studentId ? `mock-student:${studentId}` : 'student-ticket';
        window.location.href = `/?stagUserTicket=${ticket}`;
    };

    const handleMockTeacherLogin = () => {
        const ticket = teacherId ? `mock-teacher:${teacherId}` : 'teacher-ticket';
        window.location.href = `/?stagUserTicket=${ticket}`;
    };

    const handleButtonClick = () => {
        // placeholder for icon click
    }

    return (
        <Container property="min-h-screen flex items-center justify-center p-0 mx-auto">
            <Container property="w-full max-w-md p-8 bg-white rounded-lg shadow-lg">
                <LoginSwitch getLoginType={handleAccess}/>
                <Headings sizeTag="h4" property="text-center">Přihlášení</Headings>

               { loginAccess.switch !== "STAG" ? (
                <>
                <TextField
                    id="email"
                    onIconClick={handleButtonClick}
                    icon="user"
                    required={true}
                    label="E-mail"
                    placeholder="E-mail"
                    property="m-4"
                    onChange={handleAccess}
                />
                <TextField
                    id="password"
                    type="password"
                    onIconClick={handleButtonClick}
                    icon="lock"
                    required={true}
                    label="Heslo"
                    placeholder="*****"
                    property="m-4"
                    onChange={handleAccess}
                />
                <Container property="flex justify-end m-4 mt-0">
                    <Paragraph
                        variant="small"
                        property="text-blue-600 cursor-pointer hover:underline"
                        onClick={() => navigate("/reset-password")}
                    >
                        Zapomněli jste heslo?
                    </Paragraph>
                </Container>
                </>
                ):
                (
                    <Container property="m-4">
                        <Paragraph property="text-center mb-16">Přihlášení pomocí systému STAG příslušné univerzity.</Paragraph>
                    </Container>
                )
                }

                {loginAccess.switch === "STAG" ? (
                    <>
                        {/* STAG LOGIN */}
                        <Button
                            property={"w-full items-center"}
                            onClick={handleSTAGLogin}
                        >
                            Přihlaste se
                        </Button>
                        {process.env.NODE_ENV === 'development' && (
                            <>
                                <Button
                                    property={"w-full items-center mt-4 bg-gray-500 hover:bg-gray-600"}
                                    onClick={() => window.location.href = "/?stagUserTicket=demo-ticket"}
                                >
                                    Demo Login (Dev)
                                </Button>

                                <TextField
                                    id="studentId"
                                    label="Zadejte osCislo studenta (nepovinné)"
                                    placeholder="S12345"
                                    property="mt-4 mb-2"
                                    value={studentId}
                                    onChange={handleStudentIdChange}
                                />
                                <Button
                                    property={"w-full items-center bg-blue-500 hover:bg-blue-600"}
                                    onClick={handleMockStudentLogin}
                                >
                                    Mock Student (Dev)
                                </Button>

                                <TextField
                                    id="teacherId"
                                    label="Zadejte ucitIdno učitele (nepovinné)"
                                    placeholder="U98765"
                                    property="mt-4 mb-2"
                                    value={teacherId}
                                    onChange={handleTeacherIdChange}
                                />
                                <Button
                                    property={"w-full items-center bg-green-500 hover:bg-green-600"}
                                    onClick={handleMockTeacherLogin}
                                >
                                    Mock Teacher (Dev)
                                </Button>
                            </>
                        )}
                    </>


                ):(
                    <>
                        {/* ORGANIZACE LOGIN */}
                        <Button
                            property={"w-full items-center"}
                            onClick={() => handleOrganizationLogin(loginAccess)}
                        >
                            Přihlaste se
                        </Button>

                        <Button
                            property={"w-full items-center mt-2"}
                            variant="yellow"
                            onClick={() => navigate("/registrace")}
                        >
                            Registrace
                        </Button>
                    </>
                )

                }


            </Container>
        </Container>
    );
}
