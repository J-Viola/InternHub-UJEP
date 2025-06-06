// https://medium.com/@shruti.latthe/creating-a-centralized-api-client-file-in-react-with-axios-5e69dc27fdb1

import axios from 'axios';
//USECONTEXT TOKENY (AUTHCONTEXT) <- IMPORT


if (process.env.REACT_APP_API_URL) {
    console.log("ENV URL JE NAČTENA:", process.env.REACT_APP_API_URL);
}

const BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
console.log("API URL:", BASE_URL);

const apiClient = axios.create({
    baseURL: BASE_URL,
    headers: {
      'Content-Type': 'application/json',
      // TOKEN ZDE - DODĚLAT CHECK
    },
  });


// CONFIG => pokud nebude empty, tak vytvoří novou instanci apiClienta s config v headers
const _get = (url, config = {}) => {
return apiClient.get(url, config);
};

const _delete = (url, config = {}) => {
return apiClient.delete(url, config);
};

const _put = (url, data = {}, config = {}) => {
return apiClient.put(url, data, config);
};

const _post = (url, data = {}, config = {}) => {
return apiClient.post(url, data, config);
};

export { _get, _delete, _put, _post };