---
id: admin_docsexamples
title: Examples of using notes
sidebar_label: docsexamples
---

import Tabs from '@theme/Tabs';
import TabItem from '@theme/TabItem';

<Tabs
  groupId="platforms"
  defaultValue="win"
  values={[
    {label: 'Windows', value: 'win'},
    {label: 'Linux', value: 'linux'},
    {label: 'Mac', value: 'mac'},
  ]}>

<TabItem value="win">

This is your mac stuff

</TabItem>
<TabItem value="linux">

This is your linux stuff


</TabItem>
<TabItem value="mac">

This is your mac stuff

</TabItem>
</Tabs>






:::note Name of the category

<Tabs
  groupId="platforms"
  defaultValue="win"
  values={[
    {label: 'Windows', value: 'win'},
    {label: 'Linux', value: 'linux'},
    {label: 'Mac', value: 'mac'},
  ]}>

<TabItem value="win">

This is your mac stuff

</TabItem>
<TabItem value="linux">

This is your linux stuff


</TabItem>
<TabItem value="mac">

This is your mac stuff

</TabItem>
</Tabs>

:::


=========================

:::important

-   This is my note
-   another list
-   super list

```python
import os
print(os.environ)
```

:::

:::tip
This is my note
:::

:::note
This is my note
:::

:::warning
This is my note
:::

:::caution
This is my note
:::

export const Highlight = ({children, color}) => (
  <span
    style={{
      backgroundColor: color,
      borderRadius: '2px',
      color: '#fff',
      padding: '0.2rem',
    }}>
    {children}
  </span>
);

<Highlight color="#25c2a0">Docusaurus green</Highlight> and <Highlight color="#1877F2">Facebook blue</Highlight> are my favorite colors.

I can write **Markdown** alongside my _JSX_!
