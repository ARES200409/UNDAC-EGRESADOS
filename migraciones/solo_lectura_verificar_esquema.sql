-- Consultas de solo lectura para verificar entorno de NEXO UNDAC.
USE seguimiento_egresados;
SELECT COUNT(*) AS total_tablas FROM information_schema.tables WHERE table_schema='seguimiento_egresados';
SELECT table_name FROM information_schema.tables WHERE table_schema='seguimiento_egresados' ORDER BY table_name;
SELECT trigger_name, event_object_table, action_timing, event_manipulation
FROM information_schema.triggers WHERE trigger_schema='seguimiento_egresados';
SELECT routine_name, routine_type FROM information_schema.routines
WHERE routine_schema='seguimiento_egresados';
SELECT nombre FROM roles ORDER BY id_rol;
