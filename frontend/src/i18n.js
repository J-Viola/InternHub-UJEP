import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import Backend from 'i18next-http-backend';

i18n
  .use(Backend)
  .use(initReactI18next)
  .init({
    lng: 'cs',
    fallbackLng: 'cs',
    debug: process.env.NODE_ENV === 'development',

    interpolation: {
      escapeValue: false, // React to dělá za nás
    },

    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    }
  });

export default i18n;
