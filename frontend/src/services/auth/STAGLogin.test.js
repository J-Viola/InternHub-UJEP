import { getParams } from './STAGLogin';

function setUrl(search) {
    window.history.replaceState({}, '', `/${search}`);
}

describe('STAGLogin getParams', () => {
    afterEach(() => {
        sessionStorage.clear();
        setUrl('');
    });

    test('přijme ticket i bez vráceného state (reálný STAG state nevrací)', () => {
        sessionStorage.setItem('stag_oauth_state', 'nonce-1');
        setUrl('?stagUserTicket=ticket-1');

        expect(getParams()).toEqual({ service_ticket: 'ticket-1' });
        expect(sessionStorage.getItem('stag_oauth_state')).toBeNull();
    });

    test('přijme ticket se shodným state', () => {
        sessionStorage.setItem('stag_oauth_state', 'nonce-1');
        setUrl('?stagUserTicket=ticket-1&state=nonce-1');

        expect(getParams()).toEqual({ service_ticket: 'ticket-1' });
    });

    test('odmítne ticket s cizím state', () => {
        sessionStorage.setItem('stag_oauth_state', 'nonce-1');
        setUrl('?stagUserTicket=ticket-1&state=nonce-2');

        expect(getParams()).toBeNull();
    });

    test('dekóduje stagUserInfo z redirectu', () => {
        const info = { email: 'jan.novak@ujep.cz', stagUserInfo: [{ role: 'ST' }] };
        setUrl(`?stagUserTicket=ticket-1&stagUserInfo=${btoa(JSON.stringify(info))}`);

        expect(getParams()).toEqual({ service_ticket: 'ticket-1', stag_user_info: info });
    });

    test('bez ticketu vrací null', () => {
        setUrl('?foo=bar');

        expect(getParams()).toBeNull();
    });
});
