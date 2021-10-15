import argparse
import os.path
import subprocess
import sys
from typing import Optional
from typing import Sequence
from typing import Tuple

from pre_commit.commands.run import run
from pre_commit.envcontext import envcontext
from pre_commit.parse_shebang import normalize_cmd
from pre_commit.store import Store

Z40 = '0' * 40


def _run_legacy(
        hook_type: str,
        hook_dir: str,
        args: Sequence[str],
) -> Tuple[int, bytes]:
    if os.environ.get('PRE_COMMIT_RUNNING_LEGACY'):
        raise SystemExit(
            f"bug: pre-commit's script is installed in migration mode\n"
            f'run `pre-commit install -f --hook-type {hook_type}` to fix '
            f'this\n\n'
            f'Please report this bug at '
            f'https://github.com/pre-commit/pre-commit/issues',
        )

    if hook_type == 'pre-push':
        stdin = sys.stdin.buffer.read()
    else:
        stdin = b''

    # not running in legacy mode
    legacy_hook = os.path.join(hook_dir, f'{hook_type}.legacy')
    if not os.access(legacy_hook, os.X_OK):
        return 0, stdin

    with envcontext((('PRE_COMMIT_RUNNING_LEGACY', '1'),)):
        cmd = normalize_cmd((legacy_hook, *args))
        return subprocess.run(cmd, input=stdin).returncode, stdin


def _validate_config(
        retv: int,
        config: str,
        skip_on_missing_config: bool,
) -> None:
  if not os.path.isfile(config) or not os.path.isfile('.secrets.baseline'):
        if not os.path.isfile(config):
            print(
                f'No {config} file was found\n'
                f'- .pre-commit-config.yaml file must be included in root of repo\n'
                f'- The file can be copied from: \n' 
                f'' + OKGREEN + get_git_template_dir() + '\.pre-commit-config.yaml' + ENDC + '\n'
                f'- If the file is not found it can be downloaded using jfrog-cli \n'
                f'- To download .pre-commit-config.yaml, run: \n'
                f'' + OKGREEN + 'jfrog rt dl cxloyalty-tools-local/sic-tools/.pre-commit-config.yaml --flat' + ENDC + '\n'             
                f'\n'
            )
        
        if  not os.path.isfile('.secrets.baseline'):   
            print(
                f'No .secrets.baseline file was found\n'
                f'- .secrets.baseline file must be included in root of repo\n'
                f'- The file can be copied from: \n' 
                f'' + OKGREEN + get_git_template_dir() + '\.secrets.baseline' + ENDC + '\n'
                f'- If the file is not found it can be downloaded using jfrog-cli \n'               
                f'- To download .secrets.baseline, run: \n'
                f'' + OKGREEN + 'jfrog rt dl /cxloyalty-tools-local/sic-tools/.secrets.baseline --flat' + ENDC + '\n' 
                
            )
        raise SystemExit(1)
    if is_non_tracked_file('.secrets.baseline'):
        print(
            f"- .secrets.baseline is not tracked. \n"
            f"run: git add .secrets.baseline \n"
            f"- and commit the file"
        )
        raise SystemExit(1)
    if is_non_tracked_file('.pre-commit-config.yaml'):
        print(
            f"- .pre-commit-config.yaml is not tracked. \n"
            f"run: git add .pre-commit-config.yaml \n"
            f"- and commit the file"
        )
        raise SystemExit(1)
    if is_modified_file('.secrets.baseline'):
        print(
            f"- .secrets.baseline has been modified. \n"
            f"run: git add .secrets.baseline \n"
            f"- and commit the file"
        )
        raise SystemExit(1)
    if is_modified_file('.pre-commit-config.yaml'):
        print(
            f"- .pre-commit-config.yaml has been modified. \n"
            f"run: git add .pre-commit-config.yaml \n"
            f"- and commit the file"
        )
        raise SystemExit(1)
    if non_commited_file('.secrets.baseline'):
        print(
            f"- .secrets.baseline has not been commited. \n"
            f"Commit the file before proceeding \n"
        )
        raise SystemExit(1)
    if non_commited_file('.pre-commit-config.yaml'):
        print(
            f"- .pre-commit-config.yaml not been commited. \n"
            f"Commit the file before proceeding \n"
        )
        raise SystemExit(1)
def get_git_template_dir():
    output = subprocess.check_output(('git', 'config', 'init.templateDir'))
    output = output.decode().strip()
    return output 

def non_commited_file(filename):
    output = subprocess.check_output(('git', 'status', '--porcelain'))
    output = output.decode().strip().splitlines()
    for file in output: 
        file = file[2:].strip()
        if file in filename:
           return True 

    return False
    
#Added for sic tool to check if file has been modified but not added to git.        
def is_modified_file(filename): 
    output = subprocess.check_output(('git', 'diff', '--name-only'))
    output = output.decode().strip()
    if filename in output:
        return True 
    else:
        return False
    

#Added for sic tool to check if file is not tracked in git. 
def is_non_tracked_file(filename): 
    output = subprocess.check_output(('git', 'ls-files', '--others','--exclude-standard'))
    output = output.decode().strip()
    if filename in output:
       return True 
    else:
       return False

def _ns(
        hook_type: str,
        color: bool,
        *,
        all_files: bool = False,
        remote_branch: Optional[str] = None,
        local_branch: Optional[str] = None,
        from_ref: Optional[str] = None,
        to_ref: Optional[str] = None,
        remote_name: Optional[str] = None,
        remote_url: Optional[str] = None,
        commit_msg_filename: Optional[str] = None,
        checkout_type: Optional[str] = None,
        is_squash_merge: Optional[str] = None,
        rewrite_command: Optional[str] = None,
) -> argparse.Namespace:
    return argparse.Namespace(
        color=color,
        hook_stage=hook_type.replace('pre-', ''),
        remote_branch=remote_branch,
        local_branch=local_branch,
        from_ref=from_ref,
        to_ref=to_ref,
        remote_name=remote_name,
        remote_url=remote_url,
        commit_msg_filename=commit_msg_filename,
        all_files=all_files,
        checkout_type=checkout_type,
        is_squash_merge=is_squash_merge,
        rewrite_command=rewrite_command,
        files=(),
        hook=None,
        verbose=False,
        show_diff_on_failure=False,
    )


def _rev_exists(rev: str) -> bool:
    return not subprocess.call(('git', 'rev-list', '--quiet', rev))


def _pre_push_ns(
        color: bool,
        args: Sequence[str],
        stdin: bytes,
) -> Optional[argparse.Namespace]:
    remote_name = args[0]
    remote_url = args[1]

    for line in stdin.decode().splitlines():
        local_branch, local_sha, remote_branch, remote_sha = line.split()
        if local_sha == Z40:
            continue
        elif remote_sha != Z40 and _rev_exists(remote_sha):
            return _ns(
                'pre-push', color,
                from_ref=remote_sha, to_ref=local_sha,
                remote_branch=remote_branch,
                local_branch=local_branch,
                remote_name=remote_name, remote_url=remote_url,
            )
        else:
            # ancestors not found in remote
            ancestors = subprocess.check_output((
                'git', 'rev-list', local_sha, '--topo-order', '--reverse',
                '--not', f'--remotes={remote_name}',
            )).decode().strip()
            if not ancestors:
                continue
            else:
                first_ancestor = ancestors.splitlines()[0]
                cmd = ('git', 'rev-list', '--max-parents=0', local_sha)
                roots = set(subprocess.check_output(cmd).decode().splitlines())
                if first_ancestor in roots:
                    # pushing the whole tree including root commit
                    return _ns(
                        'pre-push', color,
                        all_files=True,
                        remote_name=remote_name, remote_url=remote_url,
                        remote_branch=remote_branch,
                        local_branch=local_branch,
                    )
                else:
                    rev_cmd = ('git', 'rev-parse', f'{first_ancestor}^')
                    source = subprocess.check_output(rev_cmd).decode().strip()
                    return _ns(
                        'pre-push', color,
                        from_ref=source, to_ref=local_sha,
                        remote_name=remote_name, remote_url=remote_url,
                        remote_branch=remote_branch,
                        local_branch=local_branch,
                    )

    # nothing to push
    return None


_EXPECTED_ARG_LENGTH_BY_HOOK = {
    'commit-msg': 1,
    'post-checkout': 3,
    'post-commit': 0,
    'pre-commit': 0,
    'pre-merge-commit': 0,
    'post-merge': 1,
    'post-rewrite': 1,
    'pre-push': 2,
}


def _check_args_length(hook_type: str, args: Sequence[str]) -> None:
    if hook_type == 'prepare-commit-msg':
        if len(args) < 1 or len(args) > 3:
            raise SystemExit(
                f'hook-impl for {hook_type} expected 1, 2, or 3 arguments '
                f'but got {len(args)}: {args}',
            )
    elif hook_type in _EXPECTED_ARG_LENGTH_BY_HOOK:
        expected = _EXPECTED_ARG_LENGTH_BY_HOOK[hook_type]
        if len(args) != expected:
            arguments_s = 'argument' if expected == 1 else 'arguments'
            raise SystemExit(
                f'hook-impl for {hook_type} expected {expected} {arguments_s} '
                f'but got {len(args)}: {args}',
            )
    else:
        raise AssertionError(f'unexpected hook type: {hook_type}')


def _run_ns(
        hook_type: str,
        color: bool,
        args: Sequence[str],
        stdin: bytes,
) -> Optional[argparse.Namespace]:
    _check_args_length(hook_type, args)
    if hook_type == 'pre-push':
        return _pre_push_ns(color, args, stdin)
    elif hook_type in {'commit-msg', 'prepare-commit-msg'}:
        return _ns(hook_type, color, commit_msg_filename=args[0])
    elif hook_type in {'post-commit', 'pre-merge-commit', 'pre-commit'}:
        return _ns(hook_type, color)
    elif hook_type == 'post-checkout':
        return _ns(
            hook_type, color,
            from_ref=args[0], to_ref=args[1], checkout_type=args[2],
        )
    elif hook_type == 'post-merge':
        return _ns(hook_type, color, is_squash_merge=args[0])
    elif hook_type == 'post-rewrite':
        return _ns(hook_type, color, rewrite_command=args[0])
    else:
        raise AssertionError(f'unexpected hook type: {hook_type}')


def hook_impl(
        store: Store,
        *,
        config: str,
        color: bool,
        hook_type: str,
        hook_dir: str,
        skip_on_missing_config: bool,
        args: Sequence[str],
) -> int:
    retv, stdin = _run_legacy(hook_type, hook_dir, args)
    _validate_config(retv, config, skip_on_missing_config)
    ns = _run_ns(hook_type, color, args, stdin)
    if ns is None:
        return retv
    else:
        return retv | run(config, store, ns)
