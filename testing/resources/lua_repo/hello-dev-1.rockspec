package = "hello"
version = "dev-1"

source = {
   url = "git+ssh://git@github.com/pre-commit/pre-commit.git"
}
description = {}
dependencies = {}
build = {
    type = "builtin",
    modules = {},
    install = {
        bin = {"bin/hello-world-lua"}
    },
}
