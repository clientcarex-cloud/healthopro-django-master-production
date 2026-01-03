#command to update seq of a schema


'''
DO $$
DECLARE
    target_schema TEXT := 'HealthSpringDiagnostic'; -- Define schema name here
    rec RECORD;
    seq_exists BOOLEAN;
BEGIN
    FOR rec IN
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = target_schema
    LOOP
        BEGIN
            -- Construct the sequence name based on the table name
            DECLARE
                sequence_name TEXT := format('"%s"."%s_id_seq"', target_schema, rec.table_name);
            BEGIN
                -- Check if the sequence exists
                SELECT EXISTS (
                    SELECT 1
                    FROM pg_class c
                    JOIN pg_namespace n ON n.oid = c.relnamespace
                    WHERE c.relname = format('%s_id_seq', rec.table_name)
                      AND n.nspname = target_schema
                ) INTO seq_exists;

                IF seq_exists THEN
                    -- Update the existing sequence
                    EXECUTE format(
                        'SELECT setval(
                            %L,
                            COALESCE((SELECT MAX(id) FROM "%s".%I), 1),
                            true
                        )',
                        sequence_name,
                        target_schema,
                        rec.table_name
                    );
                    RAISE NOTICE 'Updated sequence for table %', rec.table_name;
                ELSE
                    -- Create the sequence if it does not exist
                    EXECUTE format(
                        'CREATE SEQUENCE "%s".%I_id_seq
                         START 1
                         INCREMENT 1
                         MINVALUE 1
                         NO MAXVALUE
                         CACHE 1',
                        target_schema,
                        rec.table_name
                    );
                    -- Initialize the sequence with the maximum id from the table
                    EXECUTE format(
                        'SELECT setval(
                            %L,
                            COALESCE((SELECT MAX(id) FROM "%s".%I), 1),
                            true
                        )',
                        sequence_name,
                        target_schema,
                        rec.table_name
                    );
                    RAISE NOTICE 'Created and initialized sequence for table %', rec.table_name;
                END IF;

            EXCEPTION
                WHEN OTHERS THEN
                    RAISE NOTICE 'Error processing table %: %', rec.table_name, SQLERRM;
            END;
        END;
    END LOOP;
END $$;

'''

'''
DO $$
DECLARE
    schema_name TEXT;
    insert_sql TEXT;
BEGIN
    -- Loop through all schemas containing the target table
    FOR schema_name IN
        SELECT table_schema
        FROM information_schema.tables
        WHERE table_name = 'pro_laboratory_doctorspecializations'
          AND table_schema NOT IN ('pg_catalog', 'information_schema') -- Exclude system schemas
    LOOP
        -- Construct the insert query
        insert_sql := format(
            'INSERT INTO %I.pro_laboratory_doctorspecializations (id, name, added_on, last_updated)
             SELECT id, name, added_on, last_updated
             FROM public.healtho_pro_user_uprodoctorspecializations;',
            schema_name
        );

        -- Execute the constructed query
        BEGIN
            EXECUTE insert_sql;
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'Failed to insert into schema: %', schema_name;
        END;
    END LOOP;
END $$;


'''