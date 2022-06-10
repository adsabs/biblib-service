#!/usr/bin/env bash
set -e
psql "postgres://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_HOST/$POSTGRES_DB?sslmode=disable" <<-EOSQL
    CREATE USER biblib_microservice WITH ENCRYPTED PASSWORD 'biblib_microservice';
    CREATE DATABASE biblib_microservice;
    CREATE DATABASE biblib_microservice_test;
    GRANT ALL PRIVILEGES ON DATABASE biblib_microservice TO biblib_microservice;
    GRANT ALL PRIVILEGES ON DATABASE biblib_microservice_test TO biblib_microservice;
EOSQL
