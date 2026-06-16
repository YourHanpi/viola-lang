# -*- coding: utf-8 -*-
from backend import CompilerVM


def _construct_vm() -> CompilerVM:
    vm: CompilerVM = CompilerVM("hello_world.vla", ".", "vlaproject.toml")
    return vm


def _exec(vm: CompilerVM) -> None:
    with open("hello_world.vla.vlair", "r") as f:
        vm.exec(f.read())
    vm.get()


def main() -> None:
    _exec(_construct_vm())


if __name__ == '__main__':
    main()
