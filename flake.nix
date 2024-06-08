{
  inputs.nixpkgs.url = "github:nixos/nixpkgs/nixos-unstable";

  outputs = { self, nixpkgs, }:
  let
    pkgs = nixpkgs.legacyPackages.x86_64-linux;
  in {
    devShells.x86_64-linux.default = pkgs.mkShell {
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
        pkgs.qt6.qtwayland
        pkgs.qt6.full
        pkgs.qt6.qtbase
        pkgs.zstd
        # For PySide6 Multimedia
        pkgs.libpulseaudio
        pkgs.libkrb5
      ];
      buildInputs = with pkgs; [
        cmake
        gdb
        zstd
        qt6.qtbase
        qt6.full
        qt6.qtwayland
        qtcreator
        python312Packages.pip
        python312Full
        python312Packages.virtualenv # run virtualenv .
        python312Packages.pyusb # fixes the pyusb 'No backend available' when installed directly via pip

        libgcc
        makeWrapper
        bashInteractive
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
        qt6.wrapQtAppsHook
        makeWrapper
        bashInteractive
      ];
      # set the environment variables that Qt apps expect
      shellHook = ''
        export QT_QPA_PLATFORM=wayland
        export LIBRARY_PATH=/usr/lib:/usr/lib64:$LIBRARY_PATH
        # export LD_LIBRARY_PATH=${pkgs.stdenv.cc.cc.lib}/lib/:/run/opengl-driver/lib/
        export QT_PLUGIN_PATH=${pkgs.qt6.qtbase}/${pkgs.qt6.qtbase.qtPluginPrefix}
        bashdir=$(mktemp -d)
        makeWrapper "$(type -p bash)" "$bashdir/bash" "''${qtWrapperArgs[@]}"
        exec "$bashdir/bash"
      '';
    };
  };
}
