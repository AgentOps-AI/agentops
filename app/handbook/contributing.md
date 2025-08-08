# Contributing

## Git Strategy
**Main Branch**: This is the only protected branch. Any PRs into main are the final step to deploying code. CI/CD is triggered off merges into main.

Main _is_ production

**Feature Branch**: As you build out a feature, bug fix, etc, create a branch with a relevant name. There is no naming convention for feature branches at this time.

All development should take place on this feature branch.

Feature branches _can_ be shared between engineers as long as it is properly communicated.

On ocassion a feature branch can act as a parent to sub-branches. Engineers can elect to commit to a sub-branch and merge into the parent feature-branch before finally merging into main.

**Merging to main**: Merging is done via squash commits via Pull Requests on GitHub only. Under no circumstances should commits be made directly to **main**.

To merge your code, open a PR.

## Code Reviews
Code reviews are a critical part of working in an engineering team. PRs are not simply a way to get code into main, rather a tool for validating your work with other engineers.

Every PR must have at least _one_ review from another _relevant_ engineer. This means engineers who have recently modified the code you are contributing to, or are familiar with the domain of your changes. Reviews from other engineers do not satisfy the requirements of a PR, even if it unblocks merging in GitHub.

Reviewers are a tool for a change in perspective when looking at code. An approval does not by itself gaurentee code is ready to be merged. You are responsible for testing and validating that your contributed code is functional and correct.

More on [testing](./testing.md).

## Refactoring

When frustrated with software, its very easy to want to nuke it and start over. This typically leads to comprehensive refactoring or building from scratch.

Sometimes this is a proper response, other times it's a gut reaction to frustration that leads us down a circle of constantly reinventing the wheel.

Before any major overhaul of work already completed, the engineer wishing to redo work **MUST** appropriately communicate their desire, plan and reasoning with all relevant stakeholders (author of the code or team member who was present when code was written, tech leadership, engineers participating in refactor). The decision to refactor must be made as a team. 

extending good patterns > refactoring > rebuilding > crying

## Open Source Mentality
Every line of code written should be done with the assumption that it is open source or could be made open source at any moment.

1. Write code with pride. Open source code is your art that you are putting into the world. It is a reflection of yourself as an engineer and the skills you have developed.
2. Assuming code is visible by attackers encourages us to be more security-minded. There is no security through obscurity.
3. Visibility to partners and customers can best be done by making code accessible and readable.
4. Open-source is a strong value of our company. We believe that producing open and free software is in our best interest, if the codebase isn't currently open-source, it likely will be in the future.