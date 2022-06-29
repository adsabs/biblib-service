#!/bin/bash
cd /app

py.test biblib/tests/unit_tests/test_views.py
RESULT=$?

if [[ "$1" = "-p" ]]; then
    echo "For interactive access, run in a diferent terminal:"
    echo "  docker exec -it pytest_biblib_microservice bash"
    echo "Press CTRL+c to stop"
    tail -f /dev/null
fi

return $RESULT