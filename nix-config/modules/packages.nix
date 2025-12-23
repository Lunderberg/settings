{ pkgs, ... }:
{
  environment.systemPackages =
    with pkgs; [
      chrpath
      clang
      clang-tools
      discord
      ecryptfs
      emacs
      gcc
      git
      gnumake
      python3
      rsync
      ruff
      rustup
      signal-desktop
      tmux
      tree
      uv
      vlc
      wget
    ];

  # TODO: Update nix-index's bash integration to check for
  # executables located somewhere other than `/bin/$CMD`.
  programs.nix-index = {
    enable = true;
    enableBashIntegration = true;
  };

  programs.steam.enable = true;
}
