# Verify Pull Request Label Action

This action will verify that if a pull request contains changes to critical files it has the appropriate label.

If the pull request has changed critical files and does not contain one of the appropriate labels, then the action will create a pull request review requesting changes (event: `REQUEST_CHANGES`). If no critical file is changed or valid label is present in the pull request, dismiss a previous request changes review. In both of these cases the exit code will be `0`, and the GitHub check will pass successfully.

This is intended to ensure that changes to critical files are appropriately flagged with the correct labels.

## Inputs

### `github-token`

**Default** The GitHub token.

### `valid-labels`

**Required** A list of valid labels. It must be a quoted string, with label separated by colons. For example: `'bug, enhancement'`

### `file-globs`

**Required** The file globs which will trigger a PR change request if the labels are not present

### `required-label-message`

**Optional** The first line of the PR review comment requesting changes when there are critical file changes and missing labels

### `change-request-dismiss-message-label-added`

**Optional** The message displayed when the change review is dismissed because the appropriate label has been added

### `change-request-dismiss-message-changes-reverted`

**Optional** The message displayed when the change review is dismissed because the file changes have been reverted


## Example usage

In your workflow YAML file add this step:
```yaml
uses: JohnBellSageCom/verify-file-changes-and-labels-action@v1.0.0
with:
    github-token: '${{ secrets.GITHUB_TOKEN }}'
    valid-labels: 'critical-file-changes'
    file-globs: 'lib/complex_logic/*'
```

and trigger it with:
```yaml
on:
  pull_request:
   types: [opened, labeled, unlabeled, synchronize]
```
