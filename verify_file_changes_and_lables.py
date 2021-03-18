#!/usr/bin/env python3

import os
import sys
import re
from github import Github
import typing
from collections import namedtuple
import fnmatch
from functools import cached_property

Arguments = namedtuple(
    'Arguments',
    [
        'token',
        'valid_labels',
        'repo_name',
        'pr_number',
        'file_globs',
        'required_label_message',
        'label_added_message',
        'changes_reverted_message'
    ])


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


class PrChecker:
    "Checks a PR for changes to critical files and lables"
    def __init__(self, args: Arguments, pr: PullRequest):
        self.pr = pr
        self.args = args

    @classmethod
    def from_args(cls, args: Arguments):
        "Instantiates a PrChecker using the arguments provided"
        repo = Github(args.token).get_repo(args.repo_name)

        # Create a pull request object
        pr = repo.get_pull(args.pr_number)

        return cls(args, pr)

    @cached_property
    def _pr_has_required_label(self) -> bool:
        "Returns True if the pr has any of the required lables and False otherwise"
        # Get the pull request labels
        pr_labels = self.pr.get_labels()

        # Check which of the label in the pull request, are in the
        # list of valid labels
        for label in pr_labels:
            if label.name in self.args.valid_labels:
                return True

        return False

    @cached_property
    def _pr_has_changed_critical_files(self) -> bool:
        "Returns True if the pr includes changes to any of the critical files"
        pr_files = self.pr.get_files()
        for changed_file in pr_files:
            for pattern in self.args.file_globs:
                if fnmatch.fnmatch(changed_file.filename, pattern):
                    return True
        return False

    def verify_pr(self):
        """Verifies that the if the pr has changed critical files that it has 
        the appropriate label.
        
        If not, it will request changes on the PR. If the changes are reverted
        or the appropriate label is added it will dismiss the change request.
        """
        self._handle_pr_review()

    def _is_bots_change_request(self, pr_review: PullRequestReview):
        "Returns True if the pr review is a change request from the github actions bot"
        return ((pr_review.user.login == 'github-actions[bot]'
                 or self.args.required_label_message in pr_review.body)
                and pr_review.state == 'CHANGES_REQUESTED')

    def _get_bots_pr_reviews(self) -> PaginatedList[PullRequestReview]:
        "Returns a list of the change request created by the github actions bot"
        pr_reviews = self.pr.get_reviews()
        return list(filter(lambda review: self._is_bots_change_request(review), pr_reviews))

    def _handle_pr_review(self):
        """Verifies that the if the pr has changed critical files that it has 
        the appropriate label.
        
        If not, it will request changes on the PR. If the changes are reverted
        or the appropriate label is added it will dismiss the change request.
        """
        bots_prs = self._get_bots_pr_reviews()

        if self._pr_has_changed_critical_files and not self._pr_has_required_label:
            # If there were not valid labels, then create a pull request review, requesting changes
            print(
                f'This pull request contains critical changes and does not contain any of the valid labels: {self.args.valid_labels}')
            if not len(bots_prs):
                self.pr.create_review(body=f'{self.args.required_label_message} Please add one of the following labels: `{self.args.valid_labels}` to confirm '
                                 'these changes.',
                                 event='REQUEST_CHANGES')
        else:
            print('No changes to critical files')
            # If there were valid labels, dismiss the request for changes if present
            for pr_review in bots_prs:
                print('Dismissing changes request')
                pr_review.dismiss(
                    self.args.label_added_message if self._pr_has_required_label else self.args.changes_reverted_message)


def get_pr_reference(github_ref: str) -> int:
    "Tries to extract the pull request number from the GitHub reference."
    try:
        pr_number = int(
            re.search('refs/pull/([0-9]+)/merge', github_ref).group(1))
        print(f'Pull request number: {pr_number}')
        return pr_number
    except AttributeError:
        raise ValueError(
            f'The Pull request number could not be extracted from the GITHUB_REF = {github_ref}')


def get_args() -> Arguments:
    "Uses the environmental variable and command line arguments to return the required arguments"
    # Check if the number of input arguments is correct
    if len(sys.argv) != 7:
        raise ValueError('Invalid number of arguments!')

    # Get the GitHub token
    token = sys.argv[1]

    # Get the list of valid labels
    valid_labels = sys.argv[2]
    print(f'Valid labels are: {valid_labels}')

    file_globs = sys.argv[3].split(',')
    print(f'File globs are {file_globs}')

    required_label_message = sys.argv[4]
    label_added_message = sys.argv[5]
    changes_reverted_message = sys.argv[6]

    # Get needed values from the environmental variables
    repo_name = get_env_var('GITHUB_REPOSITORY')
    github_ref = get_env_var('GITHUB_REF')
    pr_number = get_pr_reference(github_ref)

    return Arguments(token, valid_labels, repo_name, pr_number, file_globs,
                     required_label_message, label_added_message, changes_reverted_message)


def main():
    args = get_args()
    pr_checker = PrChecker.from_args(args)
    pr_checker.verify_pr()


if __name__ == '__main__':
    main()
