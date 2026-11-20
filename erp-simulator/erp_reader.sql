-- Rôle lecture seule pour ia-cloud (ERP_POSTGRES_USER), ADR-0007.
-- À lancer en superuser sur livraison_express :
--   psql -d livraison_express -v pwd="'<mot de passe>'" -f erp_reader.sql
CREATE ROLE erp_reader LOGIN PASSWORD :pwd;
GRANT CONNECT ON DATABASE livraison_express TO erp_reader;
GRANT USAGE ON SCHEMA public TO erp_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO erp_reader;
-- Tables créées plus tard par le simulateur : lisibles aussi.
ALTER DEFAULT PRIVILEGES FOR ROLE erp_writer IN SCHEMA public GRANT SELECT ON TABLES TO erp_reader;
