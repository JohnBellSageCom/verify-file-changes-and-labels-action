#!/usr/bin/env python3

import os
import sys
import re
from github import Github
import typing
from collections import namedtuple
import fnmatch

Arguments = namedtuple(
    'Arguments', ['token', 'valid_labels', 'repo_name', 'pr_number', 'file_globs'])


def get_env_var(env_var_name, echo_value=False) -> str:
    """Try to get the value from a environmental variable.

    If the values is 'None', then a ValueError exception will
    be thrown.

    Args:
        env_var_name (string): The name of the environmental variable.
        echo_value (bool): Print the resulting value

    Returns:
        string: the value from the environmental variable.
    """
    value = os.environ.get(env_var_name)

    if value == None:
        raise ValueError(
            f'The environmental variable {env_var_name} is empty!')

    if echo_value:
        print(f"{env_var_name} = {value}")

    return value


def filter_pr_reviews_to_bot(pr_review: PullRequestReview):
    return ((pr_review.user.login == 'github-actions[bot]'
             or 'There are changes to production translations in this pull request' in pr_review.body)
            and pr_review.state == 'CHANGES_REQUESTED')


def get_bots_pr_reviews(pr: PullRequest) -> PaginatedList[PullRequestReview]:
    pr_reviews = pr.get_reviews()
    return list(filter(filter_pr_reviews_to_bot, pr_reviews))


def handle_pr_review(pr: PullRequest, should_request_changes: bool, valid_labels: str):
    # Check if there were at least one valid label
    # Note: In both cases we exit without an error code and let the check to succeed. This is because GitHub
    # workflow will create different checks for different trigger conditions. So, adding a missing label won't
    # clear the initial failed check during the PR creation, for example.
    # Instead, we will create a pull request review, marked with 'REQUEST_CHANGES' when no valid label was found.
    # This will prevent merging the pull request until a valid label is added, which will trigger this check again
    # and will create a new pull request review, but in this case marked as 'APPROVE'
    bots_prs = get_bots_pr_reviews(pr)

    if should_request_changes:
        # If there were not valid labels, then create a pull request review, requesting changes
        print(
            f'Error! This pull request does not contain any of the valid labels: {valid_labels}')
        if not len(bots_prs):
            pr.create_review(body='There are changes to production translations in this pull request. '
                             f'Please add one of the following labels: `{valid_labels}` to confirm that '
                             'you intend to make these changes.',
                             event='REQUEST_CHANGES')
    else:
        # If there were valid labels, dismiss the request for changes if present
        for pr_review in bots_prs:
            print('Dismissing changes request')
            pr_review.dismiss(
                'Required label added to PR confirming intention to update production translations')


def get_pr_reference(github_ref: str) -> int:
    # Try to extract the pull request number from the GitHub reference.
    try:
        pr_number = int(
            re.search('refs/pull/([0-9]+)/merge', github_ref).group(1))
        print(f'Pull request number: {pr_number}')
        return pr_number
    except AttributeError:
        raise ValueError(
            f'The Pull request number could not be extracted from the GITHUB_REF = {github_ref}')


def get_args() -> Arguments:
    # Check if the number of input arguments is correct
    if len(sys.argv) != 4:
        raise ValueError('Invalid number of arguments!')

    # Get the GitHub token
    token = sys.argv[1]

    # Get the list of valid labels
    valid_labels = sys.argv[2]
    print(f'Valid labels are: {valid_labels}')

    file_globs = sys.argv[3].split(',')
    print(f'File globs are {file_globs}')

    # Get needed values from the environmental variables
    repo_name = get_env_var('GITHUB_REPOSITORY')
    github_ref = get_env_var('GITHUB_REF')
    pr_number = get_pr_reference(github_ref)

    return Arguments(token, valid_labels, repo_name, pr_number, file_globs)


def pr_has_required_label(pr: PullRequest, valid_labels: str) -> bool:
    # Get the pull request labels
    pr_labels = pr.get_labels()
    # This is a list of valid label found in the pull request
    pr_valid_labels = []

    # Check which of the label in the pull request, are in the
    # list of valid labels
    for label in pr_labels:
        if label.name in valid_labels:
            pr_valid_labels.append(label.name)

    return len(pr_valid_labels) > 0


def pr_has_changed_critical_files(pr: PullRequest, patterns: [str]) -> bool:
    pr_files = pr.get_files()
    for changed_file in pr_files:
        for pattern in patterns:
            if fnmatch.fnmatch(changed_file.filename, pattern):
                return True
    return False


def main():
    args = get_args()

    # Create a repository object, using the GitHub token
    repo = Github(args.token).get_repo(args.repo_name)

    # Create a pull request object
    pr = repo.get_pull(args.pr_number)
    critical_files_changed = pr_has_changed_critical_files(pr, args.file_globs)
    is_required_label_present = pr_has_required_label(pr, args.valid_labels)

    handle_pr_review(pr,
                     should_request_changes=critical_files_changed and not is_required_label_present,
                     valid_labels=args.valid_labels)


if __name__ == '__main__':
    main()
