import { useApi } from "@hooks/useApi";
import { z } from "zod";

//import { createParams } from "@api/createParams";

const ListPracticeSchema = z.object({
  practice_id: z.number(),
  title: z.string(),
  description: z.string().nullable(),
  employer: z.object({
    company_name: z.string().nullable(),
  }),
  start_date: z.string().nullable(),
  end_date: z.string().nullable(),
  image_base64: z.string().nullable(),
  // add other fields you care about…
});

const NabidkyListResponseSchema = z.object({
  count: z.number(),
  next: z.string().nullable(),
  previous: z.string().nullable(),
  results: z.array(ListPracticeSchema),
});

const StatusSchema = z.object({
  status_id: z.number(),
  status_code: z.string(),
  status_name: z.string(),
  status_category: z.string(),
  description: z.string(),
});

const DepartmentSchema = z.object({
  department_id: z.number(),
  department_name: z.string(),
  description: z.string(),
});

const SubjectSchema = z.object({
  subject_id: z.number(),
  subject_code: z.string(),
  subject_name: z.string(),
  department: DepartmentSchema,
  hours_required: z.number(),
});

const EmployerSchema = z.object({
  employer_id: z.number(),
  company_name: z.string(),
  ico: z.string(),
  dic: z.string(),
  address: z.string(),
  company_profile: z.string(),
  approval_status: StatusSchema,
});

const PracticeTypeSchema = z.object({
  practice_type_id: z.number(),
  name: z.string(),
  coefficient: z.number(),
});

const PracticeDetailSchema = z.object({
  practice_id: z.number(),
  employer: EmployerSchema,
  subject: SubjectSchema,
  title: z.string(),
  description: z.string(),
  responsibilities: z.string(),
  available_positions: z.number(),
  start_date: z.string(),
  end_date: z.string(),
  status: StatusSchema,
  approval_status: StatusSchema,
  contact_user_info: z.string(),
  is_active: z.boolean(),
  image_base64: z.string(),
  practice_type: PracticeTypeSchema,
});
const CreatePracticeSchema = z.object({
  employer_id: z.number(),
  subject_id: z.number(),
  status_id: z.number(),
  approval_status_id: z.number(),
  contact_user: z.number(),
  practice_type_id: z.number(),

  title: z.string().max(100).nullable().optional(),
  description: z.string().nullable().optional(),
  responsibilities: z.string().nullable().optional(),
  available_positions: z.number().int().nullable().optional(),
  start_date: z.string().refine((s) => !s || /^\d{4}-\d{2}-\d{2}$/.test(s), {
    message: "Invalid date format, expected YYYY-MM-DD",
  }).nullable().optional(),
  end_date: z.string().refine((s) => !s || /^\d{4}-\d{2}-\d{2}$/.test(s), {
    message: "Invalid date format, expected YYYY-MM-DD",
  }).nullable().optional(),
  image_base64: z.string().nullable().optional(),
});

export const useNabidkaAPI = () => {
    const api = useApi();
    const practices = api.dummyDB.practices;

  const getNabidky = async (params = {}) => {
    try {
      const apiResponse = await api.get("practices/practices", {
        params,
      });
      console.log("apiresponse:", apiResponse.data);
      const parsed = NabidkyListResponseSchema.parse(apiResponse.data);
      let practices = parsed.results;
      console.log("Nabídky:", practices);

       let filteredData = practices;

            if (Object.keys(params).length > 0) {
                filteredData = practices.filter(practice => {
                    return Object.entries(params).every(([key, value]) => {
                        if (practice.hasOwnProperty(key)) {
                            // Pro číselné hodnoty (subject, practice_id, atd.)
                            if (typeof practice[key] === 'number') {
                                return practice[key] === parseInt(value);
                            }
                            // Pro string hodnoty (address, title, atd.)
                            if (typeof value === 'string' && typeof practice[key] === 'string') {
                                return practice[key].toLowerCase().includes(value.toLowerCase());
                            }
                            // Pro ostatní typy
                            return practice[key] === value;
                        }
                        return false;
                    });
                });
            }

      const response = {
        data: filteredData,
      };

      return response.data;
    } catch (error) {
      console.error("Chyba při získávání nabídek:", error);
      throw error;
    }
  };

  const getNabidka = async (id, params = {}) => {
    try {
      const apiResponse = await api.get(`practices/practices/${id}`, {
        params,
      });
      const practice = PracticeDetailSchema.parse(apiResponse.data);
      console.log("Nabídka:", practice);

      const response = {
        data: practice,
      };

      return response.data;
    } catch (error) {
      console.error("Chyba při získávání nabídek:", error);
      throw error;
    }
  };

  const createNabidka = async (data, params = {}) => {
    try {
    const CreatePracticeSchemaWithOptionalFields = CreatePracticeSchema.parse(data);
    const apiResponse = await api.post("practices/practices", CreatePracticeSchemaWithOptionalFields, {
      params,
    });
    console.log("Response:",apiResponse);
    const practice = PracticeDetailSchema.parse(apiResponse.data);
    console.log("Nabídka:", practice);

    return practice;

    } catch (error) {
      console.error("Chyba při získávání nabídek:", error);
      throw error;
    }
  };

  return {
    getNabidky,
    getNabidka,
    createNabidka,
  };
};
