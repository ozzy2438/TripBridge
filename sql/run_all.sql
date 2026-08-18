-- TripBridge source-load gate.
-- Data arrives -> Load -> Schema -> Row reconciliation -> PK/FK -> Business DQ -> Financial controls -> PASS/FAIL
-- Downstream analytics should run only after the latest pipeline_test_run is PASS.
--
--   psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f sql/run_all.sql

\ir tests/00_harness.sql
\ir tests/01_schema_tests.sql
\ir tests/02_row_reconciliation.sql
\ir tests/03_pk_fk_tests.sql
\ir tests/04_business_dq.sql
\ir tests/05_financial_controls.sql
\ir tests/06_gate.sql
