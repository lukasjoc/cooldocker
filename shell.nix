{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  name = "cooldocker";
  version = "1.1.0";
  buildInputs = [
    # python 3.9
    pkgs.python39

    # install all python packages needed
    pkgs.python39Packages.tabulate
    pkgs.python39Packages.termcolor
    pkgs.python39Packages.docker
    pkgs.python39Packages.mypy
  ];
}
