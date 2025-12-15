{ pkgs, ... }:
{
    environment.systemPackages =
      with pkgs; [
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
      rustup
      signal-desktop
      tmux
      uv
      vlc
      wget
    ];

    # TODO: Update nix-index's bash integration to check for
    # executables located somewhere other than `/bin/$CMD`.
    programs.nix-index.enable = true;

    programs.steam.enable = true;
}
