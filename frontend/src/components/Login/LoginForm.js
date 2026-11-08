import React, {useState, useCallback} from "react";
import Container from "@core/Container/Container";
import Button from "@core/Button/Button";
import Headings from "@components/core/Text/Headings";
import LoginSwitch from "./LoginSwitch";
import Paragraph from "@components/core/Text/Paragraph";
import TextField from "@core/Form/TextField";
import { useNavigate } from "react-router-dom";
import { validateEmail, validateRequired } from "@utils/validationUtils";

export default function LoginForm({handleSTAGLogin, handleOrganizationLogin}) {
    const [loginAccess, setLoginAccess] = useState({ switch: "STAG" });

    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [studentId, setStudentId] = useState("");
    const [teacherId, setTeacherId] = useState("");
    const [errors, setErrors] = useState({});
    const navigate = useNavigate();

    const handleAccess = useCallback((newValues) => {
        setLoginAccess(prevState => ({
            ...prevState,
            ...newValues
        }));
        setErrors({});
    }, []);

    const onEmailChange = (val) => {
        setEmail(val.email);
        if (errors.email) setErrors(prev => ({ ...prev, email: null }));
    };

    const onPasswordChange = (val) => {
        setPassword(val.password);
        if (errors.password) setErrors(prev => ({ ...prev, password: null }));
    };

    const onOrgLogin = () => {
        const newErrors = {};
        if (!validateRequired(email)) {
            newErrors.email = "E-mail je povinný";
        } else if (!validateEmail(email)) {
            newErrors.email = "Neplatný formát e-mailu";
        }

        if (!validateRequired(password)) {
            newErrors.password = "Heslo je povinné";
        }

        if (Object.keys(newErrors).length > 0) {
            setErrors(newErrors);
            return;
        }

        handleOrganizationLogin({ email, password });
    };

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
                <Headings sizeTag="h4" property="text-center">{"Přihlášení"}</Headings>

               { loginAccess.switch !== "STAG" ? (
                <>
                <TextField
                    id="email"
                    onIconClick={handleButtonClick}
                    icon="user"
                    required={true}
                    label={"E-mail"}
                    placeholder={"E-mail"}
                    property="m-4"
                    value={email}
                    onChange={onEmailChange}
                    error={errors.email}
                />
                <TextField
                    id="password"
                    type="password"
                    onIconClick={handleButtonClick}
                    icon="lock"
                    required={true}
                    label={"Heslo"}
                    placeholder="*****"
                    property="m-4"
                    value={password}
                    onChange={onPasswordChange}
                    error={errors.password}
                />
                <Container property="flex justify-end m-4 mt-0">
                    <Paragraph
                        variant="small"
                        property="text-blue-600 cursor-pointer hover:underline"
                        onClick={() => navigate("/reset-password")}
                    >
                        {"Zapomněli jste heslo?"}
                    </Paragraph>
                </Container>
                </>
                ):
                (
                    <Container property="m-4">
                        <Paragraph property="text-center mb-16">{"Přihlášení pomocí systému STAG příslušné univerzity."}</Paragraph>
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
                            {"Přihlaste se"}
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
                                    label={"Zadejte osCislo studenta (nepovinné)"}
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
                                    label={"Zadejte ucitIdno učitele (nepovinné)"}
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
                            onClick={onOrgLogin}
                        >
                            {"Přihlaste se"}
                        </Button>

                        <Button
                            property={"w-full items-center mt-2"}
                            variant="yellow"
                            onClick={() => navigate("/registrace")}
                        >
                            {"Registrace"}
                        </Button>
                    </>
                )

                }


            </Container>
        </Container>
    );
}
