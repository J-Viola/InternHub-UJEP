import React from 'react';

const useTranslation = () => ({
  t: (key) => key,
  i18n: {
    changeLanguage: () => new Promise(() => {}),
    language: 'cs',
  },
});

const Trans = ({ children }) => children;

const initReactI18next = {
  type: '3rdParty',
  init: () => {},
};

export {
  useTranslation,
  Trans,
  initReactI18next,
};
