import React, { useState, useEffect } from "react";
import Container from "@core/Container/Container";
import Headings from "@core/Text/Headings";
import BackButton from "@core/Button/BackButton";
import Paragraph from "@core/Text/Paragraph";
import { useNabidkaAPI } from "@api/nabidka/nabidkaAPI";
import StudentApplicationCard from "@components/Student/StudentApplicationCard";
import StudentInvitationCard from "@components/Student/StudentInvitationCard";
import { useTranslation } from "react-i18next";

export default function StudentApplicationsPage() {
    const { t } = useTranslation();
    const { getPracticeUserRelations } = useNabidkaAPI();
    const [data, setData] = useState({ student_practices: [], employer_invitations: [] });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchData = async () => {
        try {
            setLoading(true);
            setError(null);
            const res = await getPracticeUserRelations();
            if (res) setData(res);
        } catch {
            setError(t('internships.error'));
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    return (
        <Container property="p-4 max-w-7xl mx-auto">
            <BackButton />
            <Headings sizeTag="h2" property="mb-6 mt-4">{t('internships.my_practices_and_apps')}</Headings>

            {loading ? (
                <Paragraph>{t('common.loading')}</Paragraph>
            ) : error ? (
                <Paragraph property="text-red-600">{error}</Paragraph>
            ) : (
                <Container property="grid gap-8">
                    {/* INVITATIONS SECTION */}
                    <Container>
                        <Headings sizeTag="h3" property="mb-4 text-blue-600">
                            {t('internships.company_invitations')}
                        </Headings>
                        {data.employer_invitations && data.employer_invitations.length > 0 ? (
                            <Container property="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {data.employer_invitations.map((inv) => (
                                    <StudentInvitationCard
                                        key={inv.invitation_id}
                                        entity={inv}
                                        onResponse={fetchData}
                                    />
                                ))}
                            </Container>
                        ) : (
                            <Paragraph property="text-gray-500 italic">
                                {t('internships.no_invitations_pending')}
                            </Paragraph>
                        )}
                    </Container>

                    {/* APPLICATIONS SECTION */}
                    <Container>
                        <Headings sizeTag="h3" property="mb-4">
                            {t('nav.my_applications')}
                        </Headings>
                        {data.student_practices && data.student_practices.length > 0 ? (
                            <Container property="grid grid-cols-1 md:grid-cols-2 gap-4">
                                {data.student_practices.map((app) => (
                                    <StudentApplicationCard
                                        key={app.student_practice_id}
                                        entity={app}
                                    />
                                ))}
                            </Container>
                        ) : (
                            <Paragraph property="text-gray-500 italic">
                                {t('internships.no_applications')}
                            </Paragraph>
                        )}
                    </Container>
                </Container>
            )}
        </Container>
    );
}
