#!/bin/bash

# Run python coverage tests using all the tests files,
# both unit and functional.
# This is opted for, rather than a run_test.py, as it
# much simpler, and if any of them fail, it will raise
# a bash exit error in TravisCI

# Find all the test files
TEST_FILES=`ls biblib/tests/*/test_*.py`

# Run each coverage test
for TEST_FILE in $TEST_FILES
do
	echo "Test file: $TEST_FILE"
	coverage run -p --source=. $TEST_FILE
done

