{ pkgs, ... }:
let
  perf-patched = (pkgs.callPackage ./perf-with-addr2line.nix pkgs);
  tmux-v36 = with pkgs; tmux.overrideAttrs (finalAttrs: previousAttrs: {
    version = "3.6";
    src = fetchFromGitHub {
      owner = "tmux";
      repo = "tmux";
      rev = finalAttrs.version;
      hash = "sha256-jIHnwidzqt+uDDFz8UVHihTgHJybbVg3pQvzlMzOXPE=";
    };
  });
in {
  environment.systemPackages =
    with pkgs; [
      bind.dnsutils
      chrpath
      clang
      clang-tools
      cmake
      discord
      ecryptfs
      emacs
      file
      gcc
      gdb
      git
      gnumake
      keyutils
      lm_sensors.bin
      mold-wrapped
      openssl
      perf-patched
      net-tools
      nix-tree
      nmap
      python3
      rsync
      ruff
      rustup
      signal-desktop
      tmux-v36
      tree
      uv
      vlc
      wget
      zip
    ];

  # TODO: Update nix-index's bash integration to check for
  # executables located somewhere other than `/bin/$CMD`.
  programs.nix-index = {
    enable = true;
    enableBashIntegration = true;
  };

  programs.gnupg.agent.enable = true;

  programs.steam.enable = true;

  programs.zoom-us.enable = true;
}
