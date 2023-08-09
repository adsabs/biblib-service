[![Stories in Ready](https://badge.waffle.io/adsabs/biblib-service.png?label=ready&title=Ready)](https://waffle.io/adsabs/biblib-service)
[![Coverage Status](https://coveralls.io/repos/adsabs/biblib-service/badge.svg?branch=master)](https://coveralls.io/r/adsabs/biblib-service?branch=master)
[![Code Climate](https://codeclimate.com/github/adsabs/biblib-service/badges/gpa.svg)](https://codeclimate.com/github/adsabs/biblib-service)

# biblib-service

Astrophysic Data System's library service 

## development
**NOTE: This method is now deprecated and only works on x64 machines.**

A Vagrantfile and puppet manifest are available for development within a virtual machine. To use the vagrant VM defined here you will need to install *Vagrant* and *VirtualBox*. 

  * [Vagrant](https://docs.vagrantup.com)
  * [VirtualBox](https://www.virtualbox.org)

To load and enter the VM: `vagrant up && vagrant ssh`


### tests

Run the tests using `py.test`:
```bash
docker run --name some-postgres -e POSTGRES_USER="postgres" POSTGRES_PASSWORD="postgres" -p 5432:5432 --name postgres
virtualenv python
source python/bin/activate
pip install -r requirements.txt
pip install -r dev-requirements.txt
py.tests biblib/tests/
```

### Layout

Tests are split into three (excessive) stages:
  1. Functional tests (*biblib/tests/functional_tests/*): this tests a *workflow*, for example, a user adding a library and then trying to delete it - and testing everything behaves as expected via the REST work flow
  2. Unit tests, level 1 (*biblib/tests/unit_tests/test_webservices.py*): this tests the above *workflow* on the REST end points
  3. Unit tests, level 2 (*biblib/tests/unit_tests/test_views.py*): this tests the logic of functions that are used within views (end points), and is usually the most fine grained testing
  4. Other unit testing: other tests that are testing other parts, such as *manage* scripts are in their own unit tests, e.g., *biblib/tests/unit_tests/test_manage.py*.

All tests have been written top down, or in a Test-Driven Development approach, so keep this in mind when reading the tests. All the logic has been built based on these tests, so if you were to add something, I'd advise you first create a test for your expected behaviour, and build the logic until it works.

### Running Biblib Locally

To run a version of Biblib locally, a postgres database needs to be created and properly formatted for use with Biblib. This can be done with a local postgres instance or in a docker container using the following commands.
`config.py` must also be copied to `local_config.py` and the environment variables must be adjusted to reflect the local environment.
```bash
docker run -d -e POSTGRES_USER="postgres" -e POSTGRES_PASSWORD="postgres" -p 5432:5432 --name postgres  postgres:12.6
docker exec -it postgres bash -c "psql -c \"CREATE ROLE biblib_service WITH LOGIN PASSWORD 'biblib_service';\""
docker exec -it postgres bash -c "psql -c \"CREATE DATABASE biblib_service;\""
docker exec -it postgres bash -c "psql -c \"GRANT CREATE ON DATABASE biblib_service TO biblib_service;\""
```

Once the database has been created, `alembic` can be used to upgrade the database to the correct alembic revision
```bash
#In order for alembic to have access to the models metadata, the biblib-service directory must be added to the PYTHONPATH
export PYTHONPATH=$(pwd):$PYTHONPATH
alembic upgrade head
```

A new revision can be created by doing the following:
```bash
#In order for alembic to have access to the models metadata, the biblib-service directory must be added to the PYTHONPATH
export PYTHONPATH=$(pwd):$PYTHONPATH
alembic revision -m "<revision-name>" --autogenerate
```

A test version of the microservice can then be deployed using
```bash
python3 wsgi.py
```

## deployment

The only thing to take care of when making a deployment is the migration of the backend database. Libraries uses specific features of PostgreSQL, such as `UUID` and `JSON`-store, so you should think carefully if you wish to change the backend. **The use of `flask-migrate` for database migrations has been replaced by directly calling `alembic`.**  

## Feature additions

Please see the issues page for lists of features that have been kept in mind during the building of private libraries.

