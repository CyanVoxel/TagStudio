{
  description = "Tag Studio Development Environment";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

    qt6Nixpkgs = {
      # Commit bumping to qt6.7.1
      url = "github:NixOS/nixpkgs/47da0aee5616a063015f10ea593688646f2377e4";
    };
  };

  outputs = { self, nixpkgs, qt6Nixpkgs }:
  let
    pkgs = nixpkgs.legacyPackages.x86_64-linux;

    qt6Pkgs = qt6Nixpkgs.legacyPackages.x86_64-linux;
  in {
    devShells.x86_64-linux.default = pkgs.mkShell {
      name = "Tag Studio Virtual Environment";
      venvDir = "./.venv";

      LD_LIBRARY_PATH = pkgs.lib.makeLibraryPath [
        pkgs.gcc-unwrapped
        pkgs.zlib
        pkgs.libglvnd
        pkgs.glib
        pkgs.stdenv.cc.cc
        pkgs.fontconfig
        pkgs.libxkbcommon
        pkgs.xorg.libxcb
        pkgs.freetype
        pkgs.dbus
        pkgs.zstd
        # For PySide6 Multimedia
        pkgs.libpulseaudio
        pkgs.libkrb5

        qt6Pkgs.qt6.qtwayland
        qt6Pkgs.qt6.full
        qt6Pkgs.qt6.qtbase
      ];

      buildInputs = with pkgs; [
        cmake
        gdb
        zstd
        python312Full
        python312Packages.pip
        python312Packages.pyusb # fixes the pyusb 'No backend available' when installed directly via pip
        python312Packages.venvShellHook # Initializes a venv in $venvDir
        ruff # Ruff cannot be installed via pip
        mypy # MyPy cannot be installed via pip

        libgcc
        glib
        libxkbcommon
        freetype
        binutils
        dbus
        coreutils
        libGL
        libGLU
        fontconfig
        xorg.libxcb

        # this is for the shellhook portion
        makeWrapper
        bashInteractive
      ] ++ [
        qt6Pkgs.qt6.qtbase
        qt6Pkgs.qt6.full
        qt6Pkgs.qt6.qtwayland
        qt6Pkgs.qtcreator

        # this is for the shellhook portion
        qt6Pkgs.qt6.wrapQtAppsHook
      ];

      # Run after the virtual environment is created
      postVenvCreation = ''
        unset SOURCE_DATE_EPOCH

        echo Installing dependencies into virtual environment
        pip install -r requirements.txt
        pip install -r requirements-dev.txt
        # Hacky solution to not fight with other dev deps
        # May show failure if skipped due to same version with nixpkgs
        pip uninstall -y mypy ruff
      '';

      # set the environment variables that Qt apps expect
      postShellHook = ''
        unset SOURCE_DATE_EPOCH

        export QT_QPA_PLATFORM="wayland;xcb"
        export LIBRARY_PATH=/usr/lib:/usr/lib64:$LIBRARY_PATH
        # export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib/:/run/opengl-driver/lib/
        export QT_PLUGIN_PATH=${pkgs.qt6.qtbase}/${pkgs.qt6.qtbase.qtPluginPrefix}
        bashdir=$(mktemp -d)
        makeWrapper "$(type -p bash)" "$bashdir/bash" "''${qtWrapperArgs[@]}"

        echo Activating Virtual Environment
        source $venvDir/bin/activate
        export PYTHONPATH=$PWD/$venvDir/${pkgs.python312Full.sitePackages}:$PYTHONPATH

        exec "$bashdir/bash"
      '';
    };
  };
}
