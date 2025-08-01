
const STAG_LOGIN_URL = "https://stag-demo.zcu.cz/ws/login";
const ORIGINAL_URL = "http%3A%2F%2Fwww.localhost%3A3000%2F";
const LOGIN_PARAMS = "?originalURL=" + ORIGINAL_URL;

const API_LOGIN_URL = STAG_LOGIN_URL + LOGIN_PARAMS;
console.log(API_LOGIN_URL);
/*
https://portal.ujep.cz/ws/login?originalURL=http://www.stag-client.cz
*/

export const STAGLogin = () => {
    window.location.href = API_LOGIN_URL;
}

/*
http://www.localhost:3000/?stagUserTicket=98b837a962a2c5d95b178edf1bfbf754a47f5b5014e455072f7756004ea2693f&stagUserName=f20b0539p&stagUserRole=ST&stagUserInfo=eyJqbWVubyI6Ikthcm9sw61uYSIsInByaWptZW5pIjoiUFVSS0FSVE9Ww4EiLCJlbWFpbCI6IkYyMEIwNTM5UEBzdHVkZW50cy56Y3UuY3oiLCJzdGFnVXNlckluZm8iOlt7InVzZXJOYW1lIjoiRjIwQjA1MzlQIiwicm9sZSI6IlNUIiwicm9sZU5hemV2IjoiU3R1ZGVudCIsImZha3VsdGEiOiJGRiIsIm9zQ2lzbG8iOiJGMjBCMDUzOVAiLCJlbWFpbCI6IkYyMEIwNTM5UEBzdHVkZW50cy56Y3UuY3oifV19
*/

export const getParams = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const stagUserTicket = urlParams.get('stagUserTicket');
    
    if (stagUserTicket) {
        console.log("Nalezen STAG ticket:", stagUserTicket);
        return { service_ticket: stagUserTicket };
    }
    
    console.log("Žádný STAG ticket v URL");
    return null;
}

