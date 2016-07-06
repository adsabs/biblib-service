[![Stories in Ready](https://badge.waffle.io/adsabs/biblib-service.png?label=ready&title=Ready)](https://waffle.io/adsabs/biblib-service)
[![Build Status](https://travis-ci.org/adsabs/biblib-service.svg?branch=master)](https://travis-ci.org/adsabs/biblib-service)
[![Coverage Status](https://coveralls.io/repos/adsabs/biblib-service/badge.svg?branch=master)](https://coveralls.io/r/adsabs/biblib-service?branch=master)
[![Code Climate](https://codeclimate.com/github/adsabs/biblib-service/badges/gpa.svg)](https://codeclimate.com/github/adsabs/biblib-service)

# biblib-service

Astrophysic Data System's library service 

## development

A Vagrantfile and puppet manifest are available for development within a virtual machine. To use the vagrant VM defined here you will need to install *Vagrant* and *VirtualBox*. 

  * [Vagrant](https://docs.vagrantup.com)
  * [VirtualBox](https://www.virtualbox.org)

To load and enter the VM: `vagrant up && vagrant ssh`

### tests

Run the tests using `nosetests` or `py.test`:
```bash
nosetests biblib/tests/
```

### Layout

Tests are split into three (excessive) stages:
  1. Functional tests (*biblib/tests/functional_tests/*): this tests a *workflow*, for example, a user adding a library and then trying to delete it - and testing everything behaves as expected via the REST work flow
  2. Unit tests, level 1 (*biblib/tests/unit_tests/test_webservices.py*): this tests the above *workflow* on the REST end points
  3. Unit tests, level 2 (*biblib/tests/unit_tests/test_views.py*): this tests the logic of functions that are used within views (end points), and is usually the most fine grained testing
  4. Other unit testing: other tests that are testing other parts, such as *manage* scripts are in their own unit tests, e.g., *biblib/tests/unit_tests/test_manage.py*.

All tests have been written top down, or in a Test-Driven Development approach, so keep this in mind when reading the tests. All the logic has been built based on these tests, so if you were to add something, I'd advise you first create a test for your expected behaviour, and build the logic until it works.


## deployment

The only thing to take care of when making a deployment is the migration of the backend database. Libraries uses specific features of PostgreSQL, such as `UUID` and `JSON`-store, so you should think carefully if you wish to change the backend. It is recommended you implement the migrations using the *Flask-migrate* scripts within *manage.py* and not use `alembic` as is used elsewhere. When you have access to the DB:

```bash
cd biblib/
python manage.py db upgrade
```

If you wish to do anything else, then just look at the default behaviour of *Flask-migrate* scripts (https://flask-migrate.readthedocs.io/en/latest/) or within the source code.

## Feature additions

Please see the issues page for lists of features that have been kept in mind during the building of private libraries.
