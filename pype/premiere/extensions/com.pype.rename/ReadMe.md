# Pype timeline items renamer

This panel is used to rename selected clips on timeline. It is not directly interconnected with **Avalon** so it can be used separately. It has several different modes:

### Sequential Rename with Hierarchy

This mode uses tokens as `{folder}`, `{episode}` and `{sequence}` to rename clips along with numeric padding pattern `####`. Value for this tokens is filled in input boxes. If value is left empty, token is ignored. Those values are also stored in clips properties, so even if token is not used in clip name, it will be stored in clip property (and then used to create hierarchy when publishing into **Avalon**). `####` pattern can be arbitrary long, but is mandatory.

Example:

```
{folder}_{episode}_{sequence}_#####
```
Will result in `f01_ep01_sq01_0010` if respective tokens are set to these values. If folder token value isn't set result will be `_ep01_sq01_0010`.

Clip numbering can be adjusted by **Start #** and **Increment** fields. Setting start to **10** and increment to **10** with number padding pattern **####** will result in clip number **0010** for first clip, **0020** for second and so on.

### Sequential Rename

Is same as the one above, except not using tokens.

### Simple Rename

This will rename shot to new specified name. If `{shot}` token is used, it will reference current clip name. So if current clip name is `clip01` and we specify new name as `{shot}_foo`, result will be **clip01_foo**.

### Find and replace

Classic find and replace mode, using `{shot}` token as the mode above.

### Match sequence

Is not implemented yet.

### Clip Rename

Will name clip based on filename without extension.

### Change Case

This will change case of clip name to `UPPER` or `lower` case.
