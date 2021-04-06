---
id: module_deadline
title: Deadline Administration
sidebar_label: Deadline
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';


## Preparation

For [AWS Thinkbox Deadline](https://www.awsthinkbox.com/deadline) support you need to set a few things up in both OpenPype and Deadline itself

1. Enable Deadline module it in the [settings](admin_settings_system#deadline)

2. Set up *Deadline Web API service*. For more details on how to do it, see [here](https://docs.thinkboxsoftware.com/products/deadline/10.0/1_User%20Manual/manual/web-service.html).

3. Point OpenPype to your deadline webservice URL in the [settings](admin_settings_system#deadline)

4. Install our custom plugin, event plugin and scripts to your deadline repository. It should be ass simple as copying content of `openPype/vendor/deadline/custom` to `path/to/your/deadline/repository/custom`

## Troubleshooting

