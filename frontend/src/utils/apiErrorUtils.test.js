import { getApiErrorMessage } from './apiErrorUtils';
import translations from '../../public/locales/cs/translation.json';

const resolve = (obj, key) =>
    key.split('.').reduce((acc, part) => (acc && typeof acc === 'object' ? acc[part] : undefined), obj);

// simulace i18next: chybějící klíč se vrací jako klíč (stejně jako mocky v RTL)
const t = (key) => resolve(translations, key) ?? key;

const makeError = ({ code, details, responseData }) => {
    const err = new Error('api error');
    if (code) err.code = code;
    if (details !== undefined) err.details = details;
    if (responseData !== undefined) err.responseData = responseData;
    return err;
};

describe('getApiErrorMessage — BL-04 error surfacing', () => {
    test('capacity chyba přes error_code (transition/confirm) → česká hláška', () => {
        const error = makeError({
            code: 'CAPACITY_FULL',
            details: 'Kapacita partnera je plně obsazena',
        });
        expect(getApiErrorMessage(error, t, 'practice_detail.apply_error')).toBe(
            'Kapacita partnera je plně obsazena.'
        );
    });

    test('capacity chyba jako detail token (apply/reapply) → přeložený token', () => {
        const error = makeError({
            code: 'DRF_ERROR',
            details: 'CAPACITY_FULL',
            responseData: { detail: 'CAPACITY_FULL' },
        });
        expect(getApiErrorMessage(error, t, 'practice_detail.apply_error')).toBe(
            'Kapacita partnera je plně obsazena.'
        );

        const reapplyError = makeError({
            code: 'DRF_ERROR',
            details: 'KAPACITA_NAPLNENA',
            responseData: { detail: 'KAPACITA_NAPLNENA' },
        });
        expect(getApiErrorMessage(reapplyError, t, 'practice_detail.reapply_error')).toBe(
            'Kapacita partnera je plně obsazena.'
        );
    });

    test('serverová věta se zobrazí přímo (žádný generický překlad)', () => {
        const error = makeError({
            code: 'DRF_ERROR',
            details: 'Pro rozhodnutí o žádosti o storno je povinné pole decision=approve|reject.',
        });
        expect(getApiErrorMessage(error, t, 'practice_detail.cancellation_resolve_error')).toBe(
            'Pro rozhodnutí o žádosti o storno je povinné pole decision=approve|reject.'
        );
    });

    test('token bez překladu → fallback klíč', () => {
        const error = makeError({ code: 'DRF_ERROR', details: 'NEJAKY_TOKEN_XYZ' });
        expect(getApiErrorMessage(error, t, 'practice_detail.apply_error')).toBe(
            'Došlo k chybě při podání přihlášky.'
        );
    });

    test('bez kódu i detailu → fallback klíč; bez erroru také', () => {
        expect(getApiErrorMessage({}, t, 'practice_detail.reject_error')).toBe('Chyba při zamítání');
        expect(getApiErrorMessage(undefined, t, 'practice_detail.reject_error')).toBe(
            'Chyba při zamítání'
        );
        expect(getApiErrorMessage({ code: 'DRF_ERROR' }, t, undefined)).toBe(
            'Chyba při komunikaci se serverem.'
        );
    });
});
