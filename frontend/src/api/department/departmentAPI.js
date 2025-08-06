import { useApi } from "@hooks/useApi";
import { useMessage } from "@hooks/MessageContext";

// Dummy data pro katedry
const dummyDepartments = [
    {
        "department_id": 1,
        "department_name": "Katedra informatiky",
        "description": "Katedra zaměřená na informatiku a počítačové vědy",
        "head_of_department": "RNDr. Petr Ztracený"
    },
    {
        "department_id": 2,
        "department_name": "Katedra matematiky",
        "description": "Katedra zaměřená na matematiku a její aplikace",
        "head_of_department": "Prof. Ing. Jan Novák"
    },
    {
        "department_id": 3,
        "department_name": "Katedra fyziky",
        "description": "Katedra zaměřená na fyziku a fyzikální experimenty",
        "head_of_department": "Doc. RNDr. Marie Svobodová"
    }
];

export const useDepartmentAPI = () => {
    const api = useApi();

    // CRUD operace pro katedry s dummy daty
    const getAllDepartments = async () => {
        return dummyDepartments;
    };

    const getDepartmentById = async (id) => {
        return dummyDepartments.find(dept => dept.department_id == id) || null;
    };

    const createDepartment = async (departmentData) => {
        const newDepartment = {
            department_id: Math.max(...dummyDepartments.map(d => d.department_id)) + 1,
            ...departmentData
        };
        dummyDepartments.push(newDepartment);
        return newDepartment;
    };

    const updateDepartment = async (id, departmentData) => {
        const index = dummyDepartments.findIndex(dept => dept.department_id == id);
        if (index !== -1) {
            dummyDepartments[index] = {
                department_id: parseInt(id),
                ...departmentData
            };
            return dummyDepartments[index];
        }
        return null;
    };

    const deleteDepartment = async (id) => {
        const index = dummyDepartments.findIndex(dept => dept.department_id == id);
        if (index !== -1) {
            dummyDepartments.splice(index, 1);
            return true;
        }
        return false;
    };

    return {
        getAllDepartments,
        getDepartmentById,
        createDepartment,
        updateDepartment,
        deleteDepartment,
    };
};