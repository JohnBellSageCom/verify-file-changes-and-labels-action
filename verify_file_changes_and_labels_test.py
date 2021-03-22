from unittest.mock import MagicMock
from verify_file_changes_and_labels import PrChecker, Arguments, GITHUB_BOT_LOGIN

DEFAULT_GLOB = '**/main.*'
CRITICAL_FILE_CHANGE = 'lib/main.py'


def _get_args(
        token='token',
        valid_labels=None,
        repo_name='repo_name',
        pr_number=123,
        file_globs=None,
        required_label_message='required_label_message',
        label_added_message='label_added_message',
        changes_reverted_message='changes_reverted_message'):
    valid_labels = valid_labels if valid_labels else ['valid_labels']
    file_globs = file_globs if file_globs else [DEFAULT_GLOB]
    return Arguments(token, valid_labels, repo_name, pr_number, file_globs,
                     required_label_message, label_added_message, changes_reverted_message)


def _setup_labels(pr, n=5):
    labels = []
    for i in range(n):
        label = MagicMock()
        label.configure_mock(name=f'label{i}')
        labels.append(label)
    pr.get_labels.return_value = labels


def _get_files(base_path='lib/', extension='src', file_name='filename', n=10):
    files = []
    for i in range(n):
        files.append(
            MagicMock(filename=f'{base_path}{file_name}{i}.{extension}'))
    return files


def _setup_pr_reviews(pr, with_change_request_body=None, with_comment_body=None):
    pr_reviews = []
    change_request_review = None
    if with_change_request_body:
        change_request_review = MagicMock(
            user=MagicMock(login=GITHUB_BOT_LOGIN),
            body=with_change_request_body,
            state='CHANGES_REQUESTED'
        )
        pr_reviews.append(change_request_review)
    if with_comment_body:
        pr_reviews.append(MagicMock(
            user=MagicMock(login=GITHUB_BOT_LOGIN),
            body=with_comment_body,
            state='COMMENT'
        ))
    for i in range(5):
        pr_reviews.append(MagicMock(
            user=MagicMock(login=f'GitHubUser{i}'),
            body='',
            state='COMMENT'
        ))
    pr.get_reviews.return_value = pr_reviews
    return change_request_review


# GIVEN a pr with valid labels
# WHEN _pr_has_required_label is invoked
# THEN it returns True
def test_pr_checker_valid_labels():
    # Arrange
    args = _get_args(valid_labels=['label1', 'label2'])
    pr = MagicMock()
    _setup_labels(pr)

    pr_checker = PrChecker(args, pr)

    # Act and Assert
    assert pr_checker._pr_has_required_label


# GIVEN a pr without valid labels
# WHEN _pr_has_required_label is invoked
# THEN it returns False
def test_pr_checker_no_valid_labels():
    # Arrange
    args = _get_args(valid_labels=['label6', 'label7'])
    pr = MagicMock()
    _setup_labels(pr)

    pr_checker = PrChecker(args, pr)

    # Act and Assert
    assert not pr_checker._pr_has_required_label


# GIVEN a pr with critical file changes labels
# WHEN _pr_has_changed_critical_files is invoked
# THEN it returns True
def test_pr_checker_has_changed_critical_files():
    # Arrange
    args = _get_args(file_globs=[DEFAULT_GLOB])
    pr = MagicMock()
    pr.get_files.return_value = [
        *_get_files(),
        MagicMock(filename=CRITICAL_FILE_CHANGE)
    ]

    pr_checker = PrChecker(args, pr)

    # Act and Assert
    assert pr_checker._pr_has_changed_critical_files


# GIVEN a pr without critical file changes labels
# WHEN _pr_has_changed_critical_files is invoked
# THEN it returns False
def test_pr_checker_has_not_changed_critical_files():
    # Arrange
    args = _get_args(file_globs=[DEFAULT_GLOB])
    pr = MagicMock()
    pr.get_files.return_value = [*_get_files()]

    pr_checker = PrChecker(args, pr)

    # Act and Assert
    assert not pr_checker._pr_has_changed_critical_files


# GIVEN a pr with critical file changes labels
# AND the arguments contains more than one glob
# WHEN _pr_has_changed_critical_files is invoked
# THEN it returns False
def test_pr_checker_has_changed_critical_files_multiple_globs():
    # Arrange
    args = _get_args(file_globs=[DEFAULT_GLOB, 'lib/critical/**/*'])
    pr = MagicMock()
    pr.get_files.return_value = [
        *_get_files(),
        MagicMock(filename='lib/critical/example.py')
    ]

    pr_checker = PrChecker(args, pr)

    # Act and Assert
    assert not pr_checker._pr_has_changed_critical_files

# GIVEN a PR which the GitHub actions bot has not reviewed
# WHEN _get_bots_pr_reviews is called
# THEN it returns an empty list


def test_pr_checker_get_bots_pr_reviews_no_reviews():
    # Arrange
    args = _get_args()
    pr = MagicMock()
    _setup_pr_reviews(pr)

    pr_checker = PrChecker(args, pr)

    # Act
    bots_prs = pr_checker._get_bots_pr_reviews()

    # Asset
    assert len(bots_prs) == 0


# GIVEN a PR which the GitHub actions bot requested changes for
# WHEN _get_bots_pr_reviews is called
# THEN it returns a list containing the review
def test_pr_checker_get_bots_pr_reviews_change_request_reviews():
    # Arrange
    args = _get_args()
    pr = MagicMock()
    _setup_pr_reviews(pr, with_change_request_body=args.required_label_message)

    pr_checker = PrChecker(args, pr)

    # Act
    bots_prs = pr_checker._get_bots_pr_reviews()

    # Asset
    assert len(bots_prs) == 1


# GIVEN a PR which the GitHub actions bot has commented on
# WHEN _get_bots_pr_reviews is called
# THEN it returns an empty list
def test_pr_checker_get_bots_pr_reviews_comment_reviews():
    # Arrange
    args = _get_args()
    pr = MagicMock()
    _setup_pr_reviews(pr, with_comment_body=args.required_label_message)

    pr_checker = PrChecker(args, pr)

    # Act
    bots_prs = pr_checker._get_bots_pr_reviews()

    # Asset
    assert len(bots_prs) == 0

# GIVEN a PR which has critical file changes
# AND does not have lables
# AND the bot has not yet requested changes
# WHEN verify_pr is called
# THEN the bot creates a review requesting changes with the expected body


def test_pr_checker_verify_pr_critical_file_changes_no_label():
    # Arrange
    args = _get_args(file_globs=[DEFAULT_GLOB], valid_labels=['not_present'])
    pr = MagicMock()
    pr.get_files.return_value = [
        *_get_files(),
        MagicMock(filename=CRITICAL_FILE_CHANGE)
    ]
    _setup_labels(pr)
    _setup_pr_reviews(pr)

    pr_checker = PrChecker(args, pr)

    # Act
    pr_checker.verify_pr()

    # Asset
    pr.create_review.assert_called_once_with(body=f'{args.required_label_message} '
                                             f'Please add one of the following '
                                             f'labels: `{args.valid_labels}` '
                                             'to confirm these changes.',
                                             event='REQUEST_CHANGES')


# GIVEN a PR which has critical file changes
# AND does not have lables
# AND the bot has already requested changes
# WHEN verify_pr is called
# THEN the bot does nothing
def test_pr_checker_verify_pr_critical_file_changes_no_label_changes_requested():
    # Arrange
    args = _get_args(file_globs=[DEFAULT_GLOB], valid_labels=['not_present'])
    pr = MagicMock()
    pr.get_files.return_value = [
        *_get_files(),
        MagicMock(filename=CRITICAL_FILE_CHANGE)
    ]
    _setup_labels(pr)
    _setup_pr_reviews(pr, with_change_request_body=args.required_label_message)

    pr_checker = PrChecker(args, pr)

    # Act
    pr_checker.verify_pr()

    # Asset
    pr.create_review.assert_not_called()


# GIVEN a PR which has critical file changes
# AND does no have the appropriate lables
# AND the bot has not yet requested changes
# WHEN verify_pr is called
# THEN the bot does nothing
def test_pr_checker_verify_pr_critical_file_changes_with_label_no_changes_requested():
    # Arrange
    args = _get_args(file_globs=[DEFAULT_GLOB], valid_labels=['label1'])
    pr = MagicMock()
    pr.get_files.return_value = [
        *_get_files(),
        MagicMock(filename=CRITICAL_FILE_CHANGE)
    ]
    _setup_labels(pr)
    _setup_pr_reviews(pr)

    pr_checker = PrChecker(args, pr)

    # Act
    pr_checker.verify_pr()

    # Asset
    pr.create_review.assert_not_called()


# GIVEN a PR which has critical file changes
# AND does no have the appropriate lables
# AND the bot has already requested changes
# WHEN verify_pr is called
# THEN the bot dismisses the previous change requests with the appropriate message
def test_pr_checker_verify_pr_critical_file_changes_with_label_changes_requested():
    # Arrange
    args = _get_args(file_globs=[DEFAULT_GLOB], valid_labels=['label1'])
    pr = MagicMock()
    pr.get_files.return_value = [
        *_get_files(),
        MagicMock(filename=CRITICAL_FILE_CHANGE)
    ]
    _setup_labels(pr)
    change_request_review = _setup_pr_reviews(
        pr, with_change_request_body=args.required_label_message)

    pr_checker = PrChecker(args, pr)

    # Act
    pr_checker.verify_pr()

    # Asset
    pr.create_review.assert_not_called()
    change_request_review.dismiss.assert_called_once_with(
        args.label_added_message)


# GIVEN a PR which does not have any critical file changes
# AND the bot has already requested changes
# WHEN verify_pr is called
# THEN the bot dismisses the previous change requests with the appropriate message
def test_pr_checker_verify_pr_no_critical_file_changes_changes_requested():
    # Arrange
    args = _get_args(file_globs=[DEFAULT_GLOB], valid_labels=['label1'])
    pr = MagicMock()
    pr.get_files.return_value = [*_get_files()]
    _setup_labels(pr)
    change_request_review = _setup_pr_reviews(
        pr, with_change_request_body=args.required_label_message)

    pr_checker = PrChecker(args, pr)

    # Act
    pr_checker.verify_pr()

    # Asset
    pr.create_review.assert_not_called()
    change_request_review.dismiss.assert_called_once_with(
        args.changes_reverted_message)


# GIVEN a PR which does not have any critical file changes
# AND the bot has not previously requested changes
# WHEN verify_pr is called
# THEN the bot does nothing
def test_pr_checker_verify_pr_no_critical_file_changes_no_changes_requested():
    # Arrange
    args = _get_args(file_globs=[DEFAULT_GLOB], valid_labels=['label1'])
    pr = MagicMock()
    pr.get_files.return_value = [*_get_files()]
    _setup_labels(pr)
    _setup_pr_reviews(pr, with_comment_body=args.changes_reverted_message)

    pr_checker = PrChecker(args, pr)

    # Act
    pr_checker.verify_pr()

    # Asset
    pr.create_review.assert_not_called()
