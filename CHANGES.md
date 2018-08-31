# Change Log
All notable changes to the config files will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [1.0.19] - 2018-08-30
### Changed
* Removed unnecesary requirements

## [1.0.19] - 2018-08-30
### Changed
* Fixed requirement conflicts

## [1.0.18] - 2018-08-29
### Changed
* Updated to adsmutils v1.0.7 with readiness/liveliness probes

## [1.0.17] - 2018-08-10
### Changed
* Removed logging setup from config

## [1.0.16] - 2018-08-06
### Changed
* Enabled JSON stdout logging and HTTP connection pool

## [1.0.15] - 2018-04-06
### Changed
* Added Dockerfile and local config

## [1.0.14] - 2018-04-05
### Changed
* Migrated to ADSFlask

## [1.0.13] - 2017-06-22
### Changed
* Some code cleanup (removal of Consul) and update of requirements.txt

## [1.0.12] - 2016-09-27
### Changed
  * Calling the endpoint to transfer ownership resulted in an internal server error because of an attribute conflict (API returns "id" while code assumed "uid")

## [1.0.10] - 2016-07-05
### Changed
  * Bibcodes were being culled if there was one alternate bibcode. This fixes it

## [1.0.9] - 2016-06-23
### Changed
  * field alternate_bibcode, ensured always to be used in BigQuery; fixes hotfix where users could not delete stale bibcodes

## [1.0.8] - 2016-06-21
### Changed
  * Configuration file for logging

## [1.0.7] - 2016-06-07
### Added
  * Pagination of libraries

## [1.0.6] - 2016-05-11
### Changed
  * Increased description length to 200, and included db migration files.
  * Imports changed to enforce 200 and 50 for desc and name.

## [1.0.5] - 2016-03-09
### Changed
  * Renaming/restructuring of the import end points as there are now multiple

### Added

  * Added an ADS 2.0 import end point
  * Added an ADS 2.0 Zotero export (to zip file) end point

## [1.0.4] - 2015-12-17
### Changed

  * Split requirements.txt into a dev-requirements.txt and requirements.txt

## [1.0.3] - 2015-12-09
### Added

  * A new end point that deals with importing content from ADS Classic

### Changed

  * All views have been placed under a common folder named views/
  * Tests updated for new layout
  * Re-write of the delete stale users as the logic was not correct

## [1.0.2] - 2015-08-28
### Changed

Fixed path problems from previously tagged version.

## [1.0.1] - 2015-08-27
Released to production

## [1.0.0] - 2015-07-21

First release of biblibs and placed on staging


