import React from 'react';
import Container from '@core/Container/Container';
import Paragraph from '@components/core/Text/Paragraph';
import { useTranslation } from 'react-i18next';

export default function Footer() {
    const { t } = useTranslation();
    return (
        <footer className="w-full bg-white border-t border-gray-200 mt-auto">
            <Container property="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                 <div className="flex flex-col md:flex-row justify-between items-center">
                    <Paragraph variant="small" className="text-gray-500">
                        © {new Date().getFullYear()} InternHub UJEP. {t('footer.all_rights_reserved')}
                    </Paragraph>
                    <div className="flex space-x-6 mt-4 md:mt-0">
                         <Paragraph variant="small" className="text-gray-400">{t('footer.support')}: support@ujep.cz</Paragraph>
                    </div>
                 </div>
            </Container>
        </footer>
    );
}
