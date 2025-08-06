import { useApi } from "@hooks/useApi";
import { useMessage } from "@hooks/MessageContext";

// Dummy data pro společnosti
const dummyCompanies = [
    {
        "company_id": 1,
        "company_name": "Microsoft Czech Republic",
        "ico": "1619",
        "dic": "CZ1619",
        "address": "Vyskočilova 1561/4a, 140 00 Praha 4",
        "zip_code": 14000,
        "company_profile": "Microsoft je globální technologická společnost zaměřená na vývoj, výrobu, licencování, podporu a prodej počítačového softwaru, spotřební elektroniky, osobních počítačů a souvisejících služeb.",
        "approval_status": 1,
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/Microsoft_logo.svg/2048px-Microsoft_logo.svg.png"
    },
    {
        "company_id": 2,
        "company_name": "Google Czech Republic",
        "ico": "2724",
        "dic": "CZ2724",
        "address": "Václavské náměstí 11, 110 00 Praha 1",
        "zip_code": 11000,
        "company_profile": "Google je americká nadnárodní technologická společnost specializující se na internetové služby a produkty, které zahrnují online reklamní technologie, vyhledávač, cloud computing, software a hardware.",
        "approval_status": 1,
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Google_2015_logo.svg/272px-Google_2015_logo.svg.png"
    },
    {
        "company_id": 3,
        "company_name": "Seznam.cz",
        "ico": "2616",
        "dic": "CZ2616",
        "address": "Radlická 3294/10, 150 00 Praha 5",
        "zip_code": 15000,
        "company_profile": "Seznam.cz je český internetový portál a vyhledávač, který poskytuje řadu online služeb včetně vyhledávání, emailu, map, zpráv a dalších.",
        "approval_status": 1,
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Seznam.cz_logo.svg/1200px-Seznam.cz_logo.svg.png"
    }
];

export const useCompanyAPI = () => {
    const api = useApi();

    // CRUD operace pro společnosti s dummy daty
    const getAllCompanies = async () => {
        return dummyCompanies;
    };

    const getCompanyById = async (id) => {
        return dummyCompanies.find(company => company.company_id == id) || null;
    };

    const createCompany = async (companyData) => {
        const newCompany = {
            company_id: Math.max(...dummyCompanies.map(c => c.company_id)) + 1,
            approval_status: 1,
            ...companyData
        };
        dummyCompanies.push(newCompany);
        return newCompany;
    };

    const updateCompany = async (id, companyData) => {
        const index = dummyCompanies.findIndex(company => company.company_id == id);
        if (index !== -1) {
            dummyCompanies[index] = {
                company_id: parseInt(id),
                approval_status: dummyCompanies[index].approval_status,
                ...companyData
            };
            return dummyCompanies[index];
        }
        return null;
    };

    const deleteCompany = async (id) => {
        const index = dummyCompanies.findIndex(company => company.company_id == id);
        if (index !== -1) {
            dummyCompanies.splice(index, 1);
            return true;
        }
        return false;
    };

    return {
        getAllCompanies,
        getCompanyById,
        createCompany,
        updateCompany,
        deleteCompany,
    };
}; 