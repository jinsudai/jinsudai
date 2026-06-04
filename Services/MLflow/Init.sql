-- backend write
--CREATE ROLE mlflow_user LOGIN PASSWORD 'strong_password';

GRANT CONNECT ON DATABASE mlflow_db TO mlflow_user;

GRANT USAGE ON SCHEMA public TO mlflow_user;

GRANT SELECT, INSERT, UPDATE, DELETE
ON ALL TABLES IN SCHEMA public
TO mlflow_user;

GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO mlflow_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO mlflow_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
GRANT USAGE, SELECT ON SEQUENCES TO mlflow_user;

GRANT CREATE ON SCHEMA public TO mlflow_user;

-- REVOKE CREATE ON SCHEMA public FROM mlflow_user; retirer CREATE après initialisation pour renforcer la sécurité
-- ALTER TABLE experiments OWNER TO mlflow_user;
-- ALTER TABLE runs OWNER TO mlflow_user;
-- etc selon tables MLflow