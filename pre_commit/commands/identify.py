from pre_commit import git
from pre_commit.file_classifier.classifier import classify


def identify(args):
    # TODO: more useful output
    # TODO: check whether file is in git repo first?
    print(classify(args.path, git.guess_git_type_for_file(args.path)))
