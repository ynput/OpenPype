---
id: admin_hosts_tvpaint
title: TVPaint
sidebar_label: TVPaint
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

## Subset name templates
Definition of possible subset name templates in TVPaint integration.

### Render Layer
Render layer has additional keys for subset name template. It is possible to use **render_layer** and **render_pass**.

- Key **render_layer** is alias for variant (user's input).
- For key **render_pass** is used predefined value `"Beauty"` (ATM value can't be changed).

### Render pass
Render pass has additional keys for subset name template. It is possible to use **render_layer** and **render_pass**.
- Key **render_layer** is filled with value of **render_pass** from `renderLayer` group.
- Key **render_pass** is alias for variant (user's input).

:::important Render Layer/Pass templates
It is recommended to use same subset name template for both **renderLayer** and **renderPass** families.
- Example template: `"{family}{Task}_{Render_layer}_{Render_pass}"`
:::

### Review and Workfile
Families **review** and **workfile** are not manually created but are automatically generated during publishing. That's why it is recommended to not use **variant** key in their subset name template.
