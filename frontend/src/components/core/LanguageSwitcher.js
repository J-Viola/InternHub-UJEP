import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import Container from '@core/Container/Container';
import { FaGlobe } from 'react-icons/fa';
import { FaAngleDown } from 'react-icons/fa';

export default function LanguageSwitcher() {
  const { i18n } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  const languages = [
    { code: 'cs', label: 'Čeština', flag: '🇨🇿' },
    { code: 'en', label: 'English', flag: '🇬🇧' }
  ];

  const currentLanguage = languages.find(l => l.code === i18n.language) || languages[0];

  const changeLanguage = (lng) => {
    i18n.changeLanguage(lng);
    setIsOpen(false);
  };

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  return (
    <Container property="relative inline-block" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-2 text-white bg-white bg-opacity-10 hover:bg-opacity-20 rounded-lg transition-all border border-white border-opacity-20"
      >
        <span>{currentLanguage.flag}</span>
        <span className="hidden sm:inline font-medium">{currentLanguage.code.toUpperCase()}</span>
        <FaAngleDown className={`transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} size={12} />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 py-2 w-40 bg-white rounded-xl shadow-xl z-[100] border border-gray-100 overflow-hidden animate-in fade-in zoom-in duration-200">
          {languages.map((lang) => (
            <button
              key={lang.code}
              onClick={() => changeLanguage(lang.code)}
              className={`w-full flex items-center gap-3 px-4 py-2 text-left hover:bg-gray-50 transition-colors ${
                i18n.language === lang.code ? 'text-facultyCol font-bold bg-gray-50' : 'text-gray-700'
              }`}
            >
              <span className="text-xl">{lang.flag}</span>
              <span>{lang.label}</span>
            </button>
          ))}
        </div>
      )}
    </Container>
  );
}
