-- PostGIS index maintenance helper for scripts/postgis_maintenance.sh
CREATE OR REPLACE FUNCTION auto_maintain_indexes(p_dry_run boolean DEFAULT false)
RETURNS jsonb
LANGUAGE plpgsql
AS $$
DECLARE
    rec record;
    actions jsonb := '[]'::jsonb;
BEGIN
    FOR rec IN
        SELECT
            n.nspname AS schema_name,
            t.relname AS table_name,
            c.relname AS index_name
        FROM pg_class c
        JOIN pg_namespace n ON n.oid = c.relnamespace
        JOIN pg_index i ON i.indexrelid = c.oid
        JOIN pg_class t ON t.oid = i.indrelid
        JOIN pg_am am ON am.oid = c.relam
        WHERE c.relkind = 'i'
          AND am.amname = 'gist'
          AND n.nspname NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
    LOOP
        actions := actions || jsonb_build_array(
            jsonb_build_object(
                'action', 'analyze',
                'schema', rec.schema_name,
                'table', rec.table_name,
                'index', rec.index_name
            )
        );

        IF NOT p_dry_run THEN
            EXECUTE format('ANALYZE %I.%I', rec.schema_name, rec.table_name);
        END IF;
    END LOOP;

    RETURN jsonb_build_object(
        'dry_run', p_dry_run,
        'gist_indexes', jsonb_array_length(actions),
        'actions', actions
    );
END;
$$;