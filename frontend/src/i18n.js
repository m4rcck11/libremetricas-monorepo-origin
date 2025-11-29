import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import HttpApi from 'i18next-http-backend';

i18n
.use(initReactI18next) // Passa a instância do i18n para o react-i18next.
.use(LanguageDetector) // Detecta o idioma do usuário.
.use(HttpApi) // Permite carregar traduções de um servidor.
.init({
    supportedLngs: ['pt', 'en', 'es'],
    fallbackLng: 'pt',
    detection: {
        order: ['cookie', 'htmlTag', 'localStorage', 'path', 'subdomain'],
      caches: ['cookie'],
    },
    backend: {
        loadPath: '/locales/{{lng}}/translation.json',
    },
    react: {
        useSuspense: false,
    },
});

export default i18n;
