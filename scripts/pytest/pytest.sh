#!/bin/bash
cd /app

py.test

#echo "For interactive access, run in a diferent terminal:"
#echo "  docker exec -it pytest_biblib_microservice bash"
#echo "Press CTRL+c to stop"
#tail -f /dev/null
