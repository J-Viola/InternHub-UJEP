// zde bude switch podle paramu na příslušný formulář - tohle bude sloužit pro založení předmětů, organizačních účtů atd..
import React from "react";
import Container from "@core/Container/Container";
import BackButton from "@core/Button/BackButton";
import { useUserAPI } from "src/api/user/userAPI";
import { useSubjectAPI } from "src/api/subject/subjectAPI";
import { useDepartmentAPI } from "src/api/department/departmentAPI";
import { useCompanyAPI } from "src/api/company/companyAPI";
import { useEmployerAPI } from "src/api/employer/employerAPI";
import { Navigate, useNavigate, useSearchParams } from "react-router-dom";
import Paragraph from "@components/core/Text/Paragraph";
import SubjectForm from "@components/Forms/SubjectForm";
import UserForm from "@components/Forms/UserForm";
import DepartmentForm from "@components/Forms/DepartmentForm";
import CompanyForm from "@components/Forms/CompanyForm";
import EmployerForm from "@components/Forms/EmployerForm";
import ProfessorForm from "@components/Forms/ProfessorForm";
import { useMessage } from "@hooks/MessageContext";
import { useUser } from "@hooks/UserProvider";

export default function FormPage() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { user } = useUser();
    const { addMessage } = useMessage();

    // API hooks
    const subjectAPI = useSubjectAPI();
    const userAPI = useUserAPI();
    const departmentAPI = useDepartmentAPI();
    const companyAPI = useCompanyAPI();
    const employerAPI = useEmployerAPI();

    const getErrorMessage = (error) => {
        if (error?.response?.data?.detail) {
            return error.response.data.detail;
        }
        if (error?.response?.data && typeof error.response.data === "object") {
            const firstError = Object.values(error.response.data)[0];
            if (Array.isArray(firstError)) return firstError[0];
            if (typeof firstError === "string") return firstError;
        }
        return "Chyba při ukládání";
    };

    const handleCreate = (createApi) => async (data) => {
        try {
            await createApi(data);
            navigate(-1); // Go back to previous page
        } catch (error) {
            addMessage(getErrorMessage(error), "E");
        }
    };

    const handleUpdate = (updateApi, id) => async (data) => {
        try {
            await updateApi(id, data);
            navigate(-1); // Go back to previous page
        } catch (error) {
            addMessage(getErrorMessage(error), "E");
        }
    };

    const renderForm = () => {
        const type = searchParams.get('type');
        // F-31: administrativní formuláře nesmí otevřít běžný uživatel (backend je chrání,
        // zde jen UI, aby student neviděl formulář pro správu předmětů/kateder).
        // F-31: každý typ formuláře má jiný okruh rolí (nejde jen o studenty).
        const formTypeAllowed = {
            subject: () => user?.isDepartmentUser?.() || user?.isAdmin?.(),
            department: () => user?.isAdmin?.(),
            department_users: () => user?.isDepartmentMg?.() || user?.isAdmin?.(),
            employer: () => user?.isAdmin?.(),
            org_users: () => user?.isOrganizationUser?.() || user?.isAdmin?.(),
            org_form: () => user?.isOrganizationUser?.() || user?.isAdmin?.(),
        };
        const allowed = formTypeAllowed[type];
        if (type && allowed && !allowed()) {
            return <Navigate to="/forbidden" replace />;
        }
        const action = searchParams.get('action');
        const id = searchParams.get('id');

        switch(type) {
            case 'subject':
                return (
                    <SubjectForm
                        handleCreate={handleCreate(subjectAPI.createSubject)}
                        handleUpdate={handleUpdate(subjectAPI.updateSubject, id)}
                        action={action}
                        id={id}
                    />
                );
            case 'org_users':
                return (
                    <UserForm
                        organizationUser={true}
                        action={action}
                        id={id}
                        handleCreate={handleCreate(userAPI.createUser)}
                        handleUpdate={handleUpdate(userAPI.updateUser, id)}
                    />
                );
            case 'department_users':
                return (
                    <ProfessorForm
                        action={action}
                        id={id}
                        handleCreate={() => console.log("Create not implemented")}
                        handleUpdate={handleUpdate(departmentAPI.updateProfessor, id)}
                    />
                );
            case 'department':
                return (
                    <DepartmentForm
                        handleCreate={handleCreate(departmentAPI.createDepartment)}
                        handleUpdate={handleUpdate(departmentAPI.updateDepartment, id)}
                        action={action}
                        id={id}
                    />
                );
            case 'org_form':
                return (
                    <CompanyForm
                        handleCreate={handleCreate(companyAPI.createCompany)}
                        handleUpdate={handleUpdate(companyAPI.updateCompany, id)}
                        action={action}
                        id={id}
                    />
                );
            case 'employer':
                return (
                    <EmployerForm
                        handleCreate={handleCreate(employerAPI.createEmployer)}
                        handleUpdate={handleUpdate(employerAPI.updateEmployer, id)}
                        action={action}
                        id={id}
                    />
                );
            default:
                return (
                    <Paragraph>
                        {"Neznámý typ formuláře"}
                        {type ? `: ${type}` : ''}
                    </Paragraph>
                );
        }
    };

    return(
        <>
            <BackButton/>
            <Container property={"bg-white mt-2 p-8 rounded-lg shadow-sm"}>
                {renderForm()}
            </Container>
        </>
    )
}
