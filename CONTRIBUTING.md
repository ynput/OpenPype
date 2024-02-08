## How to contribute to OpenPype

OpenPype has reached the end of its life and is now in a limited maintenance mode (read more at https://community.ynput.io/t/openpype-end-of-life-timeline/877). As such we're no longer accepting contributions unless they are also ported to AYON at the same time. 

## Getting my PR merged during this period

- Each OpenPype PR MUST have a corresponding AYON PR in github. Without AYON compatibility features will not be merged! Luckily most of the code is compatible, albeit sometimes in a different place after refactor. Porting from OpenPype to AYON should be really easy.
- Please keep the corresponding OpenPype and AYON PR names the same so they can be easily identified.

Inside each PR, put a link to the corresponding PR from the other product. OpenPype PRs should point to AYON PR and vice versa.

AYON repository structure is a lot more granular compared to OpenPype. If you're unsure what repository your AYON equivalent PR should target, feel free to make OpenPype PR first and ask.
