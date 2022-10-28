* 1 * * * /usr/bin/python /biblib/biblib/manage.py syncdb >> /tmp/biblib_delete_stale_users.log
* 1 * * * /usr/bin/python /biblib/biblib/manage.py clean_versions_number >> /tmp/biblib_revision_deletion.log
* 1 * * * /usr/bin/python /biblib/biblib/manage.py clean_versions_time >> /tmp/biblib_revision_deletion.log