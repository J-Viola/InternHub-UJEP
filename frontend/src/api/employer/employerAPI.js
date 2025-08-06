import { useApi } from "@hooks/useApi";
import { useMessage } from "@hooks/MessageContext";

// Dummy data pro zaměstnavatele
const dummyEmployers = [
    {
        "employer_id": 1,
        "employer_name": "Microsoft Czech Republic",
        "ico": "1619",
        "dic": "CZ1619",
        "address": "Vyskočilova 1561/4a, 140 00 Praha 4",
        "zip_code": 14000,
        "employer_profile": "Microsoft je globální technologická společnost zaměřená na vývoj, výrobu, licencování, podporu a prodej počítačového softwaru, spotřební elektroniky, osobních počítačů a souvisejících služeb.",
        "approval_status": 1,
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Microsoft_logo.svg/2048px-Microsoft_logo.svg.png"
    },
    {
        "employer_id": 2,
        "employer_name": "Google Czech Republic",
        "ico": "2724",
        "dic": "CZ2724",
        "address": "Václavské náměstí 11, 110 00 Praha 1",
        "zip_code": 11000,
        "employer_profile": "Google je americká nadnárodní technologická společnost specializující se na internetové služby a produkty, které zahrnují online reklamní technologie, vyhledávač, cloud computing, software a hardware.",
        "approval_status": 1,
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Google_2015_logo.svg/272px-Google_2015_logo.svg.png"
    },
    {
        "employer_id": 3,
        "employer_name": "Seznam.cz",
        "ico": "2616",
        "dic": "CZ2616",
        "address": "Radlická 3294/10, 150 00 Praha 5",
        "zip_code": 15000,
        "employer_profile": "Seznam.cz je český internetový portál a vyhledávač, který poskytuje řadu online služeb včetně vyhledávání, emailu, map, zpráv a dalších.",
        "approval_status": 1,
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Seznam.cz_logo.svg/1200px-Seznam.cz_logo.svg.png"
    }
];

export const useEmployerAPI = () => {
    const api = useApi();

    // CRUD operace pro zaměstnavatele s dummy daty
    const getAllEmployers = async () => {
        return dummyEmployers;
    };

    const getEmployerById = async (id) => {
        return dummyEmployers.find(employer => employer.employer_id == id) || null;
    };

    const createEmployer = async (employerData) => {
        const newEmployer = {
            employer_id: Math.max(...dummyEmployers.map(e => e.employer_id)) + 1,
            approval_status: 1,
            ...employerData
        };
        dummyEmployers.push(newEmployer);
        return newEmployer;
    };

    const updateEmployer = async (id, employerData) => {
        const index = dummyEmployers.findIndex(employer => employer.employer_id == id);
        if (index !== -1) {
            dummyEmployers[index] = {
                employer_id: parseInt(id),
                approval_status: dummyEmployers[index].approval_status,
                ...employerData
            };
            return dummyEmployers[index];
        }
        return null;
    };

    const deleteEmployer = async (id) => {
        const index = dummyEmployers.findIndex(employer => employer.employer_id == id);
        if (index !== -1) {
            dummyEmployers.splice(index, 1);
            return true;
        }
        return false;
    };

    return {
        getAllEmployers,
        getEmployerById,
        createEmployer,
        updateEmployer,
        deleteEmployer,
    };
}; 