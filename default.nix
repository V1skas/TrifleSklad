{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  packages = with pkgs; [
    pipenv
    pyenv

    zlib.dev
    unzip
    libffi.dev
    readline.dev
    bzip2.dev
    openssl.dev
    ncurses.dev
    sqlite
    xz
    tk
    expat
    tcl
    pkgconf
    gcc
    gnumake
    nodejs_23
    openldap.dev
    cyrus_sasl.dev
  ];

  shellHook = ''
    export LD_LIBRARY_PATH="${pkgs.openldap}/lib:${pkgs.cyrus_sasl}/lib:$LD_LIBRARY_PATH"
    pipenv shell
  '';
}
