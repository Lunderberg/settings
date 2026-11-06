{ config, lib, pkgs, ...}:
{
  networking.hostName = "shelley";
  imports = [
    ./hardware/shelley.nix
  ];

  boot.loader = {
    systemd-boot.enable = true;
    efi.canTouchEfiVariables = true;
  };

  hardware.graphics = {
    enable = true;
    extraPackages = with pkgs; [
      intel-media-driver
    ];
  };
}
