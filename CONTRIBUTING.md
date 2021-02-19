## How to contribute to Pype

#### **Did you find a bug?**

1. Check in the issues and our [bug triage[(https://github.com/pypeclub/pype/projects/2) to make sure it wasn't reported already.
2. Ask on our [discord](http://pype.community/chat) Often, what appears as a bug, might be the intended behaviour for someone else.
3. Create a new issue.
4. Use the issue template for you PR please.


#### **Did you write a patch that fixes a bug?**

- Open a new GitHub pull request with the patch.
- Ensure the PR description clearly describes the problem and solution. Include the relevant issue number if applicable.


#### **Do you intend to add a new feature or change an existing one?**

- Open a new thread in the [github discussions](https://github.com/pypeclub/pype/discussions/new)
- Do not open issue untill the suggestion is discussed. We will convert accepted suggestions into backlog and point them to the relevant discussion thread to keep the context.

#### **Do you have questions about the source code?**

Open a new question on [github discussions](https://github.com/pypeclub/pype/discussions/new)

## Branching Strategy

As we move to 3.x as the primary supported version of pype and only keep 2.15 on bug bugfixes and client sponsored feature requests, we need to be very careful with merging strategy.

We also use this opportunity to switch the branch naming. 3.0 production branch will no longer be called MASTER,  but will be renamed to MAIN. Develop will stay as it is.

A few important notes about 2.x and 3.x development:

- 3.x features are not backported to 2.x unless specifically requested
- 3.x bugs and hotfixes can be ported to 2.x if they are relevant or severe
- 2.x features and bugs MUST be ported to 3.x at the same time

## Pull Requests

- Each 2.x PR MUST have a corresponding 3.x PR in github. Without 3.x PR, 2.x features will not be merged! Luckily most of the code is compatible, albeit sometimes in a different place after refactor. Porting from 2.x to 3.x should be really easy.
- Please keep the corresponding 2 and 3 PR names the same so they can be easily identified from the PR list page.
- Each 2.x PR should be labeled with `2.x-dev` label.

Inside each PR, put a link to the corresponding PR

Of course if you want to contribute, feel free to make a PR to only 2.x/develop or develop, based on what you are using. While reviewing the PRs, we might convert the code to corresponding PR for the other release ourselves. 

We might also change the target of you PR to and intermediate branch, rather than `develop` if we feel it requires some extra work on our end. That way, we preserve all your commits so you don't loos out on the contribution credits.




If a PR is targeted at 2.x release it must be labelled with 2x-dev label in Github.   
