
#!/usr/bin/env bash
set -e
psql "postgres://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST/$POSTGRES_DB?sslmode=disable" <<-EOSQL
    CREATE USER postrgres WITH ENCRYPTED PASSWORD 'postgres';
    CREATE DATABASE biblib_microservice;
    CREATE DATABASE biblib_microservice_test;
    GRANT ALL PRIVILEGES ON DATABASE biblib_microservice TO postgres;
    GRANT ALL PRIVILEGES ON DATABASE biblib_microservice_test TO postgres;
EOSQL
