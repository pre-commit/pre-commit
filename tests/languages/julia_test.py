from __future__ import annotations

import os
from unittest import mock

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

def test_julia_hook_version(tmp_path):
    code = """
    using Example
    function main()
        println("Hello, Julia $(VERSION)!")
    end
    main()
    """
    _make_hook(tmp_path, code)
    expected = (0, b'Hello, Julia 1.10.10!\n')
    assert run_language(
        tmp_path, julia, 'src/main.jl',
        version='1.10.10',
    ) == expected

def test_julia_hook_with_startup(tmp_path):
    depot_path = tmp_path.joinpath('depot')
    depot_path.joinpath('config').mkdir(parents=True)
    startup = depot_path.joinpath('config', 'startup.jl')
    startup.write_text('error("Startup file used!")\n')

    depo_path_var = f'{depot_path}{os.pathsep}'
    with mock.patch.dict(os.environ, {'JULIA_DEPOT_PATH': depo_path_var}):
        test_julia_hook(tmp_path)

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
