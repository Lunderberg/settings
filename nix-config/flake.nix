{
  description = "Flake config";

  inputs = {
    nixpkgs.url = "github:nixos/nixpkgs/nixos-25.11";
    home-manager.url = "github:nix-community/home-manager/release-25.11";
    home-manager.inputs.nixpkgs.follows = "nixpkgs";
  };

  outputs =
    { self, nixpkgs, home-manager, ... }@inputs:
    {
      nixosConfigurations.shelley = nixpkgs.lib.nixosSystem {
        system = "x86_64-linux";
        modules = [
          ./hosts/shelley.nix
          ./modules/common.nix
          ./modules/packages.nix
          home-manager.nixosModules.home-manager
          {
            home-manager.useGlobalPkgs = true;
            home-manager.useUserPackages = true;
            home-manager.users.eric = ./modules/home.nix;
          }
        ] ++ nixpkgs.lib.optional (builtins.pathExists ./secrets/localization.nix) ./secrets/localization.nix
        ;
      };
    };
}
