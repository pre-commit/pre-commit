from __future__ import annotations

from pre_commit.languages import dotnet
from testing.language_helpers import run_language


def _write_program_cs(tmp_path):
    program_cs = '''\
using System;

namespace dotnet_tests
{
    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("Hello from dotnet!");
        }
    }
}
'''
    tmp_path.joinpath('Program.cs').write_text(program_cs)


def _csproj(tool_name):
    return f'''\
<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>Exe</OutputType>
    <TargetFramework>net8</TargetFramework>
    <PackAsTool>true</PackAsTool>
    <ToolCommandName>{tool_name}</ToolCommandName>
    <PackageOutputPath>./nupkg</PackageOutputPath>
  </PropertyGroup>
</Project>
'''


def test_dotnet_csproj(tmp_path):
    csproj = _csproj('testeroni')
    _write_program_cs(tmp_path)
    tmp_path.joinpath('dotnet_csproj.csproj').write_text(csproj)
    ret = run_language(tmp_path, dotnet, 'testeroni')
    assert ret == (0, b'Hello from dotnet!\n')


def test_dotnet_csproj_prefix(tmp_path):
    csproj = _csproj('testeroni.tool')
    _write_program_cs(tmp_path)
    tmp_path.joinpath('dotnet_hooks_csproj_prefix.csproj').write_text(csproj)
    ret = run_language(tmp_path, dotnet, 'testeroni.tool')
    assert ret == (0, b'Hello from dotnet!\n')


def test_dotnet_sln(tmp_path):
    csproj = _csproj('testeroni')
    sln = '''\
Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio 15
VisualStudioVersion = 15.0.26124.0
MinimumVisualStudioVersion = 15.0.26124.0
Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "dotnet_hooks_sln_repo", "dotnet_hooks_sln_repo.csproj", "{6568CFDB-6F6F-45A9-932C-8C7DAABC8E56}"
EndProject
Global
        GlobalSection(SolutionConfigurationPlatforms) = preSolution
                Debug|Any CPU = Debug|Any CPU
                Debug|x64 = Debug|x64
                Debug|x86 = Debug|x86
                Release|Any CPU = Release|Any CPU
                Release|x64 = Release|x64
                Release|x86 = Release|x86
        EndGlobalSection
        GlobalSection(SolutionProperties) = preSolution
                HideSolutionNode = FALSE
        EndGlobalSection
        GlobalSection(ProjectConfigurationPlatforms) = postSolution
                {6568CFDB-6F6F-45A9-932C-8C7DAABC8E56}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
                {6568CFDB-6F6F-45A9-932C-8C7DAABC8E56}.Debug|Any CPU.Build.0 = Debug|Any CPU
                {6568CFDB-6F6F-45A9-932C-8C7DAABC8E56}.Debug|x64.ActiveCfg = Debug|Any CPU
                {6568CFDB-6F6F-45A9-932C-8C7DAABC8E56}.Debug|x64.Build.0 = Debug|Any CPU
                {6568CFDB-6F6F-45A9-932C-8C7DAABC8E56}.Debug|x86.ActiveCfg = Debug|Any CPU
                {6568CFDB-6F6F-45A9-932C-8C7DAABC8E56}.Debug|x86.Build.0 = Debug|Any CPU
                {6568CFDB-6F6F-45A9-932C-8C7DAABC8E56}.Release|Any CPU.ActiveCfg = Release|Any CPU
                {6568CFDB-6F6F-45A9-932C-8C7DAABC8E56}.Release|Any CPU.Build.0 = Release|Any CPU
                {6568CFDB-6F6F-45A9-932C-8C7DAABC8E56}.Release|x64.ActiveCfg = Release|Any CPU
                {6568CFDB-6F6F-45A9-932C-8C7DAABC8E56}.Release|x64.Build.0 = Release|Any CPU
                {6568CFDB-6F6F-45A9-932C-8C7DAABC8E56}.Release|x86.ActiveCfg = Release|Any CPU
                {6568CFDB-6F6F-45A9-932C-8C7DAABC8E56}.Release|x86.Build.0 = Release|Any CPU
        EndGlobalSection
EndGlobal
'''  # noqa: E501
    _write_program_cs(tmp_path)
    tmp_path.joinpath('dotnet_hooks_sln_repo.csproj').write_text(csproj)
    tmp_path.joinpath('dotnet_hooks_sln_repo.sln').write_text(sln)

    ret = run_language(tmp_path, dotnet, 'testeroni')
    assert ret == (0, b'Hello from dotnet!\n')


def _setup_dotnet_combo(tmp_path):
    sln = '''\
Microsoft Visual Studio Solution File, Format Version 12.00
# Visual Studio Version 16
VisualStudioVersion = 16.0.30114.105
MinimumVisualStudioVersion = 10.0.40219.1
Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "proj1", "proj1\\proj1.csproj", "{38A939C3-DEA4-47D7-9B75-0418C4249662}"
EndProject
Project("{FAE04EC0-301F-11D3-BF4B-00C04F79EFBC}") = "proj2", "proj2\\proj2.csproj", "{4C9916CB-165C-4EF5-8A57-4CB6794C1EBF}"
EndProject
Global
        GlobalSection(SolutionConfigurationPlatforms) = preSolution
                Debug|Any CPU = Debug|Any CPU
                Release|Any CPU = Release|Any CPU
        EndGlobalSection
        GlobalSection(SolutionProperties) = preSolution
                HideSolutionNode = FALSE
        EndGlobalSection
        GlobalSection(ProjectConfigurationPlatforms) = postSolution
                {38A939C3-DEA4-47D7-9B75-0418C4249662}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
                {38A939C3-DEA4-47D7-9B75-0418C4249662}.Debug|Any CPU.Build.0 = Debug|Any CPU
                {38A939C3-DEA4-47D7-9B75-0418C4249662}.Release|Any CPU.ActiveCfg = Release|Any CPU
                {38A939C3-DEA4-47D7-9B75-0418C4249662}.Release|Any CPU.Build.0 = Release|Any CPU
                {4C9916CB-165C-4EF5-8A57-4CB6794C1EBF}.Debug|Any CPU.ActiveCfg = Debug|Any CPU
                {4C9916CB-165C-4EF5-8A57-4CB6794C1EBF}.Debug|Any CPU.Build.0 = Debug|Any CPU
                {4C9916CB-165C-4EF5-8A57-4CB6794C1EBF}.Release|Any CPU.ActiveCfg = Release|Any CPU
                {4C9916CB-165C-4EF5-8A57-4CB6794C1EBF}.Release|Any CPU.Build.0 = Release|Any CPU
        EndGlobalSection
EndGlobal
'''  # noqa: E501
    tmp_path.joinpath('dotnet_hooks_combo_repo.sln').write_text(sln)

    csproj1 = _csproj('proj1')
    proj1 = tmp_path.joinpath('proj1')
    proj1.mkdir()
    proj1.joinpath('proj1.csproj').write_text(csproj1)
    _write_program_cs(proj1)

    csproj2 = _csproj('proj2')
    proj2 = tmp_path.joinpath('proj2')
    proj2.mkdir()
    proj2.joinpath('proj2.csproj').write_text(csproj2)
    _write_program_cs(proj2)


def test_dotnet_combo_proj1(tmp_path):
    _setup_dotnet_combo(tmp_path)
    ret = run_language(tmp_path, dotnet, 'proj1')
    assert ret == (0, b'Hello from dotnet!\n')


def test_dotnet_combo_proj2(tmp_path):
    _setup_dotnet_combo(tmp_path)
    ret = run_language(tmp_path, dotnet, 'proj2')
    assert ret == (0, b'Hello from dotnet!\n')
