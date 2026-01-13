* 1 * * * cd /biblib && export FLASK_APP=biblib/app.py && flask biblib syncdb >> /tmp/biblib_delete_stale_users.log
* 1 * * * cd /biblib && export FLASK_APP=biblib/app.py && flask biblib clean_versions_number >> /tmp/biblib_revision_deletion.log
* 1 * * * cd /biblib && export FLASK_APP=biblib/app.py && flask biblib clean_versions_time >> /tmp/biblib_revision_deletion.log
