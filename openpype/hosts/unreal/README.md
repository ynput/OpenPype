## Unreal Integration

Supported Unreal Engine version is 4.26+ (mainly because of major Python changes done there).

### Project naming
Unreal doesn't support project names starting with non-alphabetic character. So names like `123_myProject` are
invalid. If Ayon detects such name it automatically prepends letter **P** to make it valid name, so `123_myProject`
will become `P123_myProject`. There is also soft-limit on project name length to be shorter than 20 characters.
Longer names will issue warning in Unreal Editor that there might be possible side effects.
