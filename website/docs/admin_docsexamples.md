---
id: admin_docsexamples
title: Examples of using notes
sidebar_label: docsexamples
---

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
