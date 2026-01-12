{
  pkgs,
  lib,
  ...
}:

let

  # A faster version of `addr2line` than what is provided by
  # clang/gcc/binutils.
  addr2line = pkgs.rustPackages.rustPlatform.buildRustPackage rec {
    pname = "addr2line";
    version = "0.25.1";

    src = pkgs.fetchFromGitHub {
      owner = "gimli-rs";
      repo = pname;
      rev = version;
      hash = "sha256-u7y0DVST2pnx02Gm5Qxs9ZeqbDPQrXUZOKN8BXj0Go4=";
    };

    cargoHash = "sha256-1zNQmvPrDatg1nGwNJMXluK+KItWZ5S3T89+P/tsdT0=";

    buildFeatures = [ "bin" ];
    doCheck = false;

    meta = with lib; {
      description = "A cross-platform library for retrieving per-address debug information from files with DWARF debug information.";
      homepage = "https://github.com/gimli-rs/addr2line";
      license = licenses.mit;
      maintainers = [];
    };
  };

in with pkgs; (perf.overrideAttrs (finalAttrs: previousAttrs: {
  # Disable the wrapper script that moves `binutils-unwrapped` to the
  # front of the PATH.
  preFixup = "";

  # Instead, provide `binutils-unwrapped` as a runtime dependency,
  # along with the faster version of `addr2line`.
  buildInputs = previousAttrs.buildInputs ++ [
    addr2line
    binutils-unwrapped
  ];
}))
