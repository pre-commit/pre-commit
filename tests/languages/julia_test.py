from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pre_commit.languages import julia
from testing.language_helpers import run_language
from testing.util import cwd


def _make_hook(tmp_path, julia_code):
    src_dir = tmp_path.joinpath('src')
    src_dir.mkdir()
    src_dir.joinpath('main.jl').write_text(julia_code)
    tmp_path.joinpath('Project.toml').write_text(
        '[deps]\n'
        'Example = "7876af07-990d-54b4-ab0e-23690620f79a"\n',
    )


def test_julia_hook(tmp_path):
    code = """
    using Example
    function main()
        println("Hello, world!")
    end
    main()
    """
    _make_hook(tmp_path, code)
    expected = (0, b'Hello, world!\n')
    assert run_language(tmp_path, julia, 'src/main.jl') == expected


def test_julia_hook_with_startup(tmp_path):
    # Set a new environment dir so we can test the install process
    existing_environment_dir = julia.ENVIRONMENT_DIR
    julia.ENVIRONMENT_DIR = 'juliaenv-test-startup'
    try:
        with tempfile.TemporaryDirectory() as depot_tempdir:
            # We will temporarily use a new Julia depot so we can
            # freely write a startup.jl file
            os.environ['JULIA_DEPOT_PATH'] = depot_tempdir
            depot_path = Path(depot_tempdir)
            depot_path.joinpath('config').mkdir(exist_ok=True)
            startup = depot_path.joinpath('config', 'startup.jl')
            # write a startup.jl file that throws an error so
            # we know it's not used
            startup.write_text('error("Startup file used!")\n')
            # check that install & test succeeds with bad startup file
            test_julia_hook(tmp_path)
    finally:
        # restore environment dir
        julia.ENVIRONMENT_DIR = existing_environment_dir
        del os.environ['JULIA_DEPOT_PATH']


def test_julia_hook_manifest(tmp_path):
    code = """
    using Example
    println(pkgversion(Example))
    """
    _make_hook(tmp_path, code)

    tmp_path.joinpath('Manifest.toml').write_text(
        'manifest_format = "2.0"\n\n'
        '[[deps.Example]]\n'
        'git-tree-sha1 = "11820aa9c229fd3833d4bd69e5e75ef4e7273bf1"\n'
        'uuid = "7876af07-990d-54b4-ab0e-23690620f79a"\n'
        'version = "0.5.4"\n',
    )
    expected = (0, b'0.5.4\n')
    assert run_language(tmp_path, julia, 'src/main.jl') == expected


def test_julia_hook_args(tmp_path):
    code = """
    function main(argv)
        foreach(println, argv)
    end
    main(ARGS)
    """
    _make_hook(tmp_path, code)
    expected = (0, b'--arg1\n--arg2\n')
    assert run_language(
        tmp_path, julia, 'src/main.jl --arg1 --arg2',
    ) == expected


def test_julia_hook_additional_deps(tmp_path):
    code = """
    using TOML
    function main()
        project_file = Base.active_project()
        dict = TOML.parsefile(project_file)
        for (k, v) in dict["deps"]
            println(k, " = ", v)
        end
    end
    main()
    """
    _make_hook(tmp_path, code)
    deps = ('TOML=fa267f1f-6049-4f14-aa54-33bafae1ed76',)
    ret, out = run_language(tmp_path, julia, 'src/main.jl', deps=deps)
    assert ret == 0
    assert b'Example = 7876af07-990d-54b4-ab0e-23690620f79a' in out
    assert b'TOML = fa267f1f-6049-4f14-aa54-33bafae1ed76' in out


def test_julia_repo_local(tmp_path):
    env_dir = tmp_path.joinpath('envdir')
    env_dir.mkdir()
    local_dir = tmp_path.joinpath('local')
    local_dir.mkdir()
    local_dir.joinpath('local.jl').write_text(
        'using TOML; foreach(println, ARGS)',
    )
    with cwd(local_dir):
        deps = ('TOML=fa267f1f-6049-4f14-aa54-33bafae1ed76',)
        expected = (0, b'--local-arg1\n--local-arg2\n')
        assert run_language(
            env_dir, julia, 'local.jl --local-arg1 --local-arg2',
            deps=deps, is_local=True,
        ) == expected
