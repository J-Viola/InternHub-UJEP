import { getApiErrorMessage } from './apiErrorUtils';

const makeError = ({ code, details, responseData }) => {
    const err = new Error('api error');
    if (code) err.code = code;
    if (details !== undefined) err.details = details;
    if (responseData !== undefined) err.responseData = responseData;
    return err;
};

describe('getApiErrorMessage — BL-04 error surfacing', () => {
    test('český text z error_code má přednost před fallbackem', () => {
        const error = makeError({
            code: 'CAPACITY_FULL',
            details: 'Kapacita partnera je plně obsazena',
        });
        expect(getApiErrorMessage(error, 'Došlo k chybě při podání přihlášky.')).toBe(
            'Kapacita partnera je plně obsazena'
        );
    });

    test('token místo textu (apply/reapply) → fallback stránky', () => {
        const error = makeError({
            code: 'DRF_ERROR',
            details: 'CAPACITY_FULL',
            responseData: { detail: 'CAPACITY_FULL' },
        });
        expect(getApiErrorMessage(error, 'Došlo k chybě při podání přihlášky.')).toBe(
            'Došlo k chybě při podání přihlášky.'
        );

        const reapplyError = makeError({
            code: 'DRF_ERROR',
            details: 'KAPACITA_NAPLNENA',
            responseData: { detail: 'KAPACITA_NAPLNENA' },
        });
        expect(getApiErrorMessage(reapplyError, 'Chyba při opětovném přihlašování na praxi')).toBe(
            'Chyba při opětovném přihlašování na praxi'
        );
    });

    test('česká věta ze serveru se zobrazí přímo', () => {
        const error = makeError({
            code: 'DRF_ERROR',
            details: 'Storno je již vyřešeno.',
        });
        expect(getApiErrorMessage(error, 'Storno se nepodařilo vzít na vědomí')).toBe(
            'Storno je již vyřešeno.'
        );
    });

    test('token bez textu → fallback stránky', () => {
        const error = makeError({ code: 'DRF_ERROR', details: 'NEJAKY_TOKEN_XYZ' });
        expect(getApiErrorMessage(error, 'Došlo k chybě při podání přihlášky.')).toBe(
            'Došlo k chybě při podání přihlášky.'
        );
    });

    test('bez detailu i fallbacku → obecná hláška', () => {
        expect(getApiErrorMessage({}, 'Chyba při zamítání')).toBe('Chyba při zamítání');
        expect(getApiErrorMessage(undefined, 'Chyba při zamítání')).toBe('Chyba při zamítání');
        expect(getApiErrorMessage({ code: 'DRF_ERROR' }, undefined)).toBe(
            'Došlo k neočekávané chybě serveru.'
        );
    });
});
