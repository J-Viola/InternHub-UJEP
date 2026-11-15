
const STAG_LOGIN_URL = process.env.REACT_APP_STAG_WS_URL || "https://stag-demo.zcu.cz/ws/login";

// originalURL musí mířit na stejný origin, ze kterého se přihlášení spustilo
// (sessionStorage i cookies jsou vázané na origin); build-time proměnná by
// v produkci spadla na localhost.
const ORIGINAL_URL = encodeURIComponent(window.location.origin + "/");
const LOGIN_PARAMS = "?originalURL=" + ORIGINAL_URL;

const API_LOGIN_URL = STAG_LOGIN_URL + LOGIN_PARAMS;

function generateState() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return btoa(String.fromCharCode(...array)).replace(/[+/=]/g, '');
}

export const STAGLogin = () => {
    const state = generateState();
    sessionStorage.setItem('stag_oauth_state', state);
    window.location.href = API_LOGIN_URL + "&state=" + encodeURIComponent(state);
}

export const validateStagState = (urlParams) => {
    const returnedState = urlParams.get('state');
    const savedState = sessionStorage.getItem('stag_oauth_state');
    sessionStorage.removeItem('stag_oauth_state');

    if (returnedState && returnedState !== savedState) {
        return false;
    }

    return true;
}

export const getParams = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const stagUserTicket = urlParams.get('stagUserTicket');
    const stagUserInfoRaw = urlParams.get('stagUserInfo');

    if (stagUserTicket) {
        if (!validateStagState(urlParams)) {
            console.warn("STAG login rejected: invalid state parameter");
            return null;
        }

        const result = { service_ticket: stagUserTicket };
        if (stagUserInfoRaw) {
            try {
                result.stag_user_info = JSON.parse(atob(stagUserInfoRaw));
            } catch {
                console.warn("Error decoding stagUserInfo");
            }
        }
        return result;
    }

    return null;
}
