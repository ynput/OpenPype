---
id: admin_environment
title: Environment
sidebar_label: Environment
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

## OPENPYPE_TMPDIR:
 - Custom staging dir directory
 - Supports anatomy keys formatting. ex `{root[work]}/{project[name]}/temp`
 - supported formatting keys:
    - root[work]
    - project[name | code]

## OPENPYPE_DEBUG
 - setting logger to debug mode
 - example value: "1" (to activate)

## OPENPYPE_LOG_LEVEL
 - stringified numeric value of log level. [Here for more info](https://docs.python.org/3/library/logging.html#logging-levels)
 - example value: "10"

## OPENPYPE_MONGO
- If set it takes precedence over the one set in keyring
- for more details on how to use it go [here](admin_use#check-for-mongodb-database-connection)

## OPENPYPE_USERNAME
- if set it overrides system created username
