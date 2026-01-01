import React, { useState } from "react";
import Container from "@core/Container/Container";
import ContainerForEntity from "@core/Container/ContainerForEntity";
import Headings from "@core/Text/Headings";
import Paragraph from "@core/Text/Paragraph";
import TextField from "@core/Form/TextField";
import Button from "@core/Button/Button";
import BackButton from "@core/Button/BackButton";
import { useUserAPI } from "@api/user/userAPI";
import { useMessage } from "@hooks/MessageContext";

export default function PasswordResetRequestPage() {
    const { requestPasswordReset } = useUserAPI();
    const { addMessage } = useMessage();
    const [email, setEmail] = useState("");
    const [loading, setLoading] = useState(false);
    const [submitted, setSubmitted] = useState(false);

    const handleSubmit = async () => {
        if (!email) {
            addMessage("Zadejte prosím email", "E");
            return;
        }

        setLoading(true);
        try {
            await requestPasswordReset(email);
            setSubmitted(true);
            addMessage("Pokud účet existuje, email s instrukcemi byl odeslán.", "S");
        } catch (error) {
            // Z bezpečnostních důvodů neříkáme, jestli email existuje nebo ne,
            // ale backend může vrátit specifickou chybu pro STAG uživatele.
            if (error.response && error.response.data && error.response.data.detail) {
                addMessage(error.response.data.detail, "E");
            } else {
                addMessage("Chyba při odesílání žádosti.", "E");
            }
        } finally {
            setLoading(false);
        }
    };

    return (
        <Container property="flex items-center justify-center">
            <ContainerForEntity property="w-full max-w-md p-8">
                <BackButton />
                <Headings sizeTag="h2" property="mb-4 mt-4 text-center">Zapomenuté heslo</Headings>
                
                {!submitted ? (
                    <>
                        <Paragraph property="mb-6 text-center text-gray-600">
                            Zadejte svůj email a my vám pošleme odkaz pro obnovu hesla.
                        </Paragraph>
                        
                        <TextField 
                            id="email"
                            type="email"
                            label="Email"
                            placeholder="vas@email.cz"
                            value={email}
                            onChange={(value) => setEmail(value.email)}
                            required
                        />

                        <Container property="flex justify-center mt-6">
                            <Button 
                                onClick={handleSubmit} 
                                property="w-full"
                                disabled={loading}
                            >
                                {loading ? "Odesílám..." : "Odeslat odkaz"}
                            </Button>
                        </Container>
                    </>
                ) : (
                    <Container property="text-center">
                        <Paragraph property="mb-6 text-green-600 font-medium">
                            Zkontrolujte svou emailovou schránku. Odkaz pro obnovu hesla byl odeslán.
                        </Paragraph>
                        <Button onClick={() => window.location.href = "/"} variant="secondary">
                            Zpět na přihlášení
                        </Button>
                    </Container>
                )}
            </ContainerForEntity>
        </Container>
    );
}
