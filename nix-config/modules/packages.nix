{ pkgs, ... }:
{
  environment.systemPackages =
    with pkgs; [
      bind.dnsutils
      chrpath
      clang
      clang-tools
      discord
      ecryptfs
      emacs
      gcc
      git
      gnumake
      keyutils
      lm_sensors.bin
      openssl
      net-tools
      nix-tree
      nmap
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
