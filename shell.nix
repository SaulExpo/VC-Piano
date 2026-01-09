{ pkgs ? import <nixpkgs> {} }:

let
  libraries = with pkgs; [
    stdenv.cc.cc.lib # Necesario para libstdc++.so.6
    libglvnd
    libGLU
    glib

    # Dependencias comunes extra para OpenCV/GUI en Linux
    xorg.libX11
    xorg.libXi
    xorg.libXrender
    xorg.libICE
    xorg.libSM

    vulkan-loader

    alsa-lib
    pulseaudio
  ];

in pkgs.mkShell {
  name = "vc-dev-environment";

  packages = with pkgs; [
    uv
    binutils
  ];

  buildInputs = libraries;

  shellHook = ''
      export LD_LIBRARY_PATH="${pkgs.lib.makeLibraryPath libraries}:$LD_LIBRARY_PATH"
  '';
}
