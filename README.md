# Release-Worker

# Changelog.py

## Setup

1. `pip install --upgrade python-gitlab`
2. Generate `Personal Access Token` from gitlab

## Usage
1. Setup config file `changelog.cfg`

```
[Project1]
project_name: Project Name in Gitlab
ref_branch:  Only catch on this branch
last_release_tag:  Commit since this tag
display_name:   Name in changelog
```

3. Run `python changelog.py <release_number>`
4. Copy and paste

## Conventions
### Auto classify merge request to following sections
1. New Features : branch name contain `feature`
2. Fixed :  branch name contain `fix` or `bug`
3. CI / Refactoring / Other : `not commit above`

## TODO
* Output to google doc by api
* Modify config from jenkins job
* include important general commits (not merge request)
