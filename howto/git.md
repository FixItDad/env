### Move commits from master to another branch
Assumes that commits have NOT been pushed.
```
git fetch origin
git checkout master
git rebase origin/master
git branch <new-branch>
git status
# make sure git status is clean
git reset --hard origin-master
```
