---
id: dev_contribute
title: Contribute to openPype development
sidebar_label: Contribute
---

## What should you do if ...

### You found a bug.

1. Check in the issues and our [bug triage](https://github.com/pypeclub/pype/projects/2) to make sure it wasn't reported already.
2. Ask on our [discord](http://pype.community/chat) Often, what appears as a bug, might be the intended behavior for someone else.
3. Create a new issue.
4. Use the issue template for you PR please.


### You wrote a patch that fixes a bug.

- Open a new GitHub pull request with the patch.
- Ensure the PR description clearly describes the problem and solution. Include the relevant issue number if applicable.


### You intend to add a new feature or change an existing one.

- Open a new thread in the [github discussions](https://github.com/pypeclub/pype/discussions/new)
- Do not open issue until the suggestion is discussed. We will convert accepted suggestions into backlog and point them to the relevant discussion thread to keep the context.

### You have questions about the source code.

Open a new question on [github discussions](https://github.com/pypeclub/pype/discussions/new)


## Branching Strategy

As we move to 3.x as the primary supported version of OpenPype and only keep Pype 2.15 on bugfixes and client sponsored feature requests, we need to be very careful with merging strategy.

These are the important branches to remember.

### OpenPype 3.x

**`main`** -  Production branch with stable releases

**`develop`** - Development branch where we merge all PRs during the development

**`release/3.x.x`** - Testing branch for a release, once a release branch is created, no new features
are accepted for the given release. Bugfixes, however, are expected. Once the branch is stable it is
merged to `main` and `develop` and `main` is tagged with a new release

**`feature/{Issue#}-{Issue_name}`** - development of new features

**`bugfix/{Issue#}-{Issue_name}`** - bug fixes

**`hotfix/{Issue#}-{Issue_name}`** - production critical hotfixes (always created from `main`)

### OpenPype 2.x

Branching is identical to 3.x development, however all the branches should be pre-pended with
`2.x/` namespace. For example `2.x/feature/1025-support_exporting_of_alembic`, 
`2.x/bugfix/wrong_colourspace_in_maya`

Main and develop for 2.x development are `2.x/main` and `2.x/develop`


A few important notes about 2.x and 3.x development:

- 3.x features are not backported to 2.x unless specifically requested.
- 3.x bugs and hotfixes can be ported to 2.x if they are relevant or severe.
- 2.x features and bugs MUST be ported to 3.x at the same time.

## Pull Requests

- Each 2.x PR MUST have a corresponding 3.x PR in github. Without 3.x PR, 2.x features will not be merged! Luckily most of the code is compatible, albeit sometimes in a different place after the refactoring. Porting from 2.x to 3.x should be really easy.
- Please keep the corresponding 2 and 3 PR names the same so they can be easily identified from the PR list page.
- Each 2.x PR should be labeled with `2.x-dev` label.

Inside each PR, put a link to the corresponding PR.

Of course if you want to contribute, feel free to make a PR to only 2.x/develop or develop, based on what you are using. While reviewing the PRs, we might convert the code to corresponding PR for the other release ourselves. 

We might also change the target of you PR to and intermediate branch, rather than `develop` if we feel it requires some extra work on our end. That way, we preserve all your commits so you don't lose out on the contribution credits.




If a PR is targeted at 2.x release it must be labelled with 2x-dev label in Github.   