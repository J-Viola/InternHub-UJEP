// zde bude switch podle paramu na příslušný formulář - tohle bude sloužit pro založení předmětů, organizačních účtů atd..
import React from "react";
import Container from "@core/Container/Container";
import BackButton from "@core/Button/BackButton";
import { useUserAPI } from "src/api/user/userAPI";
import { useSubjectAPI } from "src/api/subject/subjectAPI";
import { useDepartmentAPI } from "src/api/department/departmentAPI";
import { useCompanyAPI } from "src/api/company/companyAPI";
import { useEmployerAPI } from "src/api/employer/employerAPI";
import { useNavigate, useSearchParams } from "react-router-dom";
import Paragraph from "@components/core/Text/Paragraph";
import SubjectForm from "@components/Forms/SubjectForm";
import UserForm from "@components/Forms/UserForm";
import DepartmentForm from "@components/Forms/DepartmentForm";
import CompanyForm from "@components/Forms/CompanyForm";
import EmployerForm from "@components/Forms/EmployerForm";
import ProfessorForm from "@components/Forms/ProfessorForm";

export default function FormPage() {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();

    // API hooks
    const subjectAPI = useSubjectAPI();
    const userAPI = useUserAPI();
    const departmentAPI = useDepartmentAPI();
    const companyAPI = useCompanyAPI();
    const employerAPI = useEmployerAPI();

    const handleCreate = (createApi) => async (data) => {
        try {
            await createApi(data);
            navigate(-1); // Go back to previous page
        } catch (error) {
            console.error('Chyba při ukládání:', error);
        }
    };

    const handleUpdate = (updateApi, id) => async (data) => {
        try {
            await updateApi(id, data);
            navigate(-1); // Go back to previous page
        } catch (error) {
            console.error('Chyba při aktualizaci:', error);
        }
    };

    const renderForm = () => {
        const type = searchParams.get('type');
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
                return <Paragraph>Neznámý typ formuláře: {type}</Paragraph>;
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
