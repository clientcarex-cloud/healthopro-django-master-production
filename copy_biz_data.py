from django.core.exceptions import ObjectDoesNotExist
from django.forms import model_to_dict
from django_tenants.utils import schema_context
from psycopg2 import sql
from healtho_pro import settings
import psycopg2
from django.conf import settings

from healtho_pro_user.models.business_models import BusinessProfiles
from healtho_pro_user.models.users_models import Client
from pro_laboratory.models.client_based_settings_models import BusinessDataStatus
from pro_laboratory.models.global_models import LabFixedParametersReportTemplate, LabFixedReportNormalReferralRanges
from pro_universal_data.models import ULabReportsGender, ULabPatientAge

'''
Logic:  After creation of account, we will get req. departments from user
The departments will be copied from source, and then for each department, tests will be copied.
labreporttemplates and then the parameters will be copied next...
'''


def copy_biz_data(old_schema, new_schema, department_list):
    try:
        # Connect to the PostgreSQL database
        conn = psycopg2.connect(
            dbname=settings.DATABASES['default']['NAME'],
            user=settings.DATABASES['default']['USER'],
            password=settings.DATABASES['default']['PASSWORD'],
            host=settings.DATABASES['default']['HOST'],
            port=settings.DATABASES['default']['PORT']
        )
        cursor = conn.cursor()

    except Exception as error:
        print(error)
        pass

    try:
        table = 'pro_laboratory_labdepartments'

        for name in department_list:
            # Check if the department already exists in the target schema
            cursor.execute(f'''SELECT 1 FROM "{new_schema}".pro_laboratory_labdepartments WHERE name ='{name}' ''')

            if cursor.fetchone():
                print(f"Department '{name}' already exists in the target schema. Skipping.")
                continue

            # Copying Departments
            # Get all columns except 'id' for the department table
            cursor.execute(f'''
                           SELECT column_name
                           FROM information_schema.columns
                           WHERE table_schema = '{old_schema}'
                           AND table_name = 'pro_laboratory_labdepartments'
                           AND column_name NOT IN ('id')
                            ''')
            columns = [f'"{row[0]}"' for row in cursor.fetchall()]
            columns_str = ', '.join(columns)
            print(columns)
            print(columns_str)

            cursor.execute(f'''
                            INSERT INTO "{new_schema}".pro_laboratory_labdepartments ({columns_str})
                            SELECT {columns_str} FROM "{old_schema}".pro_laboratory_labdepartments 
                            WHERE name ='{name}'
                            '''
                           )

            print(f"Copied department '{name}' to the target schema.")

            # Copying LabGlobaltests
            # Retrieve all column names from pro_laboratory_labglobaltests
            cursor.execute(f'''
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_name = 'pro_laboratory_labglobaltests'
                            AND table_schema = '{old_schema}'
                            AND column_name NOT IN ('id','department_id')
                            '''
                           )
            columns = [f'"{row[0]}"' for row in cursor.fetchall()]
            columns_str = ', '.join(columns)

            cursor.execute(f'''
                            INSERT INTO "{new_schema}".pro_laboratory_labglobaltests ("department_id",{columns_str})
                            SELECT (SELECT id FROM "{new_schema}".pro_laboratory_labdepartments WHERE name = '{name}'), {columns_str} FROM "{old_schema}".pro_laboratory_labglobaltests
                            WHERE department_id = (
                                SELECT id FROM "{old_schema}".pro_laboratory_labdepartments WHERE name = '{name}'
                            )
                            ''')
            print(f"Copied labglobaltests of department '{name}' to the target schema.")

            # Copying labreportstemplate
            # Retrieve all column names from pro_laboratory_labreportstemplates
            cursor.execute(f'''
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_name = 'pro_laboratory_labreportstemplates'
                            AND table_schema = '{old_schema}'
                            AND column_name NOT IN ('id','department_id','LabGlobalTestID_id')
                            '''
                           )
            columns = [f'"{row[0]}"' for row in cursor.fetchall()]
            print(columns)
            columns_str = ', '.join(columns)
            print(columns_str)

            cursor.execute(f'''
                            INSERT INTO "{new_schema}".pro_laboratory_labreportstemplates ("department_id","LabGlobalTestID_id",{columns_str})
                            SELECT (SELECT id FROM "{new_schema}".pro_laboratory_labdepartments WHERE name = '{name}'),                            
                                   (SELECT id FROM "{new_schema}".pro_laboratory_labglobaltests WHERE name = (SELECT name FROM "{old_schema}".pro_laboratory_labglobaltests WHERE id="LabGlobalTestID_id")),
                                    {columns_str} FROM "{old_schema}".pro_laboratory_labreportstemplates
                            WHERE department_id = (
                                SELECT id FROM "{old_schema}".pro_laboratory_labdepartments WHERE name = '{name}'
                            )
                            ''')

            print(f"Copied pro_laboratory_labreportstemplates of department '{name}' to the target schema.")

            # Copying LabFixedReportParameters
            # Retrieve all column names from pro_laboratory_labfixedreportparameters
            cursor.execute(f'''
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_name = 'pro_laboratory_labfixedparametersreporttemplate'
                            AND table_schema = '{old_schema}'
                            AND column_name NOT IN ('id','department_id','LabReportsTemplate_id')
                            '''
                           )
            columns = [f'"{row[0]}"' for row in cursor.fetchall()]
            columns_str = ', '.join(columns)

            cursor.execute(f'''
                            INSERT INTO "{new_schema}".pro_laboratory_labfixedparametersreporttemplate ("department_id","LabReportsTemplate_id",{columns_str})
                            SELECT (SELECT id FROM "{new_schema}".pro_laboratory_labdepartments WHERE name = '{name}'),
                                   (SELECT id FROM "{new_schema}".pro_laboratory_labreportstemplates WHERE name = (SELECT name FROM "{old_schema}".pro_laboratory_labreportstemplates WHERE id="LabReportsTemplate_id")),
                                    {columns_str} FROM "{old_schema}".pro_laboratory_labfixedparametersreporttemplate
                            WHERE department_id = (
                                SELECT id FROM "{old_schema}".pro_laboratory_labdepartments WHERE name = '{name}'
                            )
                            ''')

            print(f"Copied pro_laboratory_labfixedreportparameters of department '{name}' to the target schema.")


            # LabWordReportTemplate
            # Retrieve all column names from pro_laboratory_labwordreporttemplate
            cursor.execute(f'''
                                        SELECT column_name
                                        FROM information_schema.columns
                                        WHERE table_name = 'pro_laboratory_labwordreporttemplate'
                                        AND table_schema = '{old_schema}'
                                        AND column_name NOT IN ('id','department_id','LabReportsTemplate_id')
                                        ''')

            columns = [f'"{row[0]}"' for row in cursor.fetchall()]
            columns_str = ', '.join(columns)

            cursor.execute(f'''
                                INSERT INTO "{new_schema}".pro_laboratory_labwordreporttemplate ("department_id","LabReportsTemplate_id",{columns_str})
                                SELECT (SELECT id FROM "{new_schema}".pro_laboratory_labdepartments WHERE name = '{name}'),
                                       (SELECT id FROM "{new_schema}".pro_laboratory_labreportstemplates WHERE name = (SELECT name FROM "{old_schema}".pro_laboratory_labreportstemplates WHERE id="LabReportsTemplate_id")),
                                        {columns_str} FROM "{old_schema}".pro_laboratory_labwordreporttemplate
                                WHERE department_id = (
                                    SELECT id FROM "{old_schema}".pro_laboratory_labdepartments WHERE name = '{name}'
                                )
                                ''')

            print(f"Copied pro_laboratory_labwordreporttemplate of department '{name}' to the target schema.")

        # Commit the transaction
        conn.commit()


    except psycopg2.Error as e:
        print(f"Error: {e}")
        conn.rollback()

    finally:
        # Close the cursor and connection
        cursor.close()
        conn.close()

    try:
        for name in department_list:
            with schema_context(old_schema):
                old_fix_params = LabFixedParametersReportTemplate.objects.filter(department__name=f'{name}')
                print(old_fix_params)
                for old_fix_param in old_fix_params:
                    print(old_fix_param)
                    normal_ranges = LabFixedReportNormalReferralRanges.objects.filter(parameter_id=old_fix_param)

                    if normal_ranges.exists():
                        print('ok')
                        normal_ranges_data_list = []
                        for normal_range in normal_ranges:
                            normal_range_data = model_to_dict(normal_range)
                            normal_ranges_data_list.append(normal_range_data)

                        if normal_ranges_data_list:
                            template_name = old_fix_param.LabReportsTemplate.name
                            parameter = old_fix_param.parameter
                            print(template_name, parameter)

                            with schema_context(new_schema):
                                print(new_schema, name, template_name, parameter)
                                new_fixed_param = LabFixedParametersReportTemplate.objects.filter(
                                    department__name=f'{name}',
                                    LabReportsTemplate__name=template_name,
                                    parameter=parameter
                                ).first()

                                if new_fixed_param:
                                    ranges_to_create = []

                                    for normal_ranges_data in normal_ranges_data_list:
                                        try:
                                            gender = ULabReportsGender.objects.get(pk=normal_ranges_data['gender'])
                                            age_min_units = ULabPatientAge.objects.get(
                                                pk=normal_ranges_data['age_min_units'])
                                            age_max_units = ULabPatientAge.objects.get(
                                                pk=normal_ranges_data['age_max_units'])

                                            new_range = LabFixedReportNormalReferralRanges(
                                                parameter_id=new_fixed_param,
                                                gender=gender,
                                                age_min=normal_ranges_data['age_min'],
                                                age_min_units=age_min_units,
                                                age_min_in_days=normal_ranges_data['age_min_in_days'],
                                                age_max=normal_ranges_data['age_max'],
                                                age_max_units=age_max_units,
                                                age_max_in_days=normal_ranges_data['age_max_in_days'],
                                                value_min=normal_ranges_data['value_min'],
                                                value_max=normal_ranges_data['value_max']
                                            )
                                            ranges_to_create.append(new_range)
                                        except ObjectDoesNotExist as e:
                                            print(f"Data missing for: {e}")

                                    if ranges_to_create:
                                        print('creating')
                                        LabFixedReportNormalReferralRanges.objects.bulk_create(ranges_to_create)
                                        print(f'{len(ranges_to_create)} ranges created for {new_fixed_param}')

                                else:
                                    print(
                                        f"No matching parameter found in new schema for {template_name} and {parameter}")

    except Exception as error:
        print(f"Error occurred: {error}")
        conn.rollback()

    try:
        conn = psycopg2.connect(
            dbname=settings.DATABASES['default']['NAME'],
            user=settings.DATABASES['default']['USER'],
            password=settings.DATABASES['default']['PASSWORD'],
            host=settings.DATABASES['default']['HOST'],
            port=settings.DATABASES['default']['PORT']
        )
        cursor = conn.cursor()

    except Exception as error:
        print(error)
        pass

    try:
        mandatory_tables_to_copy = ['pro_laboratory_printtemplate',
                                    'pro_laboratory_printdatatemplate',
                                    'pro_laboratory_labdoctorstype']

        tables_to_copy = ['pro_laboratory_labdepartments', 'pro_laboratory_labglobaltests',
                          'pro_laboratory_labreportstemplates',
                          'pro_laboratory_labfixedparametersreporttemplate',
                          'pro_laboratory_labfixedreportnormalreferralranges',
                          'pro_laboratory_labwordreporttemplate',
                          'pro_laboratory_printtemplate',
                          'pro_laboratory_printdatatemplate',
                          'pro_laboratory_labdoctorstype']

        with schema_context(new_schema):
            business_data_status = BusinessDataStatus.objects.get(client__schema_name=new_schema)
            if not business_data_status.is_data_imported:
                for table in mandatory_tables_to_copy:
                    print(table)
                    cursor.execute(f'''
                                    SELECT column_name FROM information_schema.columns 
                                    WHERE table_name = '{table}' AND table_schema = '{old_schema}'

                                    ''')

                    columns = [f'"{row[0]}"' for row in cursor.fetchall()]
                    columns_str = ', '.join(columns)

                    cursor.execute(f'''
                                INSERT INTO "{new_schema}"."{table}" ({columns_str})
                                SELECT {columns_str} FROM "{old_schema}"."{table}" 
                                '''
                                   )
                    # conn.commit()

            for table in tables_to_copy:
                sequence_name = f'"{new_schema}"."{table}_id_seq"'
                # print(sequence_name)
                cursor.execute(
                    f"SELECT setval('{sequence_name}', (SELECT MAX(id) FROM \"{new_schema}\".\"{table}\"))"
                )

        # Commit the transaction
        conn.commit()
    except Exception as error:
        print(error)
        pass

    finally:
        try:
            with schema_context(new_schema):
                client = Client.objects.get(schema_name=new_schema)
                # print(client)
                b_id = BusinessProfiles.objects.get(organization_name=client.name)
                # print(b_id)
                business_data_status, created = BusinessDataStatus.objects.get_or_create(client=client, b_id=b_id)
                if not business_data_status.is_data_imported:
                    business_data_status.is_data_imported = True
                    business_data_status.save()
            cursor.close()
            conn.close()
        except Exception as error:
            print(error)
            cursor.close()
            conn.close()


# copy_biz_data("HealthOProSupport", "PreranaDiagnostic", ["ULTRASOUND","CLINICAL BIOCHEMISTRY","SEROLOGY","HISTOPATHOLOGY","CLINICAL PATHOLOGY","HAEMATOLOGY","MICROBIOLOGY","IMMUNOLOGY SEROLOGY","GYNECOLOGY","CYTOLOGY"])


# copy_biz_data("HealthOProAdmin", "EagleLabs", ["BIOCHEMISTRY","CLINICAL PATHOLOGY","CYTOPATHOLOGY","GENETICS AND MOLECULAR MEDICINE","HAEMATOLOGY","HISTOPATHOLOGY","IMMUNO-HEMATOLOGY","IMMUNOLOGY / SEROLOGY","MARKERS","MICROBIOLOGY", "MOLECULAR BIOLOGY","PATHOLOGY","ULTRASOUND"])
# ["GENETICS AND MOLECULAR MEDICINE","IMMUNO-HEMATOLOGY","BIOCHEMISTRY","MARKERS","PATHOLOGY","CYTOPATHOLOGY"])

