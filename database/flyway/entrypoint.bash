#!/usr/bin/env bash

/flyway/flyway -configFiles=/flyway/flyway.conf -baselineOnMigrate="true" migrate